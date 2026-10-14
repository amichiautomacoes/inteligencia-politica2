import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eleitoral.maps import dna_geo_reference as geo
from eleitoral.maps import territorial_mesh as maps
from eleitoral.common.bh_neighborhood_voting import bh_neighborhood_frame
from eleitoral.dna.sector_expansion import neighborhood_counts, municipal_potential_frame, municipal_potential_hover_frame
from eleitoral.dna import dna_expansion


class CrosswalkGeometryTests(unittest.TestCase):
    def test_dna_sector_hover_recovers_names_and_only_shows_zero_for_missing_associations(self):
        sectors = pd.DataFrame({"code_tract": ["10", "20", "30", "40"]})
        scores = pd.DataFrame({"setor": ["10", "20"], "classe_expansao": ["AZUL", "CINZA"], "votos_base": [4.5, None], "oportunidade_demografica": [120, None], "similaridade": [12, None]})
        links = pd.DataFrame({"cd_ibge_municipio": ["3106200"] * 4 + ["3101631"], "id_unidade": ["10", "10", "20", "30", "30"], "cd_bairro": ["A", "A", "B", "C", "D"], "nm_bairro": ["Centro", " Centro ", "Parque", "", "Outra cidade"], "nm_bairro_atribuido": [None, None, None, "Viúva", None], "geometry": [box(0, 0, 1, 1)] * 5})
        frame = municipal_potential_frame(sectors, scores, links)
        hover = municipal_potential_hover_frame(frame, links, "3106200").set_index("setor")
        self.assertEqual(hover.loc["10", "nome"], "Bairro: Centro")
        self.assertEqual(hover.loc["10", "votos_base_label"], "4,5")
        self.assertEqual(hover.loc["10", "similaridade_label"], "12,0%")
        self.assertEqual(hover.loc["20", "votos_base_label"], "Indisponível")
        self.assertEqual(hover.loc["20", "similaridade_label"], "Indisponível")
        self.assertEqual(hover.loc["30", "nome"], "Bairro: Viúva")
        self.assertEqual(hover.loc["30", "votos_base_label"], "0")
        self.assertEqual(hover.loc["40", "nome"], "Bairro sem referência disponível")
        self.assertEqual(hover.loc["40", "votos_base_label"], "0")
        self.assertTrue(pd.isna(hover.loc["40", "votos_base"]))
        self.assertEqual(hover.loc["40", "classe_expansao"], "CINZA")
        empty = municipal_potential_hover_frame(municipal_potential_frame(sectors, pd.DataFrame(), links), links, "3106200")
        self.assertEqual(empty["votos_base_label"].tolist(), ["0"] * 4)

    def test_dna_state_hover_shows_municipal_name_and_zero_for_unassociated_city(self):
        reference = pd.DataFrame({"codigo_ibge": ["3106200", "3101631", "3106705"], "nome": ["Belo Horizonte", "Alfredo Vasconcelos", "Betim"]})
        geography = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"id": code}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}} for code in reference.codigo_ibge]}
        scores = pd.DataFrame({"codigo_ibge": ["3106200", "3106705"], "votos_base": [8, None], "oportunidade_demografica": [100, None], "similaridade": [10, None], "diferenca_media_absoluta": [None, None], "dimensoes_com_dados": [1, 0], "classe_expansao": ["AZUL", "CINZA"]})
        with patch.object(dna_expansion, "load_geo_reference", return_value=(geography, None, reference, None)):
            fig = dna_expansion._expansion_map(scores, diagnostic=True)
        values = {str(location): (name, list(data)) for trace in fig.data for location, name, data in zip(trace.locations, trace.hovertext, trace.customdata)}
        self.assertEqual(values["3101631"][0], "Alfredo Vasconcelos")
        self.assertEqual(values["3101631"][1][1:], ["0", "Indisponível", "Indisponível"])
        self.assertEqual(values["3106705"][1][1], "Indisponível")
        self.assertEqual(values["3106200"][1][3], "10,0%")

    def test_bh_missing_record_uses_official_name_and_zero_but_preserves_unknown_votes(self):
        mesh = pd.DataFrame({"id": ["1", "2", "3"], "reference_name": ["Oficial", "Sem registro", "Desconhecido"], "geometry": [box(0, 0, 1, 1)] * 3})
        votes = pd.DataFrame({"cd_ibge_municipio": ["3106200"] * 2, "cd_ibge_bairro": ["1", "3"], "cd_bairro": ["A", "C"], "nm_bairro": ["Nome TSE", "Nome C"], "qt_votos": [12, None]})
        frame = bh_neighborhood_frame(mesh, votes).set_index("id")
        self.assertEqual(frame.loc["1", "name"], "Nome TSE")
        self.assertEqual(frame.loc["2", "name"], "Sem registro")
        self.assertEqual(frame.loc["2", "total_label"], "0")
        self.assertEqual(frame.loc["2", "details"], "Sem registro: 0 votos")
        self.assertEqual(frame.loc["3", "total_label"], "Indisponível")

    def test_complete_sector_loader_preserves_unlinked_ibge_polygons(self):
        official_shape, linked_shape = box(0, 0, 1, 1), box(0, 0, .9, .9)
        official = pd.DataFrame({"code_tract": ["10", "20"], "geometry": [official_shape, official_shape]})
        linked = pd.DataFrame({"code_tract": ["10"], "geometry": [linked_shape]})
        with patch.object(geo, "load_complete_municipality_sectors", return_value=official), patch.object(geo, "crosswalk_mesh", return_value=linked):
            mesh = geo.load_municipality_sectors.__wrapped__("3101631")
        self.assertEqual(mesh["code_tract"].tolist(), ["10", "20"])
        self.assertTrue(mesh.iloc[0].geometry.equals(linked_shape))
        self.assertTrue(mesh.iloc[1].geometry.equals(official_shape))

    def test_complete_mesh_keeps_unlinked_and_undiagnosed_sectors_gray(self):
        sectors = pd.DataFrame({"code_tract": ["10", "20", "30", "40"]})
        scores = pd.DataFrame({"setor": ["10", "20"], "classe_expansao": ["VERDE", "AZUL"]})
        links = pd.DataFrame({"id_unidade": ["10", "30"], "cd_bairro": ["A", "B"], "geometry": [box(0, 0, 1, 1)] * 2})
        frame = municipal_potential_frame(sectors, scores, links)
        self.assertEqual(frame.set_index("setor")["classe_expansao"].to_dict(), {"10": "VERDE", "20": "CINZA", "30": "CINZA", "40": "CINZA"})
        self.assertEqual(neighborhood_counts(frame, links).to_dict(), {"VERDE": 1, "CINZA": 1})

    def test_cards_count_unique_neighborhoods_per_sector_class(self):
        frame = pd.DataFrame({"setor": ["10", "20", "30"], "classe_expansao": ["AZUL", "AZUL", "CINZA"]})
        links = pd.DataFrame({"id_unidade": ["10", "10", "20", "30", "30", "99"], "cd_bairro": ["A", "B", "A", "A", None, "C"]})
        self.assertEqual(neighborhood_counts(frame, links).to_dict(), {"AZUL": 2, "CINZA": 1})

    def setUp(self):
        self.links = pd.DataFrame({
            "cd_ibge_municipio": ["3101631"] * 4 + ["3106200"],
            "cd_bairro": ["001", "002", "003", "003", "001"],
            "id_unidade": ["10", "10", "20", "30", "99"],
            "nm_bairro": ["A", "B", "C", "C", "Other city"],
            "geometry": [box(0, 0, 1, 1)] * 5,
        })

    def test_shared_polygons_are_unique_and_joins_preserve_votes(self):
        rows = pd.DataFrame({"cd_bairro": ["001", "002", "003", "004"], "qt_votos": [10, 20, 30, 40]})
        with patch.object(geo, "load_crosswalk_geometry", return_value=self.links):
            for kind in ("setor",):
                mesh = geo.crosswalk_mesh(kind, "3101631")
                self.assertEqual(len(mesh), 3)
                joined = geo.attach_crosswalk_units(rows, kind, "3101631")
                self.assertEqual(len(joined), len(rows))
                self.assertEqual(joined["qt_votos"].sum(), 100)
                self.assertEqual(joined["_code"].iloc[:2].tolist(), ["10", "10"])
                self.assertTrue(joined["_code"].iloc[2:].isna().all())
                self.assertEqual(joined.groupby("_code")["qt_votos"].sum().to_dict(), {"10": 30})

    def test_codes_keep_tse_text_and_leading_zeroes(self):
        values = pd.Series([3101631.0, "001", "40002_BAIRRO:CENTRO", None])
        normalized = geo.territorial_codes(values)
        self.assertEqual(normalized.iloc[:3].tolist(), ["3101631", "001", "40002_BAIRRO:CENTRO"])
        self.assertTrue(pd.isna(normalized.iloc[3]))

    def test_vote_map_uses_crosswalk_without_candidate_sector_or_area_columns(self):
        rows = pd.DataFrame({
            "cd_ibge_municipio": ["3101631", "3101631"],
            "cd_bairro": ["001", "002"], "nm_bairro": ["A", "B"], "qt_votos": [10, 20],
        })
        with patch.object(geo, "load_crosswalk_geometry", return_value=self.links), patch.object(maps, "load_tse_neighborhood_sector_crosswalk", return_value=self.links):
            for kind, column in (("setor", "code_tract"),):
                mesh = geo.crosswalk_mesh(kind, "3101631")
                with patch.object(maps, "municipality_mesh", return_value=(kind, mesh, column, column)), patch.object(maps, "_municipality_geometry", return_value=box(0, 0, 1, 1)):
                    figure, count = maps.municipality_mesh_map("3101631", rows, candidate_neighborhood_details=True)
                self.assertIsNotNone(figure)
                self.assertEqual(count, 3)
                trace = next(t for t in figure.data if t.type == "choropleth")
                self.assertEqual(len(trace.geojson["features"]), 3)
                self.assertEqual(trace.colorscale[0][1], "#94a3b8")
                self.assertEqual(list(trace.customdata[0]), ["0", "C: 0 votos"])
                self.assertEqual(list(trace.customdata[1]), ["0", "C: 0 votos"])
                self.assertTrue(any(t.type == "scattergeo" for t in figure.data))

    def test_mesh_selection_never_loads_weighted_areas(self):
        municipality = pd.DataFrame({"code_muni": ["3101631"], "geometry": [box(0, 0, 1, 1)]})
        neighborhoods = pd.DataFrame({"code_muni": ["3101631"], "code_neighborhood": ["1"], "name_neighborhood": ["A"], "geometry": [box(0, 0, 1, 1)]})

        def layer(kind):
            self.assertIn(kind, {"municipio", "bairro"})
            return municipality if kind == "municipio" else neighborhoods

        sectors = pd.DataFrame({"code_tract": ["10"], "geometry": [box(0, 0, 1, 1)]})
        with patch.object(maps, "load_geo_layer", side_effect=layer), patch.object(maps, "load_municipality_sectors", return_value=sectors) as read_sectors:
            self.assertEqual(maps.municipality_mesh("3101631")[0], "bairro")
            read_sectors.assert_not_called()
            self.assertEqual(maps.municipality_mesh("3101631", allow_neighborhoods=False)[0], "setor")
            neighborhoods.loc[0, "geometry"] = box(0, 0, .1, .1)
            self.assertEqual(maps.municipality_mesh("3101631")[0], "setor")


if __name__ == "__main__":
    unittest.main()
