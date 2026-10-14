import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from shapely.geometry import box, mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eleitoral.common import statewide_elections as elections


class StatewideElectionTests(unittest.TestCase):
    def setUp(self):
        self.reference = pd.DataFrame({
            "codigo_ibge": ["1", "2", "3"], "nome": ["A", "B", "C"],
            "mesorregiao_nome": ["Região A", "Região A", "Região B"],
            "region_id": ["REGIAO A", "REGIAO A", "REGIAO B"],
        })
        self.source = pd.DataFrame({
            "nivel_territorial": ["municipio"] * 3,
            "cd_ibge_municipio": ["1", "2", "3"],
            "qt_votos": [30, 90, 0], "qt_votos_validos_municipio": [100, 900, 100],
            "qt_votos_candidato_2022": [10, 90, 0], "qt_votos_validos_2022": [100, 900, 100],
            "diff_market_share_pp_vs_2022": [20, 0, None],
        })
        self.tse = pd.DataFrame({"codigo_tse": ["10", "20", "30"], "codigo_ibge": ["1", "2", "3"]})
        self.diagnostic = pd.DataFrame({
            "cd_ibge_municipio_setor": ["1", "2"], "votos_obtidos_2026": [10, 20],
            "populacao_estimada_icp": [100, 300], "populacao_total_referencia": [1000, 1000],
            "cobertura_dados_completa": [True, True],
        })

    def test_missing_history_remains_unknown_and_valid_zero_is_preserved(self):
        self.source.loc[1, "qt_votos_candidato_2022"] = None
        adapted = elections.election_votes(self.source, "2022")
        self.assertTrue(pd.isna(adapted.loc[1, "qt_votos"]))
        self.assertEqual(adapted.loc[2, "qt_votos"], 0)
        self.assertEqual(self.source.loc[0, "qt_votos"], 30)
        self.assertIsNone(elections.election_votes(self.source, "2018"))
        self.source["qt_votos_candidato_2022"] = None
        self.assertIsNone(elections.election_votes(self.source, "2022"))

    def test_municipal_source_differences_and_exact_tse_keys(self):
        source = self.source.drop(columns="cd_ibge_municipio").assign(cd_municipio=["10.0", "20", "30"])
        frame = elections.historical_state_frame(source, "2022", "votos_municipio", self.reference, self.tse)
        self.assertEqual(frame["class"].tolist(), ["Aumento", "Estabilidade", "Sem comparação"])
        self.assertEqual(frame["past"].tolist(), [10, 90, 0])
        source.loc[1, "diff_market_share_pp_vs_2022"] = -2
        frame = elections.historical_state_frame(source, "2022", "votos_municipio", self.reference, self.tse)
        self.assertEqual(frame.loc[1, "class"], "Queda")

    def test_mesoregions_compare_summed_shares_instead_of_mean_differences(self):
        frame = elections.historical_state_frame(self.source, "2022", "votos_mesorregiao", self.reference, self.tse).set_index("id")
        self.assertAlmostEqual(frame.loc["REGIAO A", "diff"], 2)
        self.assertEqual(frame.loc["REGIAO A", "past"], 100)
        self.source.loc[1, "qt_votos_candidato_2022"] = None
        frame = elections.historical_state_frame(self.source, "2022", "votos_mesorregiao", self.reference, self.tse).set_index("id")
        self.assertEqual(frame.loc["REGIAO A", "class"], "Sem comparação")
        self.assertTrue(pd.isna(frame.loc["REGIAO A", "past"]))

    def test_ambiguous_municipal_records_are_not_double_counted(self):
        source = pd.concat([self.source, self.source.iloc[:1]], ignore_index=True)
        self.assertTrue(elections.historical_state_frame(source, "2022", "votos_municipio", self.reference, self.tse).empty)

    def test_projection_uses_dna_diagnostic_and_keeps_missing_units_gray(self):
        frame = elections.projection_state_frame(self.diagnostic, "votos_municipio", self.reference).set_index("id")
        self.assertEqual(frame.loc["2", "class"], "AZUL")
        self.assertEqual(frame.loc["3", "class"], "CINZA")
        frame = elections.projection_state_frame(self.diagnostic, "votos_mesorregiao", self.reference).set_index("id")
        self.assertEqual(frame.loc["REGIAO A", "oportunidade_demografica"], 400)
        self.assertEqual(frame.loc["REGIAO A", "reference"], 2000)
        self.assertEqual(frame.loc["REGIAO B", "class"], "CINZA")
        self.diagnostic.loc[1, "cobertura_dados_completa"] = False
        frame = elections.projection_state_frame(self.diagnostic, "votos_mesorregiao", self.reference).set_index("id")
        self.assertEqual(frame.loc["REGIAO A", "class"], "CINZA")
        self.assertTrue(elections.projection_state_frame(None, "votos_municipio", self.reference).empty)

    def test_figures_preserve_all_polygons_and_territorial_click_names(self):
        def feature(code):
            return {"type": "Feature", "properties": {"id": code}, "geometry": mapping(box(0, 0, 1, 1))}
        geography = {"type": "FeatureCollection", "features": [feature(code) for code in ["1", "2", "3"]],
                     "mesoregions": {"type": "FeatureCollection", "features": [feature("Região A"), feature("Região B")]}}
        municipalities = self.reference[["codigo_ibge", "nome"]]
        regions = self.reference[["codigo_ibge", "mesorregiao_nome"]]
        with patch.object(elections, "load_geo_reference", return_value=(geography, self.tse, municipalities, regions)):
            for kind, count in (("votos_municipio", 3), ("votos_mesorregiao", 2)):
                history = elections.statewide_election_map(self.source, kind, "2022")
                self.assertEqual(len(history.data[0].locations), count)
                self.assertEqual(len(history.data[0].geojson["features"]), count)
                self.assertIn("Votos 2022", history.data[0].hovertemplate)
                self.assertIn("Votos 2026", history.data[0].hovertemplate)
                projection = elections.statewide_election_map(self.source, kind, "Projeção 2030", self.diagnostic)
                self.assertEqual(len(projection.data[0].locations), count)
                if kind == "votos_mesorregiao":
                    self.assertEqual(history.data[0].customdata[0][0], "Região A")
                    self.assertEqual(set(history.data[0].locations), {"REGIAO A", "REGIAO B"})
            self.assertIsNone(elections.statewide_election_map(self.source, "votos_municipio", "2018"))


if __name__ == "__main__":
    unittest.main()
