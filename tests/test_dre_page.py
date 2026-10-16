import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class CampaignFinancialPageTests(unittest.TestCase):
    def test_page_reads_all_financial_sources_and_renders_existing_charts_and_filters(self):
        root = "dep_estadual/candidato/2026/"
        frames = {
            "territorio/stage01a_municipios.parquet": pd.DataFrame([dict(qt_votos=100, sg_partido="TESTE")]),
            "gastos/stage05a_resumo_financeiro.parquet": pd.DataFrame([dict(
                receita_total=1000, receita_financeira=800, receita_estimavel=200,
                despesa_contratada=600, despesa_paga=400,
            )]),
            "gastos/stage05b_concentracao_doadores.parquet": pd.DataFrame([
                dict(tipo_doador=kind, rank_doador=1, nm_doador=name, valor_atribuido=200,
                     pct_receita_total=20, cobertura_atribuicao_pct=100, situacao_atribuicao="completa",
                     qt_vinculos_pendentes=0, eh_top10=True, qt_receitas_vinculadas=1)
                for kind, name in (("imediato", "Doador imediato"), ("originario", "Doador originário"))
            ]),
            "gastos/stage05d_execucao_resumo.parquet": pd.DataFrame([
                dict(recorte="global", grupo_chave="global", grupo_descricao="Total",
                     total_contratado=600, total_pago=400, taxa_execucao_pct=400 / 6, saldo_em_aberto=200),
                dict(recorte="categoria", grupo_chave="divulgacao", grupo_descricao="Divulgação",
                     total_contratado=300, total_pago=100, taxa_execucao_pct=100 / 3, saldo_em_aberto=200),
                dict(recorte="fornecedor", grupo_chave="empresa", grupo_descricao="Empresa",
                     total_contratado=300, total_pago=100, taxa_execucao_pct=100 / 3, saldo_em_aberto=200),
            ]),
            "gastos/stage05e_receita_despesa_fontes.parquet": pd.DataFrame([dict(
                fonte_chave="fefc", fonte_descricao="FEFC", receita_total=1000, receita_financeira=800,
                despesa_paga=400, saldo_financeiro_observado=400, taxa_utilizacao_financeira_pct=50,
            )]),
            "gastos/stage05e_destinacao_fontes.parquet": pd.DataFrame([
                dict(fonte_chave="fefc", fonte_descricao="FEFC", recorte=kind,
                     grupo_descricao=name, valor_pago=400, pct_total_pago=100)
                for kind, name in (("categoria", "Divulgação"), ("fornecedor", "Empresa"))
            ]),
        }
        files = [root + name for name in frames]
        app = AppTest.from_file(str(ROOT / "pages/dre_campanha.py"))
        app.session_state["deputados_files"] = files
        app.session_state["deputados_filters"] = {
            "ano": "2026", "cargo": "Deputado Estadual", "pasta": "candidato", "nome": "Candidato",
        }
        app.session_state["selected_deputado_key"] = ("2026", "Deputado Estadual", "candidato")
        config = {"HF_BUCKET_URL": "hf://buckets/owner/dashboard", "HF_VISUALIZACAO_PREFIX": "dep_estadual"}

        def read_frame(path, token=None):
            return frames[path.removeprefix(root)].copy()

        with patch("hf_sync.load_env", return_value=config), patch(
            "eleitoral.common.shared_header.load_parquet", side_effect=read_frame,
        ) as reader:
            app.run(timeout=20)
            self.assertEqual(list(app.exception), [])
            self.assertEqual(list(app.warning), [])
            self.assertGreaterEqual(len(app.get("plotly_chart")), 6)
            self.assertGreaterEqual(len(app.dataframe), 2)
            self.assertEqual({call.args[0] for call in reader.call_args_list}, set(files))
            markup = "\n".join(item.proto.body for item in app.get("html"))
            self.assertIn('class="raiox-hero-title">DRE Campanha', markup)
            self.assertIn("NOME: CANDIDATO", markup)
            self.assertIn("CARGO: DEPUTADO ESTADUAL", markup)
            self.assertIn("TOTAL DE VOTOS: 100", markup)

            donor_type = next(widget for widget in app.selectbox if widget.label == "Tipo de Doador")
            donor_type.select("originario").run(timeout=20)
            self.assertEqual(list(app.exception), [])
            breakdown = next(widget for widget in app.selectbox if widget.label == "Recorte da análise")
            breakdown.select("categoria").run(timeout=20)
            self.assertEqual(list(app.exception), [])
            category = next(widget for widget in app.selectbox if widget.label == "Categoria de Despesa")
            self.assertEqual(category.options, ["Divulgação"])
            destination = next(widget for widget in app.selectbox if widget.label == "Destinação por")
            destination.select("fornecedor").run(timeout=20)
            self.assertEqual(list(app.exception), [])


if __name__ == "__main__":
    unittest.main()
