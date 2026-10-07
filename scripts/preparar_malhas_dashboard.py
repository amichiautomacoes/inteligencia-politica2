"""Create compact, municipality-filterable GeoParquets for the dashboard."""

from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hf_sync import hf_filesystem, load_env


OUTPUT = ROOT / "terriorio"
LAYERS = (
    ("MG_municipios_2022.parquet", ["code_muni", "name_muni", "geometry"], "code_muni", 0.002, 64),
    ("MG_mesorregioes_2022.parquet", ["code_meso", "name_meso", "geometry"], "code_meso", 0.002, 12),
    ("MG_bairros_CD2022.parquet", ["code_muni", "code_neighborhood", "name_neighborhood", "geometry"], "code_muni", 0.0001, 32),
    ("MG_AreaPonderada_CD2022.parquet", ["code_muni", "code_weighting", "geometry"], "code_muni", 0.0001, 32),
)


def main() -> None:
    env = load_env(ROOT / ".env")
    fs = hf_filesystem(env.get("HF_TOKEN"))
    prefix = env.get("HF_GEOGRAPHY_REFERENCE_PREFIX", "IBGE/MG/dadosterritorio").strip("/")
    remote = f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}"
    OUTPUT.mkdir(exist_ok=True)

    for filename, columns, sort_column, tolerance, row_group_size in LAYERS:
        with fs.open(f"{remote}/{filename}", "rb") as source:
            frame = gpd.read_parquet(source, columns=columns)
        if frame.crs is None:
            raise ValueError(f"{filename} has no CRS")
        frame = frame.to_crs(4326)
        frame = frame.dropna(subset=["geometry"]).copy()
        frame[sort_column] = frame[sort_column].astype("string")
        frame = frame.sort_values(sort_column).reset_index(drop=True)
        frame["geometry"] = frame.geometry.simplify(tolerance, preserve_topology=True)
        if frame.geometry.is_empty.any() or not frame.geometry.is_valid.all():
            raise ValueError(f"Invalid simplified geometry in {filename}")
        target = OUTPUT / filename
        frame.to_parquet(target, index=False, compression="zstd", row_group_size=row_group_size)
        metadata = pq.read_metadata(target)
        print(f"{filename}: {len(frame)} rows, {metadata.num_row_groups} groups, {target.stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    main()
