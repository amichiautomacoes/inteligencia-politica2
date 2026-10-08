"""Demographic distribution panel for the DNA Eleitoral page."""
from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


DIMENSIONS = {
    "Gênero": ("genero", "pct_genero_"),
    "Faixa etária": ("idade", "pct_idade_"),
    "Escolaridade": ("escolaridade", "pct_escolaridade_"),
    "Estado civil": ("estado_civil", "pct_estado_civil_"),
}
PALETTE = ["#60A5FA", "#38BDF8", "#A78BFA", "#34D399", "#FBBF24", "#FB923C", "#94A3B8"]
GENDER_COLORS = {"feminino": "#3B82F6", "masculino": "#F97316", "nao informado": "#94A3B8"}


def _code(value: object) -> str:
    raw = str(value).strip()
    return raw if raw and raw.lower() != "nan" else ""


def _name(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    return re.sub(r"\s+", " ", "".join(c for c in normalized if not unicodedata.combining(c))).strip()


def _category_colors(labels: list[str], kind: str) -> list[str]:
    if kind == "genero":
        return [GENDER_COLORS.get(_name(label), "#A78BFA") for label in labels]
    return [PALETTE[index % len(PALETTE)] for index in range(len(labels))]


def _municipalities(votes: pd.DataFrame | None) -> list[tuple[str, str]]:
    if votes is None or votes.empty or "nm_municipio" not in votes:
        return []
    names = votes[["nm_municipio"]].copy()
    names["code"] = votes["cd_municipio"].map(_code) if "cd_municipio" in votes else ""
    names["nm_municipio"] = names["nm_municipio"].fillna("").astype(str).str.strip()
    names = names[names["nm_municipio"].ne("")].drop_duplicates()
    return sorted([(row.code, row.nm_municipio) for row in names.itertuples(index=False)], key=lambda item: item[1].casefold())


def _filter_municipality(df: pd.DataFrame, code: str, name: str) -> pd.DataFrame:
    if not name:
        return df
    if code and "cd_municipio" in df:
        matched = df.loc[df["cd_municipio"].map(_code).eq(code)]
        if not matched.empty:
            return matched.copy()
    if "nm_municipio" in df:
        return df.loc[df["nm_municipio"].map(_name).eq(_name(name))].copy()
    return df.iloc[:0].copy()


def _distribution(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    # Stage 02 files can contain both municipality and neighborhood rows. Keep
    # one level so each municipality's votes are not counted twice.
    if "nivel_territorial" in df:
        levels = df["nivel_territorial"].astype(str).str.strip().str.casefold()
        municipal = df.loc[levels.eq("municipio")]
        if not municipal.empty:
            df = municipal
        else:
            neighborhoods = df.loc[levels.eq("bairro")]
            if not neighborhoods.empty:
                df = neighborhoods
    columns = [column for column in df if column.startswith(prefix)]
    if not columns:
        return pd.DataFrame(columns=["categoria", "percentual"])
    weight_col = "QT_VOTOS_TOTAL" if "QT_VOTOS_TOTAL" in df else "qt_votos"
    weights = pd.to_numeric(df[weight_col], errors="coerce").fillna(0).clip(lower=0) if weight_col in df else pd.Series(1.0, index=df.index)
    values = []
    for column in columns:
        percentages = pd.to_numeric(df[column], errors="coerce")
        valid = percentages.between(0, 100)
        if not valid.any():
            continue
        valid_weights = weights.loc[valid]
        average = (
            float((percentages.loc[valid] * valid_weights).sum() / valid_weights.sum())
            if valid_weights.sum() > 0 else float(percentages.loc[valid].mean())
        )
        if average > 0:
            values.append((column.removeprefix(prefix).replace("_", " ").capitalize(), average))
    result = pd.DataFrame(values, columns=["categoria", "percentual"])
    return result.sort_values("percentual", ascending=False) if not result.empty else result


def _votes_in_scope(votes: pd.DataFrame | None, code: str, name: str) -> float | None:
    if votes is None or votes.empty or "qt_votos" not in votes:
        return None
    frame = _filter_municipality(votes, code, name)
    return float(pd.to_numeric(frame["qt_votos"], errors="coerce").fillna(0).sum())


def _legend_html(labels: list[str], shares: list[float], colors: list[str]) -> str:
    rows = []
    for label, share, color in zip(labels, shares, colors):
        rows.append(
            '<div class="dna-distribution-legend-row">'
            f'<span class="dna-distribution-legend-category"><span class="dna-distribution-swatch" style="background:{color}"></span>{html.escape(label)}</span>'
            f'<strong>{share:.1f}%</strong>'.replace(".", ",")
            + '</div>'
        )
    return (
        '<div class="dna-distribution-legend" aria-label="Categorias da distribuição">'
        '<div class="dna-distribution-legend-head"><span>Categoria</span><span>%</span></div>'
        + "".join(rows) + '</div>'
    )


def render_electorate_distribution(read_parquet: Callable[[str], pd.DataFrame | None]) -> None:
    votes = read_parquet("votos_municipio")
    municipalities = _municipalities(votes)
    st.html('''<style>
        .dna-distribution-leader{display:inline-flex;align-items:center;gap:.35rem;padding:.45rem .8rem;border:1px solid rgba(96,165,250,.35);border-radius:999px;background:rgba(37,99,235,.16);color:#eaf2ff;font-size:.83rem;font-weight:700}
        .dna-distribution-leader strong{color:#fff}
        .dna-distribution-legend{display:grid;gap:5px;margin:1rem 0 .75rem}
        .dna-distribution-legend-head,.dna-distribution-legend-row{display:grid;grid-template-columns:minmax(0,1fr) 4rem;align-items:center;gap:8px}
        .dna-distribution-legend-head{color:#9fb2d4;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;padding:0 10px 3px}
        .dna-distribution-legend-row{padding:9px 10px;border:1px solid rgba(147,197,253,.14);border-radius:9px;background:rgba(10,29,64,.42);font-size:.8rem;color:#eaf2ff}
        .dna-distribution-legend-category{display:flex;align-items:center;gap:8px;min-width:0}
        .dna-distribution-swatch{width:11px;height:11px;border-radius:3px;flex:none}
        .dna-distribution-legend-row strong{text-align:right;color:#fff;font-variant-numeric:tabular-nums}
        @media(max-width:560px){.dna-distribution-legend-head,.dna-distribution-legend-row{grid-template-columns:minmax(0,1fr) 3.5rem;gap:4px}.dna-distribution-legend-head{font-size:.58rem}.dna-distribution-legend-row{font-size:.72rem;padding:8px 6px}}
    </style>''')
    with st.container(border=True):
        st.markdown("#### Distribuição do eleitorado")
        st.caption("Participação estimada de cada categoria demográfica na votação do recorte selecionado.")
        chart_col, filter_col = st.columns([2.3, 1], gap="large")
        with filter_col:
            st.caption("Refine a distribuição")
            municipality_options = ["Todos os municípios"] + [name for _, name in municipalities]
            selected_name = st.selectbox("MUNICÍPIO", municipality_options, key="dna_distribution_municipality")
            dimension = st.selectbox("PERFIL DEMOGRÁFICO", list(DIMENSIONS), key="dna_distribution_dimension")
        code = ""
        name = ""
        if selected_name != "Todos os municípios":
            code, name = next(((code, name) for code, name in municipalities if name == selected_name), ("", ""))
        kind, prefix = DIMENSIONS[dimension]
        source = read_parquet(kind)
        with chart_col:
            if source is None or source.empty:
                st.info(f"Dados de {dimension.lower()} indisponíveis para este candidato.")
                return
            distribution = _distribution(_filter_municipality(source, code, name), prefix)
            if distribution.empty:
                st.info("Não há distribuição demográfica disponível para este recorte.")
                return
            total_votes = _votes_in_scope(votes, code, name)
            labels = distribution["categoria"].tolist()
            values = distribution["percentual"].tolist()
            shares = [value / sum(values) * 100 for value in values]
            colors = _category_colors(labels, kind)
            leader = f"🏆 {dimension} dominante: <strong>{html.escape(labels[0])} ({shares[0]:.1f}%)</strong>".replace(".", ",")
            st.html(f'<div class="dna-distribution-leader">{leader}</div>')
            center = f"{total_votes:,.0f}".replace(",", ".") if total_votes is not None else "—"
            hover = "<b>%{label}</b><br>%{value:.1f}% da distribuição<extra></extra>"
            fig = go.Figure(go.Pie(
                labels=labels, values=shares, hole=0.66, sort=False,
                marker={"colors": colors, "line": {"color": "rgba(255,255,255,.25)", "width": 1}},
                hovertemplate=hover,
                text=[f"{share:.1f}%".replace(".", ",") for share in shares],
                textinfo="text", textposition="outside", automargin=True,
                textfont={"color": "#f8fbff", "size": 14}, showlegend=False,
            ))
            fig.update_layout(
                height=430, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#eaf2ff"}, margin={"l": 45, "r": 45, "t": 24, "b": 24},
                showlegend=False,
                annotations=[{"x": 0.5, "y": 0.5,
                              "text": f"<span style='font-size:29px;color:#ffffff'><b>{html.escape(center)}</b></span><br><span style='font-size:12px;color:#b7c7e6'>votos no recorte</span>",
                              "showarrow": False, "font": {"size": 16, "color": "#ffffff"}}],
            )
            st.plotly_chart(fig, width="stretch", key="dna_distribution_donut", config={"displayModeBar": False})
            st.caption("Os percentuais são estimativas de dimensões separadas; as categorias exibidas não representam cruzamentos entre perfis.")
        with filter_col:
            st.html(_legend_html(labels, shares, colors))
