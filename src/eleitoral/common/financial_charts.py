"""Revenue composition in the dashboard's shared visual style."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .financial_cards import _indicator, _money, financial_values


REVENUE_LABELS = ("Entrada Financeira (Dinheiro)", "Bens e Serviços (Estimável)")
REVENUE_COLORS = ("#2563eb", "#38bdf8")


def revenue_composition_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    values = financial_values(frame)
    amounts = [values["receita_financeira"], values["receita_estimavel"]]
    if any(value is None or value < 0 for value in amounts):
        return None
    total = sum(amounts)
    if total <= 0:
        return None
    shares = [value / total * 100 for value in amounts]
    percentages = [f"{share:.1f}%".replace(".", ",") for share in shares]
    fig = go.Figure(go.Pie(
        labels=REVENUE_LABELS, values=[float(value) for value in amounts],
        hole=0.6, sort=False,
        marker={"colors": REVENUE_COLORS, "line": {"color": "rgba(7,24,54,.75)", "width": 1.5}},
        customdata=[[_money(value), percent] for value, percent in zip(amounts, percentages)],
        hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>%{customdata[1]} das receitas<extra></extra>",
        text=[percent if share >= 1 else "" for share, percent in zip(shares, percentages)],
        textinfo="text", textposition="outside", automargin=True,
        textfont={"color": "#f8fbff", "size": 14}, showlegend=False,
    ))
    fig.update_layout(
        height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        margin={"l": 42, "r": 42, "t": 18, "b": 18},
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
        annotations=[{
            "x": 0.5, "y": 0.5, "showarrow": False,
            "text": f"<b>{_money(total)}</b><br><span style='font-size:12px;color:#b7c7e6'>Total de receitas</span>",
            "font": {"size": 20, "color": "#f8fbff"},
        }],
    )
    return fig


def render_revenue_composition(frame: pd.DataFrame | None) -> None:
    with st.container(border=True, key="pagina1_revenue_composition"):
        st.markdown("### Composição das Receitas")
        st.caption("Entrada financeira e doações de bens e serviços na arrecadação da campanha.")
        fig = revenue_composition_figure(frame)
        if fig is None:
            values = financial_values(frame)
            both_zero = values["receita_financeira"] == 0 and values["receita_estimavel"] == 0
            st.info("Sem receitas registradas para compor o gráfico." if both_zero else
                    "Composição das receitas indisponível: são necessários valores completos e não negativos de receita financeira e estimável.")
            return
        st.plotly_chart(fig, width="stretch", key="pagina1_revenue_donut", config={"displayModeBar": False})
        values = financial_values(frame)
        amounts = [values["receita_financeira"], values["receita_estimavel"]]
        total = sum(amounts)
        legend_columns = st.columns(2, gap="medium")
        for column, label, value, color, description in zip(
                legend_columns,
                REVENUE_LABELS, amounts, REVENUE_COLORS,
                ("Entrada de dinheiro na campanha.", "Doações de estrutura e serviços, sem entrada de caixa."),
            ):
            with column:
                share = f"{value / total * 100:.1f}%".replace(".", ",")
                st.html(
                    f'<div style="border-left:4px solid {color};padding:4px 0 4px 18px;margin:16px 0">'
                    + _indicator(label, value, f"{share} das receitas · {description}") + "</div>"
                )
        st.caption("Receita estimável compõe a arrecadação total, mas não representa dinheiro disponível em caixa.")


def budget_funnel_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    values = financial_values(frame)
    fields = ("receita_total", "receita_financeira", "despesa_contratada", "despesa_paga")
    amounts = [values[field] for field in fields]
    if any(value is None or value < 0 for value in amounts) or not any(amounts):
        return None
    fig = go.Figure(go.Funnel(
        y=["Receita Total", "Receita Financeira", "Despesa Contratada", "Despesa Paga"],
        x=[float(value) for value in amounts],
        orientation="h", text=[_money(value) for value in amounts],
        textinfo="text", textposition="inside", textfont={"color": "#f8fbff", "size": 14},
        marker={"color": ["#2563eb", "#38bdf8", "#6366f1", "#15803d"],
                "line": {"color": "rgba(147,197,253,.3)", "width": 1}},
        connector={"fillcolor": "rgba(147,197,253,.12)", "line": {"width": 0}},
        customdata=[_money(value) for value in amounts],
        hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
    ))
    fig.update_layout(
        height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        margin={"l": 12, "r": 18, "t": 18, "b": 18}, showlegend=False,
        yaxis={"automargin": True},
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
    )
    return fig


def budget_commitment_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    values = financial_values(frame)
    revenue, contracted = values["receita_total"], values["despesa_contratada"]
    if revenue is None or contracted is None or revenue <= 0 or contracted < 0:
        return None
    percentage = float(contracted / revenue * 100)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=percentage,
        domain={"x": [0.07, 0.93], "y": [0.05, 0.98]},
        number={"suffix": "%", "valueformat": ".1f", "font": {"size": 25, "color": "#f8fbff"}},
        gauge={
            "shape": "angular",
            "axis": {"range": [0, max(100, percentage)], "visible": False},
            "bar": {"color": "#60a5fa", "thickness": 0.48},
            "bgcolor": "rgba(147,197,253,.14)", "borderwidth": 0,
        },
    ))
    fig.update_layout(
        height=170, margin={"l": 0, "r": 0, "t": 4, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
    )
    return fig


def render_financial_charts(frame: pd.DataFrame | None) -> None:
    revenue_col, funnel_col = st.columns([0.5, 0.5], gap="large")
    with revenue_col:
        render_revenue_composition(frame)
    with funnel_col:
        with st.container(border=True, key="pagina1_budget_funnel"):
            st.markdown("### DRE Simplificada da Campanha")
            st.caption("Da arrecadação aos compromissos assumidos e pagamentos executados.")
            fig = budget_funnel_figure(frame)
            if fig is None:
                st.info("Funil indisponível: são necessários valores completos, não negativos e ao menos um total positivo.")
            else:
                st.plotly_chart(fig, width="stretch", key="pagina1_budget_funnel_chart", config={"displayModeBar": False})
                st.caption("As etapas mostram os totais informados, sem subtração entre barras. Obrigações contratadas podem superar a receita; a largura preserva esses valores.")
        with st.container(border=True, key="pagina1_budget_commitment"):
            st.html('<h3 style="text-align:center">Comprometimento Orçamentário</h3>')
            fig = budget_commitment_figure(frame)
            if fig is None:
                st.info("Comprometimento indisponível: é necessária receita total positiva e despesa contratada válida.")
            else:
                st.plotly_chart(fig, width="stretch", height=170, key="pagina1_budget_commitment_gauge",
                                config={"displayModeBar": False, "staticPlot": True})
                values = financial_values(frame)
                st.caption(f"Despesas contratadas: {_money(values['despesa_contratada'])} · Receita total: {_money(values['receita_total'])}.")
                if fig.data[0].value > 100:
                    st.caption("Os compromissos superam a receita total. A escala se amplia para exibir o percentual integral.")
            st.caption("% de execução = despesas contratadas ÷ receita total × 100.")
