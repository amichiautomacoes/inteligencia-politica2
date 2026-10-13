from decimal import Decimal
import unittest

import pandas as pd

from src.eleitoral.common.financial_cards import financial_cards_html, financial_values


class FinancialCardsTests(unittest.TestCase):
    def test_liquidity_excludes_donated_goods_and_uses_exact_cents(self):
        frame = pd.DataFrame([dict(receita_financeira="100.10", receita_estimavel="9000",
                                   despesa_contratada="150.30", despesa_paga="120.20")])
        values = financial_values(frame)
        self.assertEqual(values["resultado"], Decimal("-20.10"))
        self.assertEqual(values["saldo_a_pagar"], Decimal("30.10"))
        self.assertIn("Déficit temporário de liquidez", financial_cards_html(frame))

    def test_missing_values_are_not_zero_but_reported_zero_is_valid(self):
        values = financial_values(pd.DataFrame([dict(receita_financeira=0, despesa_paga=None)]))
        self.assertEqual(values["receita_financeira"], Decimal(0))
        self.assertIsNone(values["resultado"])
        self.assertIn("Indisponível", financial_cards_html(None))

    def test_multiple_summaries_are_not_added(self):
        frame = pd.DataFrame([dict(receita_financeira=10)] * 2)
        self.assertIsNone(financial_values(frame)["receita_financeira"])


if __name__ == "__main__":
    unittest.main()
