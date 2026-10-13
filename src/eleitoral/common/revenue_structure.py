"""Donor ranking KPIs shared by both offices."""
from __future__ import annotations

import html
import textwrap
from decimal import Decimal, InvalidOperation

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from .financial_cards import _money


def top_donors_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    required = {"rank_doador", "nm_doador", "valor_atribuido"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return None
    frame = frame.copy()
    if "tipo_doador" in frame:
        frame = frame.loc[frame["tipo_doador"].astype(str).str.strip().str.casefold() == "imediato"].copy()
    frame["_rank"] = pd.to_numeric(frame["rank_doador"], errors="coerce")
    frame = frame.loc[frame["_rank"].between(1, 10) & (frame["_rank"] % 1 == 0)].copy()
    if frame["_rank"].duplicated().any():
        return None
    frame["_amount"] = pd.to_numeric(frame["valor_atribuido"], errors="coerce")
    frame = frame.loc[np.isfinite(frame["_amount"]) & (frame["_amount"] >= 0)
                      & frame["nm_doador"].notna()].copy()
    frame["_name"] = frame["nm_doador"].astype(str).str.strip()
    frame = frame.loc[frame["_name"] != ""].sort_values("_rank")
    if frame.empty:
        return None
    names = frame["_name"].tolist()
    wrapped = ["<br>".join(html.escape(line) for line in textwrap.wrap(name, width=28)) for name in names]
    ranks = frame["_rank"].astype(int).astype(str).tolist()
    money = [_money(Decimal(str(value))) for value in frame["_amount"]]
    fig = go.Figure(go.Bar(
        x=frame["_amount"].tolist(), y=ranks, orientation="h",
        marker={"color": "#2563eb", "line": {"color": "#60a5fa", "width": 1}},
        text=money, textposition="outside", cliponaxis=False,
        textfont={"color": "#f8fbff", "size": 12},
        customdata=[[html.escape(name), value] for name, value in zip(names, money)],
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
    ))
    fig.update_layout(
        height=max(460, 70 + sum(max(48, 20 * (label.count('<br>') + 1) + 20) for label in wrapped)),
        margin={"l": 8, "r": 95, "t": 20, "b": 45},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        separators=",.", showlegend=False, bargap=0.35,
        yaxis={"type": "category", "categoryorder": "array", "categoryarray": ranks,
               "autorange": "reversed", "tickmode": "array", "tickvals": ranks,
               "ticktext": wrapped, "automargin": True, "tickfont": {"size": 12}},
        xaxis={"title": "Valor atribuído (R$)", "rangemode": "tozero",
               "gridcolor": "rgba(147,197,253,.12)", "zeroline": False},
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
    )
    return fig


def donor_concentration_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    values = donor_kpis(frame)
    top, coverage = values["top10"], values["coverage"]
    if top is None:
        return None
    labels = ["Top 10 Doadores"]
    shares = [top]
    colors = ["#2563eb"]
    if coverage is not None and coverage >= top:
        labels += ["Demais doadores identificados", "Receita sem origem atribuída"]
        shares += [coverage - top, 100 - coverage]
        colors += ["#38bdf8", "#64748b"]
    else:
        labels += ["Receita fora do Top 10"]
        shares += [100 - top]
        colors += ["#38bdf8"]
    percentages = [f"{share:.1f}%".replace(".", ",") for share in shares]
    fig = go.Figure(go.Pie(
        labels=labels, values=shares, hole=0.6, sort=False,
        marker={"colors": colors, "line": {"color": "rgba(7,24,54,.75)", "width": 1.5}},
        text=[percent if share >= 1 else "" for share, percent in zip(shares, percentages)],
        textinfo="text", textposition="outside", automargin=True,
        customdata=percentages,
        hovertemplate="<b>%{label}</b><br>%{customdata} da receita total<extra></extra>",
    ))
    fig.update_layout(
        height=340, margin={"l": 30, "r": 30, "t": 15, "b": 50},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.1},
        annotations=[{"x": 0.5, "y": 0.5, "showarrow": False,
                      "text": f"<b>{percentages[0]}</b><br><span style='font-size:12px'>Top 10</span>",
                      "font": {"size": 25, "color": "#f8fbff"}}],
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
    )
    return fig


def donor_audit_table(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty or "rank_doador" not in frame:
        return pd.DataFrame()
    frame = frame.copy()
    if "tipo_doador" in frame:
        frame = frame.loc[frame["tipo_doador"].astype(str).str.strip().str.casefold() == "imediato"].copy()
    columns = [column for column in ("rank_doador", "nm_doador", "nr_cpf_cnpj_doador", "valor_atribuido",
                                     "pct_receita_total", "qt_receitas_vinculadas") if column in frame]
    frame = frame[columns].copy()
    for column in ("rank_doador", "pct_receita_total", "qt_receitas_vinculadas"):
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "nr_cpf_cnpj_doador" in frame:
        frame["nr_cpf_cnpj_doador"] = frame["nr_cpf_cnpj_doador"].astype("string")
    if "valor_atribuido" in frame:
        frame["valor_atribuido"] = frame["valor_atribuido"].map(
            lambda value: _money(Decimal(str(value))) if pd.notna(value) else None
        )
    return frame.sort_values("rank_doador", na_position="last")


def render_revenue_charts(frame: pd.DataFrame | None) -> None:
    fig = top_donors_figure(frame)
    concentration = donor_concentration_figure(frame)
    table = donor_audit_table(frame)
    if fig is None and concentration is None and table.empty:
        return
    ranking_col, details_col = st.columns([0.5, 0.5], gap="large")
    with ranking_col:
        if fig is not None:
            with st.container(border=True, key="pagina1_top_donors"):
                st.markdown("### Top 10 Doadores")
                st.caption("Principais financiadores da campanha por valor atribuído.")
                st.plotly_chart(fig, width="stretch", key="pagina1_top_donors_chart", config={"displayModeBar": False})
    with details_col:
        if concentration is not None:
            with st.container(border=True, key="pagina1_donor_concentration"):
                st.markdown("### Índice de Concentração da Receita")
                st.caption("Participação dos 10 maiores doadores no orçamento da campanha.")
                st.plotly_chart(concentration, width="stretch", key="pagina1_donor_concentration_chart", config={"displayModeBar": False})
        if not table.empty:
            with st.container(border=True, key="pagina1_donor_audit"):
                st.markdown("### Ranking Completo")
                st.caption("Detalhamento dos doadores imediatos para conferência individualizada.")
                with st.expander("Ver detalhamento dos doadores", expanded=False):
                    st.dataframe(table, hide_index=True, width="stretch", column_config={
                        "rank_doador": st.column_config.NumberColumn("Posição", format="%d"),
                        "nm_doador": st.column_config.TextColumn("Doador", width="large"),
                        "nr_cpf_cnpj_doador": st.column_config.TextColumn("CPF / CNPJ"),
                        "valor_atribuido": st.column_config.TextColumn("Valor atribuído (R$)"),
                        "pct_receita_total": st.column_config.ProgressColumn("% da receita total", min_value=0, max_value=100, format="%.2f%%"),
                        "qt_receitas_vinculadas": st.column_config.NumberColumn("Receitas vinculadas", format="%d"),
                    })


def donor_kpis(frame: pd.DataFrame | None) -> dict:
    result = dict(name=None, amount=None, top10=None, coverage=None, count=None)
    if frame is None or frame.empty:
        return result
    if "tipo_doador" in frame:
        frame = frame.loc[frame["tipo_doador"].astype(str).str.strip().str.casefold() == "imediato"]
        if frame.empty:
            return result
    result["count"] = len(frame)
    if "cobertura_atribuicao_pct" in frame:
        coverage = pd.to_numeric(frame["cobertura_atribuicao_pct"], errors="coerce")
        valid = coverage.dropna().unique()
        if len(valid) == 1 and coverage.notna().all() and 0 <= valid[0] <= 100:
            result["coverage"] = float(valid[0])
    if "rank_doador" not in frame:
        return result
    ranks = pd.to_numeric(frame["rank_doador"], errors="coerce")
    ranked = frame.loc[ranks.notna() & (ranks >= 1) & (ranks % 1 == 0)].copy()
    ranked["_rank"] = ranks.loc[ranked.index]
    if ranked["_rank"].duplicated().any():
        return result
    ranked = ranked.sort_values("_rank")
    first = ranked.loc[ranked["_rank"] == 1]
    if len(first) == 1:
        row = first.iloc[0]
        if "nm_doador" in row and pd.notna(row["nm_doador"]) and str(row["nm_doador"]).strip():
            result["name"] = str(row["nm_doador"]).strip()
        try:
            value = Decimal(str(row.get("valor_atribuido")))
            if value.is_finite() and value >= 0:
                result["amount"] = value
        except (InvalidOperation, ValueError, TypeError):
            pass
    top = ranked.loc[ranked["_rank"] <= 10]
    expected = min(10, len(frame))
    if len(top) == expected and set(top["_rank"]) == set(range(1, expected + 1)) and "pct_receita_total" in top:
        shares = pd.to_numeric(top["pct_receita_total"], errors="coerce")
        if shares.notna().all() and shares.between(0, 100).all():
            total = float(shares.sum())
            if total <= 100.000001:
                result["top10"] = min(total, 100)
    return result


def render_revenue_kpis(frame: pd.DataFrame | None) -> None:
    values = donor_kpis(frame)
    percent = lambda value: f"{value:.1f}%".replace(".", ",") if value is not None else "Indisponível"
    cards = (
        ("Maior Doador (Top 1)", _money(values["amount"]), values["name"] or "Doador indisponível"),
        ("Concentração no Top 10", percent(values["top10"]), "Participação dos 10 maiores doadores na receita total."),
        ("Cobertura da Atribuição", percent(values["coverage"]), "Receita com origem identificada."),
        ("Total de Doadores Unificados", f"{values['count']:,}".replace(",", ".") if values["count"] is not None else "Indisponível", "Registros de doadores considerados no ranking."),
    )
    available = (
        values["name"] is not None and values["amount"] is not None,
        values["top10"] is not None,
        values["coverage"] is not None,
        values["count"] is not None,
    )
    cards = [card for card, visible in zip(cards, available) if visible]
    if not cards:
        return
    content = "".join(
        f'<article class="revenue-kpi"><h4>{html.escape(title)}</h4>'
        f'<div class="revenue-kpi-value">{html.escape(value)}</div><p>{html.escape(description)}</p></article>'
        for title, value, description in cards
    )
    st.html('''<style>
    .revenue-kpi-grid {display:grid;grid-template-columns:repeat(var(--revenue-kpi-count),minmax(0,1fr));gap:16px;margin:18px 0 28px}
    .revenue-kpi {min-width:0;padding:22px;border:1px solid rgba(96,165,250,.3);border-radius:14px;background:linear-gradient(145deg,rgba(11,31,77,.76),rgba(7,24,54,.68));box-shadow:0 12px 30px rgba(0,0,0,.14)}
    .revenue-kpi h4 {display:inline-block;margin:0 0 18px;padding:8px 12px;border-radius:10px;background:#15803d;color:#fff;font-size:1.05rem;font-weight:800;line-height:1.4}
    .revenue-kpi-value {color:#f8fbff;font-size:clamp(1.5rem,2vw,2rem);font-weight:800;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
    .revenue-kpi p {margin:12px 0 0;color:#b7c7e6;font-size:.9rem;line-height:1.5;overflow-wrap:anywhere}
    @media(max-width:1100px) {.revenue-kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:600px) {.revenue-kpi-grid {grid-template-columns:1fr}}
    </style><div class="revenue-kpi-grid" role="group" aria-label="Indicadores de estrutura da receita" style="--revenue-kpi-count:''' + str(len(cards)) + '">' + content + '</div>')
