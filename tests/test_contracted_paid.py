import unittest
from decimal import Decimal

import pandas as pd

from src.eleitoral.common.contracted_paid import execution_values, execution_badge, contracted_paid_cards_html, contracted_paid_figure, execution_scope


class ContractedPaidTests(unittest.TestCase):
    def test_scope_updates_cards_and_chart_without_mixing_breakdowns(self):
        frame = pd.DataFrame([
            dict(recorte="global", grupo_chave="global", grupo_descricao="Total", total_contratado=300, total_pago=200),
            dict(recorte="categoria", grupo_chave="a", grupo_descricao="Pessoal", total_contratado=100, total_pago=50),
            dict(recorte="categoria", grupo_chave="b", grupo_descricao="Publicidade", total_contratado=200, total_pago=150),
            dict(recorte="fornecedor", grupo_chave="a", grupo_descricao="Empresa", total_contratado=75, total_pago=30),
        ])
        for breakdown, amount in (("categoria", 100), ("fornecedor", 75)):
            selected = execution_scope(frame, breakdown, "a")
            self.assertEqual(execution_values(selected, breakdown)["total_contratado"], amount)
            self.assertEqual(list(contracted_paid_figure(selected, breakdown).data[0].x), [amount])
        self.assertTrue(execution_scope(frame, "fornecedor", "missing").empty)
        self.assertEqual(execution_values(execution_scope(frame, "global"))["total_contratado"], 300)

    def test_comparison_uses_one_breakdown_and_preserves_excess_payment(self):
        frame = pd.DataFrame([
            dict(recorte="global", grupo_chave="global", grupo_descricao="Total", total_contratado=120, total_pago=130),
            dict(recorte="categoria", grupo_chave="a", grupo_descricao="Pessoal", total_contratado=100, total_pago=0),
            dict(recorte="categoria", grupo_chave="b", grupo_descricao="Publicidade", total_contratado=20, total_pago=130),
        ])
        fig = contracted_paid_figure(frame)
        self.assertEqual(list(fig.data[0].x), [20, 100])
        self.assertEqual(list(fig.data[1].x), [130, 0])
        self.assertEqual(fig.data[1].customdata[0][2], "Pago acima do contratado")
        self.assertEqual(fig.layout.barmode, "group")

    def test_top_suppliers_and_missing_values(self):
        frame = pd.DataFrame([dict(recorte="fornecedor", grupo_chave=str(i), grupo_descricao=f"Fornecedor {i}",
                                   total_contratado=i, total_pago=i) for i in range(12)])
        fig = contracted_paid_figure(frame, "fornecedor")
        self.assertEqual(list(fig.data[0].x), list(range(11, 1, -1)))
        frame.loc[11, "total_pago"] = None
        fig = contracted_paid_figure(frame, "fornecedor")
        self.assertEqual(fig.layout.meta["omitted"], 1)
        self.assertEqual(len(fig.data[0].x), 9)
        self.assertIsNone(contracted_paid_figure(None))

    def test_global_row_avoids_double_counting(self):
        frame = pd.DataFrame([
            dict(recorte="categoria", total_contratado=100),
            dict(recorte="fornecedor", total_contratado=100),
            dict(recorte="global", total_contratado="100.01", total_pago=50, taxa_execucao_pct=150),
        ])
        values = execution_values(frame)
        self.assertEqual(values["total_contratado"], Decimal("100.01"))
        self.assertEqual(values["taxa_execucao_pct"], 150)
        self.assertEqual(execution_badge(values["taxa_execucao_pct"])[1], "warning")

    def test_missing_or_ambiguous_global_is_unavailable(self):
        frame = pd.DataFrame([dict(recorte="categoria", total_contratado=100)])
        self.assertIsNone(execution_values(frame)["total_contratado"])
        frame = pd.DataFrame([dict(recorte="global", total_contratado=100)] * 2)
        self.assertIsNone(execution_values(frame)["total_contratado"])
        self.assertIn("Indisponível", contracted_paid_cards_html(None))

    def test_zero_signed_delay_and_net_balance_are_preserved(self):
        frame = pd.DataFrame([dict(total_pago=0, saldo_liquido=-10,
                                   defasagem_media_conhecida_dias=-2, excesso_pago_conhecido="NaN")])
        values = execution_values(frame)
        self.assertEqual(values["total_pago"], 0)
        self.assertEqual(values["saldo_liquido"], -10)
        self.assertEqual(values["defasagem_media_conhecida_dias"], -2)
        self.assertIsNone(values["excesso_pago_conhecido"])
        markup = contracted_paid_cards_html(frame)
        self.assertIn("Saldo Líquido", markup)
        self.assertIn("-2,0 dias", markup)
        self.assertIn('<details class="execution-card execution-alerts">', markup)
