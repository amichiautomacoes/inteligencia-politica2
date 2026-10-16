from __future__ import annotations

import streamlit as st

from eleitoral.common.contracted_paid import (
    contracted_paid_cards_html,
    render_contracted_paid_chart,
    render_execution_filters,
)
from eleitoral.common.financial_cards import financial_cards_html
from eleitoral.common.financial_charts import render_financial_charts
from eleitoral.common.resource_sources import render_resource_flow
from eleitoral.common.revenue_structure import (
    render_revenue_charts,
    render_revenue_filters,
    render_revenue_kpis,
)
from eleitoral.common.shared_header import (
    apply_shared_visual_model,
    major_section_header,
    read_selected_parquet,
    render_page_header,
    section_header,
)


def _render_campaign_finances() -> None:
    major_section_header(
        "EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO",
        "Análise do retorno do investimento eleitoral: veja onde o orçamento foi alocado e quanto custou a conquista de cada voto.",
    )
    section_header(
        "BALANÇO MACRO & LIQUIDEZ DE CAIXA",
        "Raio-x executivo da arrecadação e dos compromissos financeiros: monitore o saldo real de caixa, o volume contratado e a saúde orçamentária da campanha.",
        compact=True,
    )
    financial_summary = read_selected_parquet("resumo_financeiro")
    st.markdown(financial_cards_html(financial_summary), unsafe_allow_html=True)
    render_financial_charts(financial_summary)

    section_header(
        "ESTRUTURA DA RECEITA",
        "Origem e concentração dos recursos da campanha",
        compact=True,
    )
    donor_summary = read_selected_parquet("concentracao_doadores")
    donor_summary, top_only = render_revenue_filters(donor_summary)
    render_revenue_kpis(donor_summary, donor_type=None)
    render_revenue_charts(donor_summary, top_only=top_only)

    section_header(
        "Contratado × Pago",
        "A importância da análise de passivos, prazos e distorções entre contratos e pagamentos.",
        compact=True,
    )
    execution_summary = read_selected_parquet("execucao_resumo")
    execution_filtered, execution_breakdown = render_execution_filters(execution_summary)
    st.html(contracted_paid_cards_html(execution_filtered, execution_breakdown))
    render_contracted_paid_chart(
        execution_summary if execution_breakdown == "global" else execution_filtered,
        None if execution_breakdown == "global" else execution_breakdown,
    )

    section_header(
        "DA ORIGEM AO DESTINO: O CAMINHO DOS RECURSOS",
        "Cruze as fontes de financiamento (FEFC, Fundo Partidário e Doações) com os pagamentos efetuados por categoria e fornecedor para entender para onde foi cada real da campanha.",
        compact=True,
    )
    render_resource_flow(
        read_selected_parquet("receita_despesa_fontes"),
        read_selected_parquet("destinacao_fontes"),
    )


apply_shared_visual_model()
render_page_header("dre_campanha")
_render_campaign_finances()
