"""Executive view of the global contracted/payment reconciliation."""
from __future__ import annotations

import html
import textwrap
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .financial_cards import _money


FIELDS = (
    "total_contratado", "total_pago", "taxa_execucao_pct", "saldo_em_aberto",
    "saldo_liquido", "excesso_pago_conhecido", "contratado_sem_pagamento",
    "defasagem_media_conhecida_dias",
)


def execution_scope(frame: pd.DataFrame | None, breakdown: str, group_key: str | None = None) -> pd.DataFrame:
    if frame is None or "recorte" not in frame:
        return pd.DataFrame()
    selected = frame.loc[frame["recorte"].astype(str).str.strip().str.casefold() == breakdown].copy()
    if group_key is not None:
        if "grupo_chave" not in selected:
            return selected.iloc[:0]
        selected = selected.loc[selected["grupo_chave"].astype(str) == group_key].copy()
    return selected


def render_execution_filters(frame: pd.DataFrame | None) -> tuple[pd.DataFrame, str]:
    scope = str(st.session_state.get("selected_deputado_key", "default"))
    scope_col, group_col = st.columns(2)
    with scope_col:
        breakdown = st.selectbox("Recorte da análise", ["global", "categoria", "fornecedor"],
            format_func=lambda value: {"global": "Global / Geral da Campanha",
                "categoria": "Por Categoria de Despesa", "fornecedor": "Por Fornecedor"}[value],
            key=f"execution_scope_{scope}")
    selected = execution_scope(frame, breakdown)
    if breakdown != "global":
        label_column = "categoria" if breakdown == "categoria" else "nm_fornecedor"
        if label_column not in selected:
            label_column = "grupo_descricao"
        labels = {}
        if "grupo_chave" in selected and label_column in selected:
            labels = {str(row["grupo_chave"]): str(row[label_column]) if pd.notna(row[label_column]) else "Não identificado"
                      for _, row in selected.iterrows()}
        keys = sorted(labels, key=lambda key: (labels[key].casefold(), key))
        with group_col:
            key = st.selectbox("Categoria de Despesa" if breakdown == "categoria" else "Fornecedor",
                keys, format_func=labels.get, key=f"execution_group_{scope}_{breakdown}",
                disabled=not keys, placeholder="Sem dados disponíveis")
        selected = execution_scope(frame, breakdown, key) if key is not None else selected.iloc[:0]
    if selected.empty:
        st.info("Não há dados de execução para o recorte selecionado.")
    return selected, breakdown


def contracted_paid_figure(frame: pd.DataFrame | None, breakdown: str = "categoria") -> go.Figure | None:
    required = {"recorte", "grupo_chave", "grupo_descricao", "total_contratado", "total_pago"}
    if frame is None or frame.empty or not required.issubset(frame.columns):
        return None
    data = frame.loc[frame["recorte"].astype(str).str.strip().str.casefold() == breakdown].copy()
    if data.empty or data["grupo_chave"].duplicated().any():
        return None
    for field in ("total_contratado", "total_pago"):
        data[field] = pd.to_numeric(data[field], errors="coerce")
    data["_volume"] = data[["total_contratado", "total_pago"]].max(axis=1)
    data = data.sort_values(["_volume", "grupo_chave"], ascending=[False, True], kind="stable")
    if breakdown == "fornecedor":
        data = data.head(10)
    valid = (np.isfinite(data["total_contratado"]) & np.isfinite(data["total_pago"])
             & (data["total_contratado"] >= 0) & (data["total_pago"] >= 0))
    omitted = int((~valid).sum())
    data = data.loc[valid].copy()
    if data.empty:
        return None
    names = data["grupo_descricao"].fillna("Não identificado").astype(str).tolist()
    labels = ["<br>".join(html.escape(part) for part in textwrap.wrap(name, width=38)) for name in names]
    ids = [str(index) for index in range(len(data))]
    custom = []
    for name, contracted, paid in zip(names, data["total_contratado"], data["total_pago"]):
        difference = Decimal(str(contracted)) - Decimal(str(paid))
        reading = "Saldo contratado ainda não pago" if difference > 0 else "Pago acima do contratado" if difference < 0 else "Valores equivalentes"
        custom.append([html.escape(name), _money(abs(difference)), reading])
    fig = go.Figure()
    for field, label, color in (("total_contratado", "Contratado", "#2563eb"), ("total_pago", "Pago", "#38bdf8")):
        money = [_money(Decimal(str(value))) for value in data[field]]
        fig.add_trace(go.Bar(
            name=label, x=data[field].tolist(), y=ids, orientation="h",
            marker_color=color, text=money, textposition="outside", cliponaxis=False,
            customdata=[[*details, value] for details, value in zip(custom, money)],
            hovertemplate=("<b>%{customdata[0]}</b><br>" + label + ": %{customdata[3]}"
                           "<br>%{customdata[2]}: %{customdata[1]}<extra></extra>"),
        ))
    fig.update_layout(
        barmode="group", bargap=.3, bargroupgap=.08,
        height=max(420, 100 + sum(max(75, 22 * (label.count("<br>") + 1) + 30) for label in labels)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 125, "t": 25, "b": 50},
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        separators=",.", legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={"title": "Valor (R$)", "rangemode": "tozero", "gridcolor": "rgba(147,197,253,.12)"},
        yaxis={"type": "category", "categoryorder": "array", "categoryarray": ids,
               "autorange": "reversed", "tickmode": "array", "tickvals": ids,
               "ticktext": labels, "automargin": True},
        hoverlabel={"bgcolor": "rgba(5,12,28,.95)", "font_color": "#eaf2ff"},
        meta={"omitted": omitted},
    )
    return fig


def render_contracted_paid_chart(frame: pd.DataFrame | None, breakdown: str | None = None) -> None:
    with st.container(border=True, key="pagina1_contracted_paid_comparison"):
        st.markdown("### Contratado vs. Pago")
        scope = str(st.session_state.get("selected_deputado_key", "default"))
        if breakdown is None:
            breakdown = st.selectbox("Comparar por", ["categoria", "fornecedor"],
                format_func=lambda value: "Categoria" if value == "categoria" else "Top 10 Fornecedores",
                key=f"contracted_paid_breakdown_{scope}")
            st.caption("Categorias e fornecedores ordenados pelo maior valor entre contratado e pago. Fornecedores limitados aos 10 primeiros.")
        else:
            st.caption("Comparação do recorte selecionado nos filtros acima dos indicadores.")
        fig = contracted_paid_figure(frame, breakdown)
        if fig is None:
            st.info("Comparação indisponível: são necessários registros únicos por grupo e valores completos, não negativos de contratado e pago.")
            return
        st.plotly_chart(fig, width="stretch", key="pagina1_contracted_paid_comparison_chart", config={"displayModeBar": False})
        if fig.layout.meta["omitted"]:
            st.caption(f"{fig.layout.meta['omitted']} grupo(s) com valores ausentes ou inválidos não foram exibidos.")
        st.caption("A diferença entre as barras indica saldo ainda não pago ou pagamento acima do contratado. Sem datas e prazos contratuais, ela não comprova atraso, retenção ou adiantamento.")


def execution_values(frame: pd.DataFrame | None, breakdown: str = "global") -> dict[str, Decimal | None]:
    values = dict.fromkeys(FIELDS)
    if frame is None or frame.empty:
        return values
    if "recorte" in frame:
        frame = execution_scope(frame, breakdown)
    if len(frame) != 1:
        return values
    row = frame.iloc[0]
    for field in FIELDS:
        try:
            value = Decimal(str(row.get(field)))
            signed = field in {"saldo_liquido", "defasagem_media_conhecida_dias"}
            if value.is_finite() and (signed or value >= 0):
                values[field] = value
        except (InvalidOperation, ValueError, TypeError):
            pass
    return values


def execution_badge(rate: Decimal | None) -> tuple[str, str]:
    if rate is None:
        return "Ritmo indisponível", "neutral"
    if rate == 0:
        return "Execução não iniciada", "warning"
    if rate < 100:
        return "Execução parcial", "neutral"
    if rate == 100:
        return "Execução integral", "positive"
    return "Pagamento acima do contratado", "warning"


def contracted_paid_cards_html(frame: pd.DataFrame | None, breakdown: str = "global") -> str:
    values = execution_values(frame, breakdown)

    def indicator(label: str, value: Decimal | None, description: str, *, days: bool = False) -> str:
        display = (f"{value:.1f}".replace(".", ",") + " dias") if days and value is not None else _money(value)
        return (f'<div class="execution-indicator"><h4>{html.escape(label)}</h4>'
                f'<strong>{html.escape(display)}</strong><p>{html.escape(description)}</p></div>')

    volume = indicator("Total Contratado", values["total_contratado"], "Compromissos assumidos pela campanha.")
    volume += indicator("Total Pago", values["total_pago"], "Pagamentos executados.")
    rate = values["taxa_execucao_pct"]
    rate_label = f"{rate:.1f}%".replace(".", ",") if rate is not None else "Indisponível"
    badge, tone = execution_badge(rate)
    execution = (f'<div class="execution-indicator"><strong>{rate_label}</strong>'
                 f'<span class="execution-status execution-{tone}">{badge}</span>'
                 '<p>Percentual pago sobre o total contratado.</p></div>')
    balance = values["saldo_em_aberto"]
    balance_label, balance_description = "Saldo em Aberto", "Passivo remanescente conhecido a pagar."
    if balance is None and values["saldo_liquido"] is not None:
        balance = values["saldo_liquido"]
        balance_label = "Saldo Líquido"
        balance_description = "Saldo líquido informado na conciliação; excessos de pagamento podem compensar passivos."
    outstanding = indicator(balance_label, balance, balance_description)
    alerts = indicator("Pagamentos acima do contratado", values["excesso_pago_conhecido"], "Excesso pago conhecido na conciliação.")
    alerts += indicator("Contratado sem pagamento", values["contratado_sem_pagamento"], "Compromissos com quitação zero.")
    alerts += indicator("Defasagem média conhecida", values["defasagem_media_conhecida_dias"], "Intervalo entre contratação e pagamento; valor negativo indica antecipação.", days=True)
    cards = "".join(
        f'<article class="execution-card"><h3>{title}</h3>{body}</article>'
        for title, body in (("Total Contratado vs. Total Pago", volume),
                            ("Taxa de Execução Geral", execution), ("Saldo em Aberto", outstanding))
    )
    cards += ('<details class="execution-card execution-alerts"><summary>'
              '<h3>Indicadores de Alerta / Distorções</h3><span class="execution-chevron" aria-hidden="true">⌄</span>'
              f'</summary><div class="execution-alert-content">{alerts}</div></details>')
    return '''<style>
    .execution-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;align-items:start;margin:18px 0 28px}
    .execution-card{min-width:0;box-sizing:border-box;min-height:190px;padding:22px;border:1px solid rgba(96,165,250,.3);border-radius:14px;background:linear-gradient(145deg,rgba(11,31,77,.76),rgba(7,24,54,.68));box-shadow:0 12px 30px rgba(0,0,0,.14);color:#eaf2ff}
    .execution-card h3{display:inline-block;margin:0 0 18px;padding:8px 12px;border-radius:10px;background:#15803d;color:white;font-size:1.05rem;font-weight:800;line-height:1.4}
    .execution-indicator h4{margin:0 0 10px;color:#eaf2ff;font-size:1rem}
    .execution-indicator strong{display:block;color:#f8fbff;font-size:clamp(1.3rem,1.7vw,1.9rem);overflow-wrap:anywhere;font-variant-numeric:tabular-nums}
    .execution-indicator p{margin:12px 0 0;color:#b7c7e6;font-size:.85rem;line-height:1.55}
    .execution-indicator+.execution-indicator{margin-top:20px;padding-top:20px;border-top:1px solid rgba(147,197,253,.2)}
    .execution-status{display:inline-block;margin-top:12px;padding:6px 10px;border-radius:8px;font-size:.8rem;font-weight:700}
    .execution-neutral{background:rgba(147,197,253,.12);color:#bfdbfe}
    .execution-positive{background:rgba(22,163,74,.18);color:#86efac}
    .execution-warning{background:rgba(234,179,8,.18);color:#fde68a}
    .execution-alerts summary{display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer;list-style:none}
    .execution-alerts summary::-webkit-details-marker{display:none}
    .execution-alerts summary:focus-visible{outline:2px solid #93c5fd;outline-offset:5px}
    .execution-chevron{font-size:1.5rem;color:#93c5fd;transition:transform .2s}
    .execution-alerts[open] .execution-chevron{transform:rotate(180deg)}
    .execution-alert-content{margin-top:18px;padding-top:20px;border-top:1px solid rgba(147,197,253,.2)}
    @media(max-width:1100px){.execution-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    @media(max-width:600px){.execution-grid{grid-template-columns:1fr}}
    </style><div class="execution-grid" role="group" aria-label="Contratado versus pago">''' + cards + '</div>'
