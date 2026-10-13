import unittest

import pandas as pd

from src.eleitoral.common.resource_sources import funding_sources_figure, destination_table


class FundingSourcesTests(unittest.TestCase):
    def test_destination_filters_do_not_mix_category_and_supplier(self):
        frame = pd.DataFrame([
            dict(fonte_chave="fefc", recorte="categoria", grupo_descricao="Impulsionamento", valor_pago=100, pct_total_pago=25),
            dict(fonte_chave="fefc", recorte="fornecedor", grupo_descricao="Empresa", nr_cpf_cnpj_fornecedor="00123456789012", valor_pago=100, pct_total_pago=25),
            dict(fonte_chave="outros", recorte="categoria", grupo_descricao="Pessoal", valor_pago=300, pct_total_pago=75),
        ])
        table = destination_table(frame, "fefc", "categoria")
        self.assertEqual(table["grupo_descricao"].tolist(), ["Impulsionamento"])
        self.assertEqual(table["pct_total_pago"].tolist(), [25])
        supplier = destination_table(frame, "fefc", "fornecedor")
        self.assertEqual(supplier.iloc[0]["nr_cpf_cnpj_fornecedor"], "00123456789012")
        self.assertEqual(supplier.iloc[0]["valor_pago"], "R$ 100,00")
        self.assertEqual(len(destination_table(frame, None, "categoria")), 2)
        self.assertTrue(destination_table(frame, "partidario", "categoria").empty)
        self.assertTrue(destination_table(None, None, "categoria").empty)

    def test_preserves_financial_indicators_separate_from_total_revenue(self):
        frame = pd.DataFrame([
            dict(fonte_chave="a", fonte_descricao="FEFC", receita_total=100,
                 receita_financeira=80, despesa_paga=90,
                 saldo_financeiro_observado=-10, taxa_utilizacao_financeira_pct=112.5),
            dict(fonte_chave="b", fonte_descricao="Fundo Partidário", receita_total=20,
                 receita_financeira=0, despesa_paga=0,
                 saldo_financeiro_observado=0, taxa_utilizacao_financeira_pct=None),
        ])
        fig = funding_sources_figure(frame)
        self.assertEqual(list(fig.data[0].x), [100, 20])
        self.assertEqual(list(fig.data[1].x), [90, 0])
        self.assertEqual(fig.data[0].customdata[0][1:4], ["R$ -10,00", "112,5%", "R$ 80,00"])
        self.assertEqual(fig.data[0].customdata[1][2], "Indisponível")

    def test_missing_amounts_are_omitted_and_duplicate_sources_rejected(self):
        frame = pd.DataFrame([
            dict(fonte_chave="a", fonte_descricao="A", receita_total=0, despesa_paga=0),
            dict(fonte_chave="b", fonte_descricao="B", receita_total=100, despesa_paga=None),
        ])
        fig = funding_sources_figure(frame)
        self.assertEqual(fig.layout.meta["omitted"], 1)
        self.assertEqual(list(fig.data[0].x), [0])
        self.assertIsNone(funding_sources_figure(pd.concat([frame, frame])))
        self.assertIsNone(funding_sources_figure(None))
