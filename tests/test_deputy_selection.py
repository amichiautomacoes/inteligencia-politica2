import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

import hf_sync


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eleitoral.common.shared_header import selected_deputado_label


class DeputySelectionTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "HF_BUCKET_URL": "hf://buckets/owner/dashboard",
            "HF_VISUALIZACAO_PREFIX": "dep_estadual",
        }
        self.env_patch = patch("hf_sync.load_env", return_value=self.config)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_default_and_empty_prefixes_use_state_deputies(self):
        for prefix in (None, "", " / ", "/dep_estadual/"):
            with self.subTest(prefix=prefix):
                config = {"HF_BUCKET_URL": self.config["HF_BUCKET_URL"] + "/"}
                if prefix is not None:
                    config["HF_VISUALIZACAO_PREFIX"] = prefix
                self.assertEqual(
                    hf_sync.hf_visualizacao_path(config),
                    "hf://buckets/owner/dashboard/dep_estadual",
                )

    def test_legacy_session_group_does_not_override_environment(self):
        config = dict(self.config, HF_VISUALIZACAO_PREFIX="dados/dep_estadual")
        with patch.object(hf_sync.st, "session_state", {"candidate_group": "vereadores"}):
            self.assertEqual(
                hf_sync.hf_visualizacao_path(config),
                "hf://buckets/owner/dashboard/dados/dep_estadual",
            )

    def test_canonical_paths_preserve_candidate_and_year(self):
        relative = "dep_estadual/12345_nome_sobrenome/2026/territorio/stage01a_municipios.parquet"
        for path in (relative, "hf://buckets/owner/dashboard/" + relative,
                     "buckets/owner/dashboard/" + relative, relative.replace("/", "\\")):
            with self.subTest(path=path):
                parsed = hf_sync.deputado_parts(path)
                self.assertEqual(parsed["cargo"], "Deputado Estadual")
                self.assertEqual(parsed["pasta"], "12345_nome_sobrenome")
                self.assertEqual(parsed["nome"], "Nome Sobrenome")
                self.assertEqual(parsed["ano"], "2026")

    def test_other_groups_and_nonannual_folders_are_ignored(self):
        for path in (
            "vereadores/candidato/2026/territorio/stage01a_municipios.parquet",
            "dep_estaduais/candidato/2026/territorio/stage01a_municipios.parquet",
            "dep_estadual/candidato/bh_2026/territorio/stage01b_bairros.parquet",
            "dep_estadual/candidato/26/territorio/stage01a_municipios.parquet",
            "IBGE/malha_mapas/MG_municipios_2022.parquet",
        ):
            with self.subTest(path=path):
                self.assertIsNone(hf_sync.deputado_parts(path))

    def test_index_and_files_keep_candidates_and_annual_data_separate(self):
        files = [
            "dep_estadual/candidato/2022/territorio/stage01a_municipios.parquet",
            "dep_estadual/candidato/2026/territorio/stage01a_municipios.parquet",
            "dep_estadual/candidato/2030/territorio/stage01a_municipios.parquet",
            "dep_estadual/outro/2022/territorio/stage01a_municipios.parquet",
            "dep_estadual/outro/2024/territorio/stage01a_municipios.parquet",
            "dep_estadual/apenas_bh/bh_2026/territorio/stage01b_bairros.parquet",
            "vereadores/candidato/2026/territorio/stage01a_municipios.parquet",
        ]
        rows = hf_sync.deputados_index(files)
        self.assertEqual([(row["Pasta"], row["Ano"]) for row in rows],
                         [("candidato", "2026"), ("outro", "2024")])
        filters = {"pasta": "candidato", "cargo": "Deputado Estadual", "ano": "2026"}
        self.assertEqual(hf_sync.selected_deputado_files(files, filters), [files[1]])
        self.assertEqual(hf_sync.selected_deputado_files(files, {"pasta": "Todos"}), [])

    def test_discovery_lists_only_candidate_folders_with_annual_data(self):
        root = "buckets/owner/dashboard/dep_estadual"
        folders = {
            root: [f"{root}/candidato", f"{root}/IBGE", f"{root}/apenas_bh"],
            f"{root}/candidato": [f"{root}/candidato/2026"],
            f"{root}/apenas_bh": [f"{root}/apenas_bh/bh_2026"],
        }
        fs = Mock()
        fs.ls.side_effect = lambda path, **kwargs: folders[path]
        expected = f"{root}/candidato/2026/territorio/stage01a_municipios.parquet"
        fs.find.return_value = [expected, f"{root}/candidato/notas.txt"]
        hf_sync.remote_data_files.clear()
        self.addCleanup(hf_sync.remote_data_files.clear)
        with patch("hf_sync.hf_filesystem", return_value=fs):
            self.assertEqual(hf_sync.remote_data_files(root, None), [expected])
        fs.find.assert_called_once_with(f"{root}/candidato")

    def test_sidebar_has_only_candidates_and_preserves_selection(self):
        files = [f"dep_estadual/{slug}/2026/territorio/stage01a_municipios.parquet"
                 for slug in ("amanda", "lud_falcao")]
        app = AppTest.from_file(str(ROOT / "app.py"))
        # Leave the page renderer out of this sidebar test; it would read map data.
        with patch("hf_sync.data_files", return_value=files), patch("streamlit.navigation"):
            app.run()
            self.assertEqual(list(app.exception), [])
            self.assertEqual([widget.label for widget in app.selectbox], ["Candidato"])
            self.assertEqual(app.selectbox[0].options, ["Amanda", "Lud Falcão"])
            app.selectbox[0].select("lud_falcao").run()
            app.run()
            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.session_state["deputados_filters"]["pasta"], "lud_falcao")
            with patch("eleitoral.common.shared_header.st.session_state", app.session_state):
                self.assertEqual(selected_deputado_label()["cargo"], "DEPUTADO ESTADUAL")

    def test_missing_bucket_folder_reports_once_without_retrying_in_each_section(self):
        fs = Mock()
        fs.open.side_effect = FileNotFoundError("Map data omitted in this test")
        with patch("hf_sync.remote_data_files", side_effect=FileNotFoundError("missing folder")) as listing, patch(
            "eleitoral.maps.dna_geo_reference.hf_filesystem", return_value=fs,
        ), patch(
            "eleitoral.dna.sector_expansion.municipality_options", return_value=[],
        ):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(listing.call_count, 1)
            self.assertEqual(len(app.error), 1)
            self.assertIn("HF_VISUALIZACAO_PREFIX", app.error[0].value)
            self.assertNotIn("HF_TOKEN", app.error[0].value)
            self.assertTrue(app.sidebar.selectbox[0].disabled)
            app.sidebar.button(key="raiox-nav-dna").click().run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(len(app.error), 1)

    def test_sidebar_navigation_preserves_candidate_between_pages(self):
        fs = Mock()
        fs.open.side_effect = FileNotFoundError("Map data omitted in this test")
        files = [f"dep_estadual/{slug}/2026/territorio/stage01a_municipios.parquet"
                 for slug in ("amanda", "lud_falcao")]
        with patch("hf_sync.remote_data_files", return_value=files), patch(
            "hf_sync.hf_filesystem", return_value=fs,
        ), patch(
            "eleitoral.maps.dna_geo_reference.hf_filesystem", return_value=fs,
        ), patch(
            "eleitoral.dna.sector_expansion.municipality_options", return_value=[],
        ):
            app = AppTest.from_file(str(ROOT / "app.py")).run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual([button.label for button in app.sidebar.button],
                             ["RaioX Territorial", "DNA do Eleitor", "DRE Campanha", "Impacto político"])
            self.assertEqual(app.sidebar.button(key="raiox-nav-active").label, "RaioX Territorial")
            self.assertFalse(any(button.label in {"RaioX Territorial", "DNA do Eleitor"}
                                 for button in app.main.button))
            app.sidebar.selectbox[0].select("lud_falcao").run(timeout=20)
            selected = dict(app.session_state["deputados_filters"])
            self.assertEqual(selected["pasta"], "lud_falcao")
            rendered = "\n".join(
                [item.value for item in app.markdown]
                + [item.proto.body for item in app.get("html")]
            )
            self.assertNotIn("Mapa da atuação parlamentar", rendered)
            self.assertNotIn("Força da política local", rendered)
            self.assertNotIn("Como foi sua votação em Belo Horizonte", rendered)
            self.assertNotIn("EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO", rendered)
            self.assertNotIn("EFICIÊNCIA FINANCEIRA &amp; CUSTO DO VOTO", rendered)
            app.sidebar.button(key="raiox-nav-dna").click().run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.sidebar.button(key="raiox-nav-active").label, "DNA do Eleitor")
            self.assertEqual(app.session_state["deputados_filters"], selected)
            rendered = "\n".join(
                [item.value for item in app.markdown]
                + [item.proto.body for item in app.get("html")]
            )
            self.assertIn("Identidade da Base Eleitoral", rendered)
            self.assertNotIn("Eleitor de BH x Eleitor do Interior", rendered)
            app.sidebar.button(key="raiox-nav-dre_campanha").click().run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.sidebar.button(key="raiox-nav-active").label, "DRE Campanha")
            self.assertEqual(app.session_state["deputados_filters"], selected)
            rendered = "\n".join(
                [item.value for item in app.markdown]
                + [item.proto.body for item in app.get("html")]
            )
            for title in (
                "EFICIÊNCIA FINANCEIRA &amp; CUSTO DO VOTO",
                "BALANÇO MACRO &amp; LIQUIDEZ DE CAIXA",
                "ESTRUTURA DA RECEITA",
                "Contratado × Pago",
                "DA ORIGEM AO DESTINO: O CAMINHO DOS RECURSOS",
            ):
                self.assertIn(title, rendered)
            app.sidebar.button(key="raiox-nav-impacto_politico").click().run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.sidebar.button(key="raiox-nav-active").label, "Impacto político")
            self.assertEqual(app.session_state["deputados_filters"], selected)
            rendered = "\n".join(
                [item.value for item in app.markdown]
                + [item.proto.body for item in app.get("html")]
            )
            for title in (
                "Força da política local",
                "Mapa da atuação parlamentar de acordo com os votos",
            ):
                self.assertTrue(title in rendered, title)
            self.assertNotIn("EFICIÊNCIA FINANCEIRA &amp; CUSTO DO VOTO", rendered)
            app.sidebar.button(key="raiox-nav-raio_x").click().run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.sidebar.button(key="raiox-nav-active").label, "RaioX Territorial")
            self.assertEqual(app.session_state["deputados_filters"], selected)


if __name__ == "__main__":
    unittest.main()
