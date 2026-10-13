import unittest
from decimal import Decimal

import pandas as pd

from src.eleitoral.common.revenue_structure import filter_donors, donor_audit_table, donor_concentration_figure, donor_kpis, top_donors_figure


class DonorKpiTests(unittest.TestCase):
    def test_concentration_separates_unattributed_revenue(self):
        frame = pd.DataFrame([dict(rank_doador=1, pct_receita_total=40, cobertura_atribuicao_pct=70)])
        fig = donor_concentration_figure(frame)
        self.assertEqual(list(fig.data[0].values), [40, 30, 30])
        self.assertIn("Receita sem origem atribuída", fig.data[0].labels)

    def test_audit_preserves_document_leading_zero_and_all_ranks(self):
        frame = pd.DataFrame([dict(rank_doador=11, nr_cpf_cnpj_doador="00123456789", valor_atribuido=10),
                              dict(rank_doador=1, nr_cpf_cnpj_doador="00000000001", valor_atribuido=100)])
        table = donor_audit_table(frame)
        self.assertEqual(table["rank_doador"].tolist(), [1, 11])
        self.assertEqual(table.iloc[1]["nr_cpf_cnpj_doador"], "00123456789")
        self.assertEqual(table.iloc[1]["valor_atribuido"], "R$ 10,00")
    def test_donor_chart_preserves_names_order_and_top10_scope(self):
        name = "Direção Estadual de um Partido com Nome Muito Longo em Minas Gerais"
        frame = pd.DataFrame([dict(rank_doador=2, nm_doador="Outro", valor_atribuido=50),
                              dict(rank_doador=1, nm_doador=name, valor_atribuido=100),
                              dict(rank_doador=11, nm_doador="Fora", valor_atribuido=1)])
        fig = top_donors_figure(frame)
        self.assertEqual(list(fig.data[0].x), [100, 50])
        self.assertEqual(fig.data[0].customdata[0][0], name)
        self.assertEqual(fig.layout.yaxis.ticktext[0].replace("<br>", " "), name)

    def test_donor_chart_hides_missing_values(self):
        frame = pd.DataFrame([dict(rank_doador=1, nm_doador="Doador", valor_atribuido=None)])
        self.assertIsNone(top_donors_figure(frame))
    def test_immediate_and_original_rankings_are_not_mixed(self):
        frame = pd.DataFrame([dict(tipo_doador="imediato", rank_doador=1, nm_doador="Partido",
                                   valor_atribuido=100, pct_receita_total=100, cobertura_atribuicao_pct=100),
                              dict(tipo_doador="originario", rank_doador=1, nm_doador="Origem",
                                   valor_atribuido=20, pct_receita_total=20, cobertura_atribuicao_pct=20)])
        values = donor_kpis(frame)
        self.assertEqual(values["name"], "Partido")
        self.assertEqual(values["coverage"], 100)
        self.assertEqual(values["count"], 1)
    def test_ranking_order_top10_sum_and_repeated_coverage(self):
        frame = pd.DataFrame([dict(rank_doador=i, nm_doador=f"Doador {i}",
                                   valor_atribuido=str(1000 / i), pct_receita_total=5,
                                   cobertura_atribuicao_pct=80) for i in range(12, 0, -1)])
        values = donor_kpis(frame)
        self.assertEqual(values["name"], "Doador 1")
        self.assertEqual(values["amount"], Decimal("1000.0"))
        self.assertEqual(values["top10"], 50)
        self.assertEqual(values["coverage"], 80)
        self.assertEqual(values["count"], 12)

    def test_missing_share_does_not_become_zero(self):
        frame = pd.DataFrame([dict(rank_doador=1, pct_receita_total=None)])
        self.assertIsNone(donor_kpis(frame)["top10"])
        self.assertIsNone(donor_kpis(frame)["coverage"])

    def test_fewer_than_ten_donors_and_inconsistent_coverage(self):
        frame = pd.DataFrame([dict(rank_doador=1, pct_receita_total=40, cobertura_atribuicao_pct=70),
                              dict(rank_doador=2, pct_receita_total=30, cobertura_atribuicao_pct=80)])
        values = donor_kpis(frame)
        self.assertEqual(values["top10"], 70)
        self.assertIsNone(values["coverage"])


class DonorFilterTests(unittest.TestCase):
    def test_original_type_top_flag_and_status_share_one_scope(self):
        frame = pd.DataFrame([
            dict(tipo_doador="imediato", rank_doador=1, eh_top10=True, situacao_atribuicao="completa"),
            dict(tipo_doador="originario", rank_doador=1, eh_top10=True, situacao_atribuicao="parcial", nm_doador="Fundo", valor_atribuido=20),
            dict(tipo_doador="originario", rank_doador=11, eh_top10=False, situacao_atribuicao="completa", nm_doador="Outro", valor_atribuido=10),
        ])
        selected = filter_donors(frame, "originario", True, "parcial")
        self.assertEqual(selected["nm_doador"].tolist(), ["Fundo"])
        self.assertEqual(donor_kpis(selected, donor_type=None)["name"], "Fundo")
        self.assertEqual(len(donor_audit_table(selected, donor_type=None)), 1)
        all_original = filter_donors(frame, "originario", False, "Todas as situações")
        self.assertEqual(list(top_donors_figure(all_original, donor_type=None, top_only=False).data[0].x), [20, 10])

    def test_missing_top_flag_falls_back_to_rank_without_promoting(self):
        frame = pd.DataFrame([dict(rank_doador=2), dict(rank_doador=11)])
        self.assertEqual(filter_donors(frame, "imediato", True, "Todas as situações")["rank_doador"].tolist(), [2])
        self.assertTrue(filter_donors(frame, "originario", False, "Todas as situações").empty)
