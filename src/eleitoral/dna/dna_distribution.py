"""Demographic distribution panel for the DNA Eleitoral page."""
from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from eleitoral.maps.territorial_mesh import mesoregion_options, municipality_options


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


def _percent_label(share: float) -> str:
    if 0 < share < 0.05:
        return "<0,1%"
    if 99.95 < share < 100:
        return ">99,9%"
    return f"{share:.1f}%".replace(".", ",")


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
            f'<strong>{html.escape(_percent_label(share))}</strong>'
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
        .st-key-dna_distribution_card{margin:28px 0;padding:30px!important;border:1px solid rgba(96,165,250,.3)!important;border-radius:20px!important;background:linear-gradient(135deg,rgba(11,31,77,.76),rgba(7,24,54,.68))!important;box-shadow:0 12px 30px rgba(0,0,0,.14)!important}
        .dna-distribution-dimension-badge{display:inline-flex;align-items:center;padding:.45rem .9rem;margin:.65rem 0 .45rem;border-radius:999px;font-size:.95rem;font-weight:800;line-height:1.3;box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 3px 10px rgba(0,0,0,.12)}
        .dna-distribution-dimension-genero{background:#15803d;color:#fff;border:1px solid #34d399}
        .dna-distribution-dimension-idade{background:#1d4ed8;color:#fff;border:1px solid #60a5fa}
        .dna-distribution-dimension-escolaridade{background:#7e22ce;color:#fff;border:1px solid #c084fc}
        .dna-distribution-dimension-estado_civil{background:#fbbf24;color:#291c03;border:1px solid #fde68a}
        .st-key-dna_distribution_card [data-testid="stSelectbox"] [data-baseweb="select"]>div{border:1px solid rgba(147,197,253,.23);border-radius:10px;background:rgba(10,29,64,.7)}
        .dna-distribution-note{margin:.1rem 0 .35rem;color:#b7c7e6;font-size:.81rem;line-height:1.5}
        .dna-distribution-legend{display:grid;gap:6px;margin:1.25rem 0 .5rem}
        .dna-distribution-legend-head,.dna-distribution-legend-row{display:grid;grid-template-columns:minmax(0,1fr) 4rem;align-items:center;gap:8px}
        .dna-distribution-legend-head{color:#9fb2d4;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;padding:0 10px 3px}
        .dna-distribution-legend-row{padding:10px 11px;border:1px solid rgba(147,197,253,.16);border-radius:9px;background:rgba(10,29,64,.48);font-size:.81rem;color:#eaf2ff}
        .dna-distribution-legend-head + .dna-distribution-legend-row{border-color:rgba(96,165,250,.34);background:rgba(37,99,235,.12)}
        .dna-distribution-legend-category{display:flex;align-items:center;gap:8px;min-width:0}
        .dna-distribution-swatch{width:11px;height:11px;border-radius:3px;flex:none}
        .dna-distribution-legend-row strong{text-align:right;color:#fff;font-variant-numeric:tabular-nums}
        @media(max-width:560px){.st-key-dna_distribution_card{padding:18px!important}.dna-distribution-legend-head,.dna-distribution-legend-row{grid-template-columns:minmax(0,1fr) 3.5rem;gap:4px}.dna-distribution-legend-head{font-size:.58rem}.dna-distribution-legend-row{font-size:.72rem;padding:8px 6px}}
    </style>''')
    with st.container(border=True, key="dna_distribution_card"):
        try:
            regions = mesoregion_options()
        except Exception:
            st.info("Referência de mesorregiões indisponível no momento.")
            return
        region_col, municipality_col = st.columns(2, gap="medium")
        with region_col:
            region = st.selectbox(
                "MESORREGIÃO", ["Todas", *regions], key="dna_distribution_mesoregion",
            )
        scoped_votes = votes
        allowed_names = None
        allowed_codes = set()
        if region != "Todas":
            try:
                regional_municipalities = municipality_options(region)
            except Exception:
                st.info("Referência municipal indisponível para esta mesorregião.")
                return
            allowed_names = {_name(name) for _, name in regional_municipalities}
            allowed_codes = {_code(code) for code, _ in regional_municipalities}
            municipalities = [(code, name) for code, name in municipalities if _name(name) in allowed_names or code in allowed_codes]
            allowed_codes.update(code for code, _ in municipalities if code)

        def regional_scope(frame: pd.DataFrame | None) -> pd.DataFrame | None:
            if frame is None or allowed_names is None:
                return frame
            mask = pd.Series(False, index=frame.index)
            if "nm_municipio" in frame:
                mask |= frame["nm_municipio"].map(_name).isin(allowed_names)
            if "cd_municipio" in frame:
                mask |= frame["cd_municipio"].map(_code).isin(allowed_codes)
            return frame.loc[mask].copy()

        scoped_votes = regional_scope(votes)
        with municipality_col:
            municipality_labels = dict(municipalities)
            selected_code = st.selectbox(
                "MUNICÍPIO", ["", *municipality_labels],
                format_func=lambda code: "Todos os municípios" if not code else municipality_labels[code],
                key=f"dna_distribution_municipality_{region}",
            )
        code = selected_code
        name = municipality_labels.get(code, "")
        chart_col, filter_col = st.columns([2.3, 1], gap="large")
        distributions = {}
        selections = {}

        def activate_dimension(label: str) -> None:
            st.session_state["dna_distribution_active_dimension"] = label

        with filter_col:
            for label, (kind, prefix) in DIMENSIONS.items():
                source = regional_scope(read_parquet(kind))
                distribution = (
                    _distribution(_filter_municipality(source, code, name), prefix)
                    if source is not None and not source.empty else pd.DataFrame()
                )
                distributions[label] = distribution
                categories = distribution["categoria"].tolist() if not distribution.empty else []
                widget_key = f"dna_distribution_category_{kind}"
                options = ["Todas as categorias", *categories]
                if st.session_state.get(widget_key) not in options:
                    st.session_state[widget_key] = options[0]
                badge_label = "Estado Civil" if kind == "estado_civil" else label
                st.html(
                    f'<div class="dna-distribution-dimension-badge dna-distribution-dimension-{kind}">{html.escape(badge_label)}</div>'
                )
                selections[label] = st.selectbox(
                    label, options, key=widget_key, label_visibility="collapsed",
                    disabled=not categories, on_change=activate_dimension, args=(label,),
                )
                if not categories:
                    st.caption("Sem dados para este recorte.")
        dimension = st.session_state.get("dna_distribution_active_dimension", next(iter(DIMENSIONS)))
        if dimension not in DIMENSIONS:
            dimension = next(iter(DIMENSIONS))
        kind, _ = DIMENSIONS[dimension]
        distribution = distributions[dimension]
        with chart_col:
            if distribution.empty:
                st.info(f"Dados de {dimension.lower()} indisponíveis para este recorte.")
                return
            total_votes = _votes_in_scope(scoped_votes, code, name)
            labels = distribution["categoria"].tolist()
            values = distribution["percentual"].tolist()
            shares = [value / sum(values) * 100 for value in values]
            colors = _category_colors(labels, kind)
            st.html(
                f'<div class="dna-distribution-dimension-badge dna-distribution-dimension-{kind}">{html.escape(dimension)}</div>'
                + _legend_html(labels, shares, colors)
            )
            selected_category = selections[dimension]
            center = f"{total_votes:,.0f}".replace(",", ".") if total_votes is not None else "—"
            hover = "<b>%{label}</b><br>%{customdata} da distribuição<extra></extra>"
            fig = go.Figure(go.Pie(
                labels=labels, values=shares, hole=0.68, sort=False,
                pull=[0.08 if label == selected_category else 0 for label in labels],
                marker={"colors": colors, "line": {"color": "rgba(7,24,54,.75)", "width": 1.5}},
                hovertemplate=hover, customdata=[_percent_label(share) for share in shares],
                text=[_percent_label(share) if share >= 1 else "" for share in shares],
                textinfo="text", textposition="outside", automargin=True,
                textfont={"color": "#f8fbff", "size": 14}, showlegend=False,
            ))
            fig.update_layout(
                height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#eaf2ff"}, margin={"l": 42, "r": 42, "t": 18, "b": 18},
                showlegend=False,
                annotations=[{"x": 0.5, "y": 0.5,
                              "text": f"<span style='font-size:27px;color:#ffffff'><b>{html.escape(center)}</b></span><br><span style='font-size:12px;color:#b7c7e6'>votos no recorte</span>",
                              "showarrow": False, "font": {"size": 16, "color": "#ffffff"}}],
            )
            st.plotly_chart(fig, width="stretch", key="dna_distribution_donut", config={"displayModeBar": False})
            st.html('<p class="dna-distribution-note">Os percentuais são estimativas de dimensões separadas; as categorias exibidas não representam cruzamentos entre perfis.</p>')
