import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eleitoral.common.local_political_strength import LOCAL_STRENGTH_SELECTION_KEY


class PoliticalImpactPageTests(unittest.TestCase):
    def setUp(self):
        self.root = "dep_estadual/candidato/2026/"
        municipalities = ["Cidade A", "Cidade B", "Cidade C", "Cidade D"]
        self.frames = {
            "territorio/stage01a_municipios.parquet": pd.DataFrame([
                dict(cd_municipio=str(10 * (i + 1)), cd_ibge_municipio=str(i + 1),
                     nm_municipio=name, nivel_territorial="municipio", qt_votos=votes,
                     qt_votos_validos_municipio=1000, pct_market_share=votes / 10,
                     sg_partido="TESTE", rank_municipio=i + 1)
                for i, (name, votes) in enumerate(zip(municipalities, (80, 20, 80, 20)))
            ]),
            "forca_local/stage07a_capital_local_municipios.parquet": pd.DataFrame([
                dict(cd_municipio=str(10 * (i + 1)), nm_municipio=name,
                     capital_local_0a100=score, sg_partido_prefeito_2024="TESTE",
                     vinculo_prefeito="mesmo_partido", ano_base_eleitos=2024)
                for i, (name, score) in enumerate(zip(municipalities, (80, 80, 20, 20)))
            ]),
            "forca_local/stage07b_afinidade_eleitos.parquet": pd.DataFrame([
                dict(cd_municipio="10", nm_municipio="Cidade A", cargo_eleito="prefeito",
                     nm_eleito="Prefeito A", sg_partido_eleito="TESTE",
                     vinculo_politico="mesmo_partido", afinidade_eleito_0a100=100),
            ]),
            "emendas/emendas_legislativa.parquet": pd.DataFrame([
                dict(cd_ibge_municipio=str(i + 1), valor_pago_atualizado=value,
                     valor_indicado=value, funcao_descricao="Saúde", tipo_indicacao="Individual")
                for i, value in enumerate((1000, 500))
            ]),
        }
        features = []
        for i in range(4):
            x = -44 + i * .1
            features.append(dict(
                type="Feature", properties=dict(id=str(i + 1)),
                geometry=dict(type="Polygon", coordinates=[[
                    [x, -20], [x + .1, -20], [x + .1, -19.9], [x, -19.9], [x, -20],
                ]]),
            ))
        geo_reference = (
            dict(type="FeatureCollection", features=features),
            pd.DataFrame([
                dict(codigo_tse=str(10 * (i + 1)), codigo_ibge=str(i + 1),
                     nome_municipio=name, municipio_norm=name.upper())
                for i, name in enumerate(municipalities)
            ]),
            pd.DataFrame([
                dict(codigo_ibge=str(i + 1), nome=name)
                for i, name in enumerate(municipalities)
            ]),
            pd.DataFrame(),
        )
        patches = [
            patch("hf_sync.load_env", return_value={
                "HF_BUCKET_URL": "hf://buckets/owner/dashboard",
                "HF_VISUALIZACAO_PREFIX": "dep_estadual",
            }),
            patch("eleitoral.common.shared_header.load_parquet", side_effect=self.read_frame),
        ]
        for module in (
            "eleitoral.maps.choropleth_maps", "eleitoral.common.local_political_strength",
            "eleitoral.deputados.emendas", "eleitoral.deputados.emendas_map",
        ):
            patches.append(patch(f"{module}.load_geo_reference", return_value=geo_reference))
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def read_frame(self, path, token=None):
        return self.frames[path.removeprefix(self.root)].copy()

    def page(self):
        app = AppTest.from_file(str(ROOT / "pages/impacto_politico.py"))
        app.session_state["deputados_files"] = [self.root + name for name in self.frames]
        app.session_state["deputados_filters"] = {
            "ano": "2026", "cargo": "Deputado Estadual", "pasta": "candidato", "nome": "Candidato",
        }
        app.session_state["selected_deputado_key"] = ("2026", "Deputado Estadual", "candidato")
        return app

    def test_page_renders_both_maps_shared_header_and_class_filter(self):
        app = self.page().run(timeout=20)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(list(app.warning), [])
        self.assertEqual(len(app.get("plotly_chart")), 2)
        markup = "\n".join(
            [item.proto.body for item in app.get("html")]
            + [item.value for item in app.markdown]
        )
        for text in (
            'class="raiox-hero-title">Impacto político', "NOME: CANDIDATO",
            "CARGO: DEPUTADO ESTADUAL", "PARTIDO: TESTE", "TOTAL DE VOTOS: 200",
            "Força da política local", "Mapa da atuação parlamentar de acordo com os votos",
            'class="raiox-kpi-grid"', 'class="raiox-parliament-card-stack"',
        ):
            self.assertTrue(text in markup, text)
        self.assertLess(markup.index("Força da política local"), markup.index("Mapa da atuação parlamentar"))
        self.assertEqual(len(app.button), 4)
        app.button(key="pagina1_forca_local_card_0").click().run(timeout=20)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state[LOCAL_STRENGTH_SELECTION_KEY], "Máquina eficiente")
        self.assertEqual(len(app.get("plotly_chart")), 2)
        app.button(key="pagina1_forca_local_card_0").click().run(timeout=20)
        self.assertEqual(list(app.exception), [])
        self.assertIsNone(app.session_state[LOCAL_STRENGTH_SELECTION_KEY])

    def test_local_map_click_opens_municipality_composition(self):
        with patch("eleitoral.common.local_political_strength._local_politics_map_selection", return_value={
            "codigo_ibge": "1", "municipio": "Cidade A", "classificacao": "Máquina eficiente",
        }):
            app = self.page().run(timeout=20)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.get("dialog")), 1)
        self.assertEqual(len(app.get("plotly_chart")), 3)
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(app.dataframe[0].value["Nome"].tolist(), ["Prefeito A"])
        self.assertEqual(next(item.value for item in app.metric if item.label == "Votos no município"), "80")

    def test_parliamentary_map_click_opens_amendment_details(self):
        with patch("eleitoral.deputados.emendas._parliamentary_map_selection", return_value={"codigo_ibge": "1"}):
            app = self.page().run(timeout=20)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.get("dialog")), 1)
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(app.dataframe[0].value["Finalidade"].tolist(), ["Saúde"])
        self.assertEqual(app.dataframe[0].value["Valor indicado"].tolist(), [1000])


if __name__ == "__main__":
    unittest.main()
