from io import BytesIO
import unittest
from unittest.mock import patch

import pandas as pd
from pyarrow import ArrowInvalid

from hf_sync import load_parquet


class RemoteFileSystem:
    """Model a remote replacement whose listing still has the old file size."""

    def __init__(self, payload: bytes, cached_size: int | None = None):
        self.payload = payload
        self.cached_size = len(payload) if cached_size is None else cached_size
        self.opened = []
        self.invalidated = []

    def open(self, path, mode, *, block_size=None):
        self.opened.append((path, block_size))
        # Ordinary reads are bounded by listing metadata; streaming reads are not.
        data = self.payload if block_size == 0 else self.payload[:self.cached_size]
        return BytesIO(data)

    def invalidate_cache(self, path):
        self.invalidated.append(path)
        self.cached_size = len(self.payload)


class LoadParquetTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "cd_municipio": ["00123", "41238"],
            "QT_VOTOS_TOTAL": [10, 0],
            "pct_genero_feminino": [60.0, None],
        })
        self.payload = self.frame.to_parquet(index=False)
        load_parquet.clear()
        self.addCleanup(load_parquet.clear)

    def test_replaced_file_recovers_from_stale_size_for_both_groups(self):
        for group in ("vereadores", "dep_estaduais"):
            with self.subTest(group=group):
                path = f"{group}/candidato/2026/demografico/stage02_genero.parquet"
                fs = RemoteFileSystem(self.payload, len(self.payload) - 17)
                with fs.open(path, "rb") as source:
                    with self.assertRaisesRegex(ArrowInvalid, "magic bytes not found"):
                        pd.read_parquet(source)
                fs.opened.clear()
                with patch("hf_sync.hf_filesystem", return_value=fs):
                    actual = load_parquet(path)
                    pd.testing.assert_frame_equal(actual, self.frame)
                    # A second consumer (capital/interior or distribution) reuses
                    # the successful frame without downloading the same file again.
                    pd.testing.assert_frame_equal(load_parquet(path), self.frame)
                self.assertEqual(fs.invalidated, [path])
                self.assertEqual(fs.opened, [(path, None), (path, 0)])

    def test_valid_file_keeps_normal_read(self):
        fs = RemoteFileSystem(self.payload)
        with patch("hf_sync.hf_filesystem", return_value=fs):
            pd.testing.assert_frame_equal(load_parquet("valid.parquet"), self.frame)
        self.assertEqual(fs.opened, [("valid.parquet", None)])
        self.assertEqual(fs.invalidated, [])

    def test_corrupt_file_still_fails_after_one_retry(self):
        fs = RemoteFileSystem(b"this is not a parquet file")
        with patch("hf_sync.hf_filesystem", return_value=fs):
            with self.assertRaises(ArrowInvalid):
                load_parquet("corrupt.parquet")
        self.assertEqual(len(fs.opened), 2)
        self.assertEqual(fs.invalidated, ["corrupt.parquet"])

    def test_missing_or_forbidden_file_is_not_retried(self):
        for error in (FileNotFoundError, PermissionError):
            with self.subTest(error=error):
                fs = RemoteFileSystem(self.payload)
                with patch.object(fs, "open", side_effect=error) as open_file:
                    with patch("hf_sync.hf_filesystem", return_value=fs):
                        with self.assertRaises(error):
                            load_parquet(f"{error.__name__}.parquet")
                self.assertEqual(open_file.call_count, 1)
                self.assertEqual(fs.invalidated, [])


if __name__ == "__main__":
    unittest.main()
