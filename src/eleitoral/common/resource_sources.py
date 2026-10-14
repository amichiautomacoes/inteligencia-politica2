"""Revenue and paid expenses by funding source."""
from __future__ import annotations

import html
import textwrap
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .financial_cards import _money


def _decimal(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def funding_sources_figure(frame: pd.DataFrame | None) -> go.Figure | None:
    required = {"fonte_chave", "fonte_descricao", "receita_total", "despesa_paga"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return None
    data = frame.copy()
    if data["fonte_chave"].isna().any() or data["fonte_chave"].duplicated().any():
        return None
    for field in ("receita_total", "despesa_paga"):
        data[field] = pd.to_numeric(data[field], errors="coerce")
    valid = (np.isfinite(data["receita_total"]) & np.isfinite(data["despesa_paga"])
             & (data["receita_total"] >= 0) & (data["despesa_paga"] >= 0))
    omitted = int((~valid).sum())
    data = data.loc[valid].sort_values("receita_total", ascending=False, kind="stable")
    if data.empty:
        return None
    ids, labels, custom = [], [], []
    for index, (_, row) in enumerate(data.iterrows()):
        name = str(row["fonte_descricao"]) if pd.notna(row["fonte_descricao"]) else "Fonte não informada"
        balance = _money(_decimal(row.get("saldo_financeiro_observado")))
        rate = _decimal(row.get("taxa_utilizacao_financeira_pct"))
        usage = f"{rate:.1f}%".replace(".", ",") if rate is not None and rate >= 0 else "Indisponível"
        wrapped = "<br>".join(html.escape(part) for part in textwrap.wrap(name, width=22))
        labels.append(f"{wrapped}<br><span style='font-size:10px'>Saldo: {balance}<br>Utilização: {usage}</span>")
        ids.append(str(index))
        custom.append([html.escape(name), balance, usage,
                       _money(_decimal(row.get("receita_financeira")))])
    fig = go.Figure()
    for field, label, color in (("receita_total", "Arrecadado", "#2563eb"),
                                 ("despesa_paga", "Efetivamente pago", "#38bdf8")):
        money = [_money(Decimal(str(value))) for value in data[field]]
        fig.add_trace(go.Bar(
            name=label, x=data[field].tolist(), y=ids, orientation="h", marker_color=color,
            text=money, textposition="outside", cliponaxis=False,
            customdata=[[*details, amount] for details, amount in zip(custom, money)],
            hovertemplate=("<b>%{customdata[0]}</b><br>" + label + ": %{customdata[4]}"
                           "<br>Receita financeira: %{customdata[3]}"
                           "<br>Saldo financeiro observado: %{customdata[1]}"
                           "<br>Taxa de utilização financeira: %{customdata[2]}<extra></extra>"),
        ))
    fig.update_layout(
        barmode="group", bargap=.35, bargroupgap=.08,
        height=max(450, 100 + len(data) * 115),
        margin={"l": 8, "r": 120, "t": 35, "b": 50},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", separators=",.",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        legend={"orientation": "h", "x": 0, "y": 1.12},
        xaxis={"title": "Valor (R$)", "rangemode": "tozero", "gridcolor": "rgba(147,197,253,.12)"},
        yaxis={"type": "category", "categoryorder": "array", "categoryarray": ids,
               "autorange": "reversed", "tickmode": "array", "tickvals": ids,
               "ticktext": labels, "automargin": True},
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
        meta={"omitted": omitted},
    )
    return fig


def destination_table(frame: pd.DataFrame | None, source: str | None, breakdown: str) -> pd.DataFrame:
    required = {"fonte_chave", "recorte", "grupo_descricao", "valor_pago", "pct_total_pago"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame()
    data = frame.loc[frame["recorte"].astype(str).str.strip().str.casefold() == breakdown].copy()
    if source is not None:
        data = data.loc[data["fonte_chave"].astype(str) == source].copy()
    data["_amount"] = pd.to_numeric(data["valor_pago"], errors="coerce")
    data = data.sort_values("_amount", ascending=False, kind="stable")
    data["valor_pago"] = data["valor_pago"].map(lambda value: _money(_decimal(value)))
    data["pct_total_pago"] = pd.to_numeric(data["pct_total_pago"], errors="coerce")
    if "nr_cpf_cnpj_fornecedor" in data:
        data["nr_cpf_cnpj_fornecedor"] = data["nr_cpf_cnpj_fornecedor"].astype("string")
    columns = [column for column in ("fonte_descricao", "grupo_descricao", "nr_cpf_cnpj_fornecedor",
                                     "natureza_despesa", "valor_pago", "pct_total_pago") if column in data]
    return data[columns].reset_index(drop=True)


def render_resource_flow(frame: pd.DataFrame | None, destinations: pd.DataFrame | None) -> None:
    left, right = st.columns([.5, .5], gap="large")
    with left:
        with st.container(border=True, key="pagina1_funding_sources", height="stretch"):
            st.markdown("### De onde vem?")
            fig = funding_sources_figure(frame)
            if fig is None:
                st.info("Dados por fonte indisponíveis para comparar arrecadação e pagamentos.")
            else:
                st.plotly_chart(fig, width="stretch", key="pagina1_funding_sources_chart", config={"displayModeBar": False})
                if fig.layout.meta["omitted"]:
                    st.info(f"{fig.layout.meta['omitted']} fonte(s) com valores incompletos ou inválidos não foram exibidas.")
    with right:
        with st.container(border=True, key="pagina1_resource_destinations", height="stretch"):
            scope = str(st.session_state.get("selected_deputado_key", "default"))
            labels = {}
            for source_frame in (frame, destinations):
                if source_frame is not None and {"fonte_chave", "fonte_descricao"}.issubset(source_frame.columns):
                    for _, row in source_frame.dropna(subset=["fonte_chave"]).iterrows():
                        labels[str(row["fonte_chave"])] = str(row["fonte_descricao"]) if pd.notna(row["fonte_descricao"]) else "Fonte não informada"
            title_col, source_col, breakdown_col = st.columns([1, 1.35, 1.25], gap="small", vertical_alignment="center")
            with title_col:
                st.markdown("### Para onde vai?")
            with source_col:
                source = st.selectbox("Fonte de financiamento", [None, *sorted(labels, key=lambda key: (labels[key], key))],
                    format_func=lambda value: "Todas as fontes" if value is None else labels[value],
                    key=f"resource_destination_source_{scope}")
            with breakdown_col:
                breakdown = st.selectbox("Destinação por", ["categoria", "fornecedor"],
                    format_func=lambda value: "Categoria de Despesa" if value == "categoria" else "Fornecedor",
                    key=f"resource_destination_breakdown_{scope}")
            table = destination_table(destinations, source, breakdown)
            if table.empty:
                st.info("Não há dados de destinação disponíveis para a fonte e o recorte selecionados.")
            else:
                visible_table = table.drop(columns=["nr_cpf_cnpj_fornecedor", "natureza_despesa"], errors="ignore")
                st.dataframe(visible_table, hide_index=True, width="stretch", height=450, column_config={
                    "fonte_descricao": st.column_config.TextColumn("Fonte"),
                    "grupo_descricao": st.column_config.TextColumn("Categoria" if breakdown == "categoria" else "Fornecedor", width="large"),
                    "valor_pago": st.column_config.TextColumn("Valor pago (R$)"),
                    "pct_total_pago": st.column_config.NumberColumn("% do total pago", format="%.2f%%"),
                })
