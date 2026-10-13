import unittest

import pandas as pd

from src.eleitoral.common.financial_charts import budget_commitment_figure, budget_funnel_figure, revenue_composition_figure


class RevenueCompositionTests(unittest.TestCase):
    def test_commitment_preserves_over_budget_percentage(self):
        fig = budget_commitment_figure(pd.DataFrame([dict(receita_total=100, despesa_contratada=150)]))
        self.assertEqual(fig.data[0].value, 150)
        self.assertEqual(list(fig.data[0].gauge.axis.range), [0, 150])

    def test_commitment_requires_positive_revenue_and_accepts_zero_expense(self):
        self.assertIsNone(budget_commitment_figure(pd.DataFrame([dict(receita_total=0, despesa_contratada=50)])))
        fig = budget_commitment_figure(pd.DataFrame([dict(receita_total=100, despesa_contratada=0)]))
        self.assertEqual(fig.data[0].value, 0)

    def test_funnel_preserves_source_total_and_obligations_above_revenue(self):
        frame = pd.DataFrame([dict(receita_total=100, receita_financeira=80,
                                   despesa_contratada=150, despesa_paga=50)])
        fig = budget_funnel_figure(frame)
        self.assertEqual(list(fig.data[0].x), [100, 80, 150, 50])
        self.assertEqual(list(fig.data[0].y), ["Receita Total", "Receita Financeira", "Despesa Contratada", "Despesa Paga"])

    def test_incomplete_funnel_does_not_invent_total(self):
        frame = pd.DataFrame([dict(receita_financeira=80, despesa_contratada=50, despesa_paga=40)])
        self.assertIsNone(budget_funnel_figure(frame))

    def test_chart_uses_only_financial_and_estimated_revenue(self):
        frame = pd.DataFrame([dict(receita_financeira=75, receita_estimavel=25, receita_total=999)])
        fig = revenue_composition_figure(frame)
        self.assertEqual(list(fig.data[0].values), [75, 25])
        self.assertEqual(fig.data[0].customdata[0][1], "75,0%")
        self.assertIn("100,00", fig.layout.annotations[0].text)

    def test_missing_negative_and_empty_totals_do_not_create_a_pie(self):
        for amounts in ((None, 10), (-1, 10), (0, 0)):
            frame = pd.DataFrame([dict(zip(("receita_financeira", "receita_estimavel"), amounts))])
            self.assertIsNone(revenue_composition_figure(frame))

    def test_one_zero_category_keeps_valid_composition(self):
        fig = revenue_composition_figure(pd.DataFrame([dict(receita_financeira=10, receita_estimavel=0)]))
        self.assertEqual(fig.data[0].customdata[0][1], "100,0%")
