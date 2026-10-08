from __future__ import annotations

import html
import re
import unicodedata
from textwrap import dedent

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from hf_sync import file_by_kind, load_env, load_parquet
from eleitoral.dna.cluster_cards import cluster_cards_html
from eleitoral.common.dna_copy import sentence_label
from eleitoral.dna.dna_expansion import render_vote_expansion
from eleitoral.dna.dna_distribution import render_electorate_distribution
from eleitoral.maps.dna_geo_reference import (
    load_area_ponderada_bairro_crosswalk, load_geo_layer, load_geo_reference,
)
from eleitoral.dna.demographic_alignment import (
    Profile, alignment, alignment_map, area_neighborhoods, population_by_area,
    profile_options, weighted_area_geojson,
)
from eleitoral.maps.choropleth_maps import continuous_choropleth
from eleitoral.maps.territorial_mesh import (
    mesoregion_options,
    municipality_mesh_map,
    municipality_options,
    state_municipality_mesh_map,
)
from eleitoral.common.shared_header import (
    apply_shared_visual_model,
    major_section_header,
    render_page_header,
    section_header,
    selected_files,
)


def _read_selected_parquet(kind: str) -> pd.DataFrame | None:
    file_name = file_by_kind(selected_files(), kind)
    if not file_name:
        return None
    try:
        return load_parquet(file_name, load_env().get("HF_TOKEN"))
    except Exception as exc:
        st.warning(f"Nao consegui ler `{kind}.parquet`: {exc}")
        return None


def _first_value(df: pd.DataFrame, column: str, fallback: str = "Nao informado") -> str:
    if df is None or df.empty or column not in df.columns:
        return fallback
    values = df[column].dropna()
    if values.empty:
        return fallback
    value = values.iloc[0]
    if isinstance(value, float) and pd.isna(value):
        return fallback
    text = str(value).strip()
    return text or fallback


def _format_percent_value(value: str, *, fraction: bool = False) -> str:
    if value in {"", "Nao informado"}:
        return "Nao informado"
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return "Nao informado"
    if fraction and abs(float(number)) <= 1:
        number = float(number) * 100
    return f"{float(number):.1f}%".replace(".", ",")


def _has_profile_label(value: str) -> bool:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return bool(normalized.strip()) and normalized.strip() != "nao informado"


def _weighted_dominant(df: pd.DataFrame, value_col: str) -> tuple[str, float]:
    if df.empty or value_col not in df.columns:
        return "Nao informado", 0.0
    working = df[[value_col]].copy()
    working[value_col] = working[value_col].fillna("").astype(str).str.strip()
    working = working[working[value_col].ne("")]
    if working.empty:
        return "Nao informado", 0.0
    if "votos_candidato" in df.columns:
        working["votos_candidato"] = pd.to_numeric(
            df.loc[working.index, "votos_candidato"], errors="coerce"
        ).fillna(0)
    else:
        working["votos_candidato"] = 1
    grouped = working.groupby(value_col, as_index=False)["votos_candidato"].sum()
    total = float(grouped["votos_candidato"].sum())
    top = grouped.sort_values("votos_candidato", ascending=False).iloc[0]
    pct = float(top["votos_candidato"]) / total * 100 if total > 0 else 0.0
    return str(top[value_col]), pct


def _territorial_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Use a single territorial level: municipalities, or neighborhoods as fallback."""
    if "nivel_territorial" not in df:
        return df.copy()
    levels = df["nivel_territorial"].astype(str).str.strip().str.lower()
    for level in ("municipio", "bairro"):
        if levels.eq(level).any():
            return df.loc[levels.eq(level)].copy()
    return df.iloc[:0].copy()


def _demographic_percent(df: pd.DataFrame, column: str, category: str) -> float:
    pct_column = f"pct_{column}"
    if pct_column not in df or column not in df:
        return float("nan")
    # These percentages describe the category, not the profile's electoral share.
    rows = df.loc[df[column].eq(category)]
    values = pd.to_numeric(rows[pct_column], errors="coerce")
    valid = values.between(0, 100)
    if not valid.any():
        return float("nan")
    weights = pd.to_numeric(rows.loc[valid, "votos_candidato"], errors="coerce").fillna(0)
    return float((values[valid] * weights).sum() / weights.sum()) if weights.sum() > 0 else float(values[valid].mean())


def _icp_general_row(icp_df: pd.DataFrame) -> pd.DataFrame:
    if icp_df.empty:
        return icp_df
    working = _territorial_rows(icp_df)
    if "votos_candidato" not in working:
        working["votos_candidato"] = 0.0
    working["votos_candidato"] = pd.to_numeric(working["votos_candidato"], errors="coerce").fillna(0)

    persona, _ = _weighted_dominant(working, "persona_executiva")
    genero, pct_genero = _weighted_dominant(working, "genero_principal")
    idade, pct_idade = _weighted_dominant(working, "idade_principal")
    escolaridade, pct_escolaridade = _weighted_dominant(working, "escolaridade_principal")
    estado_civil, pct_estado_civil = _weighted_dominant(working, "estado_civil_principal")
    pct_genero = _demographic_percent(working, "genero_principal", genero)
    pct_idade = _demographic_percent(working, "idade_principal", idade)
    pct_escolaridade = _demographic_percent(working, "escolaridade_principal", escolaridade)
    pct_estado_civil = _demographic_percent(working, "estado_civil_principal", estado_civil)
    summary, _ = _weighted_dominant(working, "perfil_resumo")
    if summary == "Nao informado":
        summary = persona

    confidence = 0.0
    if "confianca_persona" in working.columns:
        confidence_values = pd.to_numeric(working["confianca_persona"], errors="coerce")
        if "votos_candidato" in working.columns:
            weights = pd.to_numeric(working["votos_candidato"], errors="coerce").fillna(0)
            valid = confidence_values.notna() & weights.gt(0)
            if valid.any():
                confidence = float((confidence_values[valid] * weights[valid]).sum() / weights[valid].sum())
        elif confidence_values.notna().any():
            confidence = float(confidence_values.mean())

    return pd.DataFrame(
        [
            {
                "persona_executiva": persona,
                "perfil_resumo": summary,
                "genero_principal": genero,
                "pct_genero_principal": pct_genero,
                "idade_principal": idade,
                "pct_idade_principal": pct_idade,
                "escolaridade_principal": escolaridade,
                "pct_escolaridade_principal": pct_escolaridade,
                "estado_civil_principal": estado_civil,
                "pct_estado_civil_principal": pct_estado_civil,
                "confianca_persona": confidence,
            }
        ]
    )


def _render_icp_geral_card(icp_df: pd.DataFrame | None) -> None:
    kpis = [
        ("🟢 Gênero", "genero_principal", "pct_genero_principal", "#34d399"),
        ("🔵 Faixa etária", "idade_principal", "pct_idade_principal", "#60a5fa"),
        ("🟣 Escolaridade", "escolaridade_principal", "pct_escolaridade_principal", "#a78bfa"),
        ("🟡 Estado civil", "estado_civil_principal", "pct_estado_civil_principal", "#fbbf24"),
    ]
    has_profile = icp_df is not None and not icp_df.empty
    if has_profile:
        icp_df = _icp_general_row(icp_df)
        persona = sentence_label(_first_value(icp_df, "persona_executiva", "Persona executiva dominante"))
        summary = sentence_label(_first_value(icp_df, "perfil_resumo", "Resumo analítico da persona não informado."))
        normalize = lambda text: " ".join(text.casefold().split()).rstrip(".")
        summary_html = "" if normalize(summary) == normalize(persona) else f'<div class="dna-icp-summary">💬 {html.escape(summary)}</div>'
        if _has_profile_label(persona):
            attributes = [part.strip() for part in re.split(r"[,;|]", persona) if part.strip()]
        else:
            attributes = [
                sentence_label(_first_value(icp_df, value_col))
                for _, value_col, _, _ in kpis
            ]
            attributes = [value for value in attributes if _has_profile_label(value)]
    else:
        icp_df = pd.DataFrame()
        summary_html = ""
        attributes = []

    badge_html = " ".join(
        f'<span class="dna-icp-badge dna-icp-badge-{index % 4}">{html.escape(value)}</span>'
        for index, value in enumerate(attributes)
    )

    with st.container(border=True, key="dna_icp_general_card"):
        st.html(
            dedent(f"""
            <div class="dna-icp-heading">
                <h3 class="dna-subsection-title">Eleitor ideal do candidato</h3>
                <p class="dna-subsection-description">Síntese do perfil demográfico predominante na base eleitoral do candidato.</p>
            </div>
            {f'<div class="dna-icp-persona"><div class="dna-icp-persona-label">👤 PERFIL PREDOMINANTE</div><div class="dna-icp-badges">{badge_html}</div></div>' if badge_html else ''}
            {summary_html}
            """)
        )
        if not has_profile:
            st.info("Perfil geral indisponível para este candidato.")
            return

        metric_columns = st.columns(4, gap="medium")
        for index, (column, (label, value_col, pct_col, color)) in enumerate(zip(metric_columns, kpis)):
            value = sentence_label(_first_value(icp_df, value_col))
            pct = pd.to_numeric(pd.Series([_first_value(icp_df, pct_col, "")]), errors="coerce").iloc[0]
            with column:
                with st.container(border=True, key=f"dna_icp_metric_{index}"):
                    st.html(
                        f'<div class="dna-icp-kpi-label">{html.escape(label)}</div>'
                        f'<div class="dna-icp-kpi-value">{html.escape(value)}</div>'
                    )
                    if not pd.isna(pct) and 0 <= float(pct) <= 100:
                        indicator = go.Figure(
                            go.Indicator(
                                mode="gauge+number",
                                value=float(pct),
                                domain={"x": [0.07, 0.93], "y": [0.05, 0.98]},
                                number={
                                    "suffix": "%",
                                    "valueformat": ".1f",
                                    "font": {"size": 25, "color": "#f8fbff"},
                                },
                                gauge={
                                    "axis": {"range": [0, 100], "visible": False},
                                    "bar": {"color": color, "thickness": 0.48},
                                    "bgcolor": "rgba(147, 197, 253, 0.14)",
                                    "borderwidth": 0,
                                },
                            )
                        )
                        indicator.update_layout(
                            height=170,
                            margin={"l": 0, "r": 0, "t": 4, "b": 0},
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            separators=",.",
                        )
                        st.plotly_chart(
                            indicator,
                            width="stretch",
                            height=170,
                            key=f"dna_icp_pct_{index}",
                            config={"displayModeBar": False, "staticPlot": True},
                        )
                    else:
                        st.html('<div class="dna-icp-kpi-missing">Percentual indisponível</div>')


def _apply_icp_card_styles() -> None:
    st.html("""
    <style>
    .st-key-dna_icp_general_card {
        margin: 28px 0;
        padding: 30px !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        border-radius: 20px !important;
        background: linear-gradient(135deg, rgba(11, 31, 77, 0.76), rgba(7, 24, 54, 0.68)) !important;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.14) !important;
    }
    .st-key-dna_icp_metric_0,
    .st-key-dna_icp_metric_1,
    .st-key-dna_icp_metric_2,
    .st-key-dna_icp_metric_3 {
        min-height: 17rem;
        border: 1px solid rgba(177, 211, 255, 0.2) !important;
        border-radius: 14px !important;
        background: rgba(4, 18, 43, 0.34) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
    }
    .dna-icp-heading {
        border-bottom: 1px solid rgba(147, 197, 253, 0.2);
        padding-bottom: 1.25rem;
        margin-bottom: 1.35rem;
    }
    .dna-icp-heading .dna-subsection-description { font-size: 1rem; margin-bottom: 0; }
    .dna-icp-persona {
        margin: 0.5rem 0 1.5rem;
        text-align: center;
    }
    .dna-icp-persona-label {
        margin: 0 0 1rem;
        color: #f8fbff;
        font-size: 1.18rem;
        font-weight: 850;
        letter-spacing: 0.08em;
    }
    .dna-icp-badges {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 0.8rem;
        margin: 0;
    }
    .dna-icp-badge {
        display: inline-flex;
        align-items: center;
        min-height: 2.55rem;
        padding: 0.48rem 1rem;
        border: 1px solid rgba(147, 197, 253, 0.28);
        border-radius: 999px;
        color: #f8fbff;
        font-size: 1.06rem;
        font-weight: 750;
        line-height: 1.25;
    }
    .dna-icp-badge-0 { background: rgba(16, 185, 129, 0.16); border-color: rgba(52, 211, 153, 0.34); }
    .dna-icp-badge-1 { background: rgba(59, 130, 246, 0.17); border-color: rgba(96, 165, 250, 0.36); }
    .dna-icp-badge-2 { background: rgba(139, 92, 246, 0.17); border-color: rgba(167, 139, 250, 0.36); }
    .dna-icp-badge-3 { background: rgba(245, 158, 11, 0.16); border-color: rgba(251, 191, 36, 0.35); }
    .st-key-dna_icp_general_card .dna-icp-summary { text-align: center; }
    .dna-icp-kpi-label {
        color: #b7c7e6;
        font-size: 0.98rem;
        font-weight: 750;
        letter-spacing: 0.02em;
        text-align: center;
    }
    .dna-icp-kpi-value {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 3.1rem;
        margin-top: 0.55rem;
        color: #f8fbff;
        font-size: 1.12rem;
        font-weight: 750;
        line-height: 1.4;
        overflow-wrap: anywhere;
        text-align: center;
    }
    .dna-icp-kpi-missing {
        margin-top: 3rem;
        color: #b7c7e6;
        text-align: center;
    }
    .st-key-dna_icp_general_card [data-testid="stPlotlyChart"] { margin-top: 0.25rem; }
    @media (max-width: 900px) {
        .st-key-dna_icp_general_card [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
        .st-key-dna_icp_general_card [data-testid="stColumn"] {
            flex: 1 1 calc(50% - 0.75rem) !important;
            min-width: min(100%, 15rem);
        }
    }
    @media (max-width: 760px) {
        .st-key-dna_icp_general_card { padding: 18px !important; }
        .st-key-dna_icp_general_card [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            min-width: 100%;
        }
    }
    </style>
    """)


def _cluster_profiles(clusters_df: pd.DataFrame | None) -> list[dict]:
    if clusters_df is None or clusters_df.empty:
        return []
    df = _territorial_rows(clusters_df)
    if df.empty or not {"perfil_eleitor", "votos_candidato"}.issubset(df.columns):
        return []
    df["votos_candidato"] = pd.to_numeric(df["votos_candidato"], errors="coerce").fillna(0)
    totals = pd.to_numeric(df.get("total_votos_candidato", pd.Series(dtype=float)), errors="coerce").dropna()
    total = float(totals.iloc[0]) if not totals.empty else float(df["votos_candidato"].sum())
    fallback = df["votos_candidato"] / total * 100 if total > 0 else pd.Series(0.0, index=df.index)
    df["share"] = pd.to_numeric(df["pct_market_share"], errors="coerce").fillna(fallback) if "pct_market_share" in df else fallback
    profiles = []
    for profile, group in df.groupby("perfil_eleitor", sort=True):
        demographics = []
        for label, column in [("Gênero", "genero_principal"), ("Faixa etária", "idade_principal"), ("Escolaridade", "escolaridade_principal"), ("Estado civil", "estado_civil_principal")]:
            category, _ = _weighted_dominant(group, column)
            demographics.append((label, category, _demographic_percent(group, column, category)))
        profiles.append({"id": str(profile), "classification": _first_value(group, "cluster_strategy_label").strip().upper(),
                         "persona": _first_value(group, "persona_executiva"),
                         "reason": _first_value(group, "cluster_strategy_reason", "Recomendação estratégica não informada."),
                         "votes": float(group["votos_candidato"].sum()), "share": float(group["share"].sum()),
                         "demographics": demographics})
    return profiles


def _render_cluster_profiles(clusters_df: pd.DataFrame | None) -> None:
    st.html(cluster_cards_html(_cluster_profiles(clusters_df)))


def _municipal_rows(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if "nivel_territorial" not in df:
        return df.iloc[:0].copy()
    levels = df["nivel_territorial"].astype(str).str.strip().str.casefold()
    return df.loc[levels.eq("municipio")].copy()


def _canonical_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _municipality_codes(values: pd.Series) -> pd.Series:
    codes = values.astype("string").str.slice(0, 7)
    return codes.where(codes.str.len().eq(7))


def _census_demographics(
    gender: pd.DataFrame | None,
    age: pd.DataFrame | None,
    schooling: pd.DataFrame | None,
) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}

    for dimension, frame, prefix, excluded in (
        ("genero", gender, "populacao_genero_", {"nao_informado"}),
        ("idade", age, "populacao_idade_", {"invalido"}),
    ):
        if frame is None or frame.empty or "cd_area_ponderada" not in frame:
            result[dimension] = pd.DataFrame(columns=["codigo_ibge", "categoria", "percentual"])
            continue
        code = _municipality_codes(frame["cd_area_ponderada"])
        total_cols = [column for column in frame if column.startswith(prefix)]
        pieces = []
        for column in total_cols:
            category = column.removeprefix(prefix)
            if category in excluded:
                continue
            values = pd.to_numeric(frame[column], errors="coerce").fillna(0)
            pieces.append(pd.DataFrame({"codigo_ibge": code, "categoria": category, "populacao": values}))
        if pieces:
            totals = pd.concat(pieces, ignore_index=True).groupby(
                ["codigo_ibge", "categoria"], as_index=False
            )["populacao"].sum()
            denom = totals.groupby("codigo_ibge")["populacao"].transform("sum")
            totals["percentual"] = np.where(denom.gt(0), totals["populacao"] / denom * 100, np.nan)
            result[dimension] = totals[["codigo_ibge", "categoria", "percentual"]]
        else:
            result[dimension] = pd.DataFrame(columns=["codigo_ibge", "categoria", "percentual"])

    frame = schooling
    if frame is not None and not frame.empty and {"cd_municipio", "categoria", "pct_populacao_categoria"}.issubset(frame.columns):
        working = frame.copy()
        if "indicador" in working:
            working = working[
                working["indicador"].map(_canonical_text).eq("nivel instrucao")
            ]
        if "faixa_etaria" in working:
            working = working[
                working["faixa_etaria"].map(_canonical_text).eq("25 anos ou mais")
            ]
        working["codigo_ibge"] = _municipality_codes(working["cd_municipio"])
        working["percentual"] = pd.to_numeric(working["pct_populacao_categoria"], errors="coerce")
        population_weights = None
        for population_frame in (gender, age):
            if population_frame is not None and {"cd_area_ponderada", "populacao_total_ibge"}.issubset(population_frame.columns):
                population_weights = population_frame[["cd_area_ponderada", "populacao_total_ibge"]].drop_duplicates("cd_area_ponderada")
                break
        if population_weights is not None and "cd_area_ponderada" in working:
            working = working.merge(population_weights, on="cd_area_ponderada", how="left")
            working["peso"] = pd.to_numeric(working["populacao_total_ibge"], errors="coerce").fillna(0)
        elif "qt_votos_demografico" in working:
            working["peso"] = pd.to_numeric(working["qt_votos_demografico"], errors="coerce").fillna(0)
        else:
            working["peso"] = 1.0
        working = working[working["percentual"].between(0, 100)]
        working["ponderado"] = working["percentual"] * working["peso"]
        grouped = working.groupby(["codigo_ibge", "categoria"], as_index=False).agg(
            ponderado=("ponderado", "sum"), peso=("peso", "sum"), media=("percentual", "mean")
        )
        grouped["percentual"] = np.where(grouped["peso"].gt(0), grouped["ponderado"] / grouped["peso"], grouped["media"])
        result["escolaridade"] = grouped[["codigo_ibge", "categoria", "percentual"]]
    else:
        result["escolaridade"] = pd.DataFrame(columns=["codigo_ibge", "categoria", "percentual"])
    return result


def _census_category(dimension: str, profile_category: str) -> str:
    key = _canonical_text(profile_category)
    if dimension == "genero":
        if key in {"feminino", "mulher", "mulheres"}:
            return "feminino"
        if key in {"masculino", "homem", "homens"}:
            return "masculino"
    if dimension == "escolaridade":
        if "superior completo" in key:
            return "superior_completo"
        if "superior incompleto" in key or "medio completo" in key:
            return "medio_completo_superior_incompleto"
        if "medio incompleto" in key or "fundamental completo" in key:
            return "fundamental_completo_medio_incompleto"
        if "fundamental incompleto" in key or "sem instrucao" in key:
            return "sem_instrucao_fundamental_incompleto"
    return key.replace(" ", "_")


def _profile_snapshot(
    profile_kind: str,
    selected_label: str,
    icp_general: pd.DataFrame | None,
    icp_clusters: pd.DataFrame | None,
) -> tuple[dict[str, object], pd.DataFrame]:
    if profile_kind == "icp_geral":
        profile_df = _icp_general_row(icp_general.copy()) if icp_general is not None and not icp_general.empty else pd.DataFrame()
        source_rows = _municipal_rows(icp_general)
    else:
        source_rows = _municipal_rows(icp_clusters)
        if "cluster_strategy_label" in source_rows:
            source_rows = source_rows[source_rows["cluster_strategy_label"].fillna("").astype(str).str.strip().eq(selected_label)]
        profile_df = pd.DataFrame()
        if not source_rows.empty:
            profile_df = pd.DataFrame([{
                "genero_principal": _weighted_dominant(source_rows, "genero_principal")[0],
                "pct_genero_principal": _demographic_percent(source_rows, "genero_principal", _weighted_dominant(source_rows, "genero_principal")[0]),
                "idade_principal": _weighted_dominant(source_rows, "idade_principal")[0],
                "pct_idade_principal": _demographic_percent(source_rows, "idade_principal", _weighted_dominant(source_rows, "idade_principal")[0]),
                "escolaridade_principal": _weighted_dominant(source_rows, "escolaridade_principal")[0],
                "pct_escolaridade_principal": _demographic_percent(source_rows, "escolaridade_principal", _weighted_dominant(source_rows, "escolaridade_principal")[0]),
            }])
    snapshot: dict[str, object] = {"label": selected_label}
    for dimension, category_col, pct_col in (
        ("genero", "genero_principal", "pct_genero_principal"),
        ("idade", "idade_principal", "pct_idade_principal"),
        ("escolaridade", "escolaridade_principal", "pct_escolaridade_principal"),
    ):
        category = _first_value(profile_df, category_col, "")
        pct = pd.to_numeric(pd.Series([_first_value(profile_df, pct_col, "")]), errors="coerce").iloc[0]
        snapshot[dimension] = _census_category(dimension, category) if category else ""
        snapshot[f"{dimension}_label"] = category
        snapshot[f"{dimension}_pct"] = float(pct) if pd.notna(pct) else np.nan
    return snapshot, source_rows


def _candidate_votes_by_ibge(source_rows: pd.DataFrame) -> pd.DataFrame:
    if source_rows.empty or "votos_candidato" not in source_rows or "cd_municipio" not in source_rows:
        return pd.DataFrame(columns=["codigo_ibge", "votos_candidato"])
    votes = source_rows.copy()
    votes["cd_municipio"] = votes["cd_municipio"].astype("string")
    votes["votos_candidato"] = pd.to_numeric(votes["votos_candidato"], errors="coerce").fillna(0)
    votes = votes.groupby("cd_municipio", as_index=False)["votos_candidato"].sum()
    _, df_tse, _, _ = load_geo_reference()
    if df_tse is None or df_tse.empty:
        return pd.DataFrame(columns=["codigo_ibge", "votos_candidato"])
    result = votes.merge(
        df_tse[["codigo_tse", "codigo_ibge"]], left_on="cd_municipio", right_on="codigo_tse", how="left"
    )
    result["codigo_ibge"] = _municipality_codes(result["codigo_ibge"])
    return result.groupby("codigo_ibge", as_index=False)["votos_candidato"].sum()


def _potential_map(
    census: dict[str, pd.DataFrame], profile: dict[str, object], source_rows: pd.DataFrame
) -> tuple[object | None, str]:
    geojson_mg, _, municipalities, _ = load_geo_reference()
    if not geojson_mg or municipalities is None or municipalities.empty:
        return None, "A referência geográfica de Minas Gerais não está disponível."
    geo_ids = sorted({str(feature.get("properties", {}).get("id", "")) for feature in geojson_mg.get("features", [])})
    if not geo_ids:
        return None, "A malha municipal de Minas Gerais está vazia."
    frame = pd.DataFrame({"codigo_ibge_str": geo_ids})
    frame["codigo_ibge"] = _municipality_codes(frame["codigo_ibge_str"])
    municipality_names = municipalities[["codigo_ibge", "nome"]].copy()
    municipality_names["codigo_ibge"] = _municipality_codes(municipality_names["codigo_ibge"])
    frame = frame.merge(municipality_names, on="codigo_ibge", how="left")
    score_columns = []
    for dimension in ("genero", "idade", "escolaridade"):
        census_frame = census.get(dimension, pd.DataFrame())
        profile_category = str(profile.get(dimension, ""))
        profile_pct = pd.to_numeric(pd.Series([profile.get(f"{dimension}_pct")]), errors="coerce").iloc[0]
        score_col = f"aderencia_{dimension}"
        if census_frame.empty or not profile_category or pd.isna(profile_pct):
            frame[score_col] = np.nan
            frame[f"censo_{dimension}_pct"] = np.nan
        else:
            local = census_frame.copy()
            local["codigo_ibge"] = _municipality_codes(local["codigo_ibge"])
            local["categoria_key"] = local["categoria"].map(lambda value: _census_category(dimension, str(value)))
            local = local[local["categoria_key"].eq(profile_category)][["codigo_ibge", "percentual"]]
            local = local.groupby("codigo_ibge", as_index=False)["percentual"].mean()
            local = local.rename(columns={"percentual": f"censo_{dimension}_pct"})
            local[score_col] = (100 - (local[f"censo_{dimension}_pct"] - float(profile_pct)).abs()).clip(0, 100)
            frame = frame.merge(local[["codigo_ibge", f"censo_{dimension}_pct", score_col]], on="codigo_ibge", how="left")
        score_columns.append(score_col)
    available = frame[score_columns].notna().sum(axis=1)
    frame["aderencia_demografica"] = frame[score_columns].mean(axis=1, skipna=True)
    frame.loc[available.lt(3), "aderencia_demografica"] = np.nan

    votes = _candidate_votes_by_ibge(source_rows)
    frame = frame.merge(votes, on="codigo_ibge", how="left")
    frame["votos_candidato"] = frame["votos_candidato"].fillna(0.0)
    frame["compatibilidade"] = np.where(
        frame["votos_candidato"].gt(0), frame["aderencia_demografica"].fillna(0), 0.0
    )
    positive_scores = frame.loc[frame["compatibilidade"].gt(0), "compatibilidade"]
    frame["compatibilidade_log"] = 0.0
    if not positive_scores.empty:
        low_score = float(positive_scores.min())
        high_score = float(positive_scores.max())
        if high_score > low_score:
            log_low, log_high = np.log1p(low_score), np.log1p(high_score)
            frame.loc[frame["compatibilidade"].gt(0), "compatibilidade_log"] = 0.08 + 0.92 * (
                np.log1p(positive_scores) - log_low
            ) / (log_high - log_low)
        else:
            frame.loc[frame["compatibilidade"].gt(0), "compatibilidade_log"] = 0.85
    frame["municipio"] = frame["nome"].fillna("Município")

    fig = continuous_choropleth(
        frame, geojson_mg, location="codigo_ibge_str", color="compatibilidade_log",
        colors=["#e8f5e9", "#c8e6c9", "#81c784", "#43a047", "#14532d"],
        hover_name="municipio", custom_data=["compatibilidade", "aderencia_demografica", "votos_candidato"],
        colorbar_title="Compatibilidade", color_range=(0, 1),
    )
    fig.update_traces(hovertemplate=(
        "<b>%{hovertext}</b><br>Compatibilidade: %{customdata[0]:.1f}/100"
        "<br>Aderência: %{customdata[1]:.1f}/100<br>Votos: %{customdata[2]:,.0f}<extra></extra>"
    ))
    note = "A compatibilidade é a média das aderências de gênero, idade e escolaridade. Municípios sem votos ou sem os três cruzamentos completos ficam no valor mínimo; a escala de cor é logarítmica."
    return fig, note


def _render_demographic_potential_analysis() -> None:
    icp_general = _read_selected_parquet("icp_geral")
    icp_clusters = _read_selected_parquet("icp_clusters")
    labels = ["ELEITOR IDEAL"]
    if icp_clusters is not None and "cluster_strategy_label" in icp_clusters:
        labels += sorted(
            value for value in icp_clusters["cluster_strategy_label"].dropna().astype(str).str.strip().unique() if value
        )
    _, right = st.columns([0.64, 0.36], vertical_alignment="bottom")
    with right:
        selected_label = st.selectbox(
            "Perfil de eleitor", labels, key="dna_demographic_potential_profile"
        )
    if selected_label == "ELEITOR IDEAL":
        profile_kind = "icp_geral"
    else:
        profile_kind = "icp_clusters"

    profile, source_rows = _profile_snapshot(profile_kind, selected_label, icp_general, icp_clusters)
    census = {
        "genero": _read_selected_parquet("censo_genero"),
        "idade": _read_selected_parquet("censo_idade"),
        "escolaridade": _read_selected_parquet("censo_escolaridade"),
    }
    census = _census_demographics(census["genero"], census["idade"], census["escolaridade"])
    fig, note = _potential_map(census, profile, source_rows)
    if fig is None:
        st.info(note)
        return
    st.caption(
        "Perfil comparado: " + " · ".join(
            f"{label}: {profile.get(dimension + '_label', 'não informado')} ({_format_percent_value(str(profile.get(dimension + '_pct', '')))} no perfil)"
            for dimension, label in (("genero", "Gênero"), ("idade", "Idade"), ("escolaridade", "Escolaridade"))
        )
    )
    st.plotly_chart(fig, width="stretch", height=620, key="dna_demographic_potential_map")
    st.caption(note)


def _potential_cards(rows: pd.DataFrame, profile: Profile, scope: str) -> None:
    if rows.empty:
        st.info("Dados demográficos indisponíveis para o recorte.")
        return
    summary = rows.copy()
    summary["municipio"] = "recorte"
    totals = alignment(summary, profile, by_municipality=True).iloc[0]

    def percent(value: object) -> str:
        return f"{float(value):.1f}%".replace(".", ",") if pd.notna(value) else "—"

    def population(value: object) -> str:
        return f"{int(value):,}".replace(",", ".") if pd.notna(value) else "—"

    cards = [
        ("População nas áreas com dados", population(totals["populacao"]),
         "Censo 2022 · todas as idades"),
        ("Alinhamento demográfico", f'{percent(totals["alinhamento"])}'.replace("%", "/100"),
         f'{int(totals["dimensoes"])} de 2 dimensões válidas'),
        ("Gênero do ICP", percent(totals["local_genero"]),
         f'Local × ICP {percent(profile.percentages.get("genero"))}'),
        ("Faixa etária do ICP", percent(totals["local_idade"]),
         f'Local × ICP {percent(profile.percentages.get("idade"))}'),
    ]
    st.html('<div class="dna-potential-side-cards" aria-label="Resumo demográfico de ' + html.escape(scope) + '">' + "".join(
        '<div class="dna-potential-side-card">'
        f'<div class="dna-potential-card-label">{html.escape(label)}</div>'
        f'<div class="dna-potential-card-value">{html.escape(value)}</div>'
        f'<div class="dna-potential-card-detail">{html.escape(detail)}</div>'
        '</div>' for label, value, detail in cards
    ) + '</div>')


def _profile_select(profiles: list[Profile], key: str) -> Profile:
    choices = {profile.key: profile for profile in profiles}
    selected = st.selectbox(
        "Perfil de eleitor", list(choices), format_func=lambda value: choices[value].label,
        key=key,
    )
    return choices[selected]


def _render_state_demographic_potential(population: pd.DataFrame, profiles: list[Profile]) -> None:
    map_col, cards_col = st.columns([0.70, 0.30], gap="large")
    card_rows = population
    card_profile = profiles[0]
    scope = "Minas Gerais"
    with map_col:
        with st.container(border=True, key="dna_state_potential_map_card"):
            try:
                _, profile_col = st.columns([0.57, 0.43], vertical_alignment="bottom")
                with profile_col:
                    card_profile = _profile_select(profiles, "dna_state_alignment_profile")
                selected_mesorregiao = st.selectbox(
                    "Mesorregião",
                    ["Todas", *mesoregion_options()],
                    key="dna_state_potential_mesorregiao",
                )
                municipality_choices = municipality_options(selected_mesorregiao)
                if not municipality_choices:
                    st.info("Nenhum município disponível para a mesorregião selecionada.")
                else:
                    municipality_labels = dict(municipality_choices)
                    selected_code = st.selectbox(
                        "Município",
                        ["", *municipality_labels],
                        format_func=lambda code: (
                            "Todos os municípios" if not code else municipality_labels.get(code, code)
                        ),
                        key=f"dna_state_potential_municipio_{selected_mesorregiao}",
                    )
                    geojson, _, municipalities, _ = load_geo_reference()
                    if not geojson or municipalities is None:
                        st.info("Malha municipal de Minas Gerais indisponível.")
                        return
                    scores = alignment(population, card_profile, by_municipality=True)
                    allowed = {code for code, _ in municipality_choices}
                    scores = scores.loc[scores["municipio"].isin(allowed)].copy()
                    names = municipalities.drop_duplicates("codigo_ibge").set_index("codigo_ibge")["nome"]
                    fig = alignment_map(scores, geojson, key="municipio", names=names,
                                        profile=card_profile,
                                        selected_code=selected_code)
                    st.plotly_chart(fig, width="stretch", key="dna_state_potential_municipality_mesh",
                                    config={"displayModeBar": False})
                    if selected_code:
                        card_rows = population.loc[population["municipio"].eq(selected_code)]
                        scope = municipality_labels[selected_code]
                    elif selected_mesorregiao != "Todas":
                        card_rows = population.loc[population["municipio"].isin(allowed)]
                        scope = selected_mesorregiao
                    st.caption(
                        "Escala verde: média de min(percentual local, percentual ICP) / "
                        "max(percentual local, percentual ICP) em gênero e idade. "
                        "O cálculo usa as áreas com dados; escolaridade não compõe a cor. "
                        "É uma comparação descritiva, não uma estimativa de votos."
                    )
            except Exception as exc:
                st.warning(f"Não foi possível carregar o alinhamento estadual: {exc}")
    with cards_col:
        _potential_cards(card_rows, card_profile, scope)


def _render_demographic_potential(population: pd.DataFrame, profiles: list[Profile]) -> None:
    map_col, cards_col = st.columns([0.70, 0.30], gap="large")
    card_rows = pd.DataFrame()
    card_profile = profiles[0]
    scope = "município"
    with map_col:
        with st.container(border=True, key="dna_potential_map_card"):
            try:
                _, profile_col = st.columns([0.57, 0.43], vertical_alignment="bottom")
                with profile_col:
                    card_profile = _profile_select(profiles, "dna_municipal_alignment_profile")
                mesoregions = mesoregion_options()
                selected_mesorregiao = st.selectbox(
                    "Mesorregião",
                    ["Todas", *mesoregions],
                    key="dna_potential_mesorregiao",
                )
                municipality_choices = municipality_options(selected_mesorregiao)
                if not municipality_choices:
                    st.info("Nenhum município disponível para a mesorregião selecionada.")
                else:
                    selected_code = st.selectbox(
                        "Município",
                        [code for code, _ in municipality_choices],
                        format_func=dict(municipality_choices).get,
                        key=f"dna_potential_municipio_{selected_mesorregiao}",
                    )
                    scope = dict(municipality_choices)[selected_code]
                    card_rows = population.loc[population["municipio"].eq(selected_code)].copy()
                    areas = load_geo_layer("area_ponderada")
                    areas = areas.loc[areas["code_muni"].astype("string").eq(selected_code)].copy()
                    areas["code_weighting"] = areas["code_weighting"].astype("string").str.zfill(10)
                    neighborhoods = area_neighborhoods(
                        load_area_ponderada_bairro_crosswalk(), selected_code
                    )
                    area_codes = sorted(areas["code_weighting"].dropna().unique())
                    selected_area = st.selectbox(
                        "Área ponderada",
                        ["", *area_codes],
                        format_func=lambda code: (
                            "Todas as áreas ponderadas" if not code else
                            f"{code} · {str(neighborhoods.get(code, 'sem bairro vinculado'))[:75]}"
                        ),
                        key=f"dna_potential_area_{selected_code}",
                    )
                    if selected_area:
                        card_rows = card_rows.loc[card_rows["area"].eq(selected_area)]
                        scope = f"área ponderada {selected_area}"
                    if areas.empty:
                        st.info("Áreas ponderadas ou população indisponíveis para este município.")
                    else:
                        municipality_rows = population.loc[population["municipio"].eq(selected_code)]
                        scores = alignment(municipality_rows, card_profile, by_municipality=False)
                        names = municipality_rows.drop_duplicates("area").set_index("area").index.to_series().map(
                            lambda value: f"Área ponderada {value}"
                        )
                        fig = alignment_map(scores, weighted_area_geojson(areas), key="area",
                                            names=names, profile=card_profile,
                                            context=neighborhoods, selected_code=selected_area)
                        st.plotly_chart(fig, width="stretch", key="dna_potential_municipality_mesh",
                                        config={"displayModeBar": False})
                        if selected_area:
                            st.caption(
                                f"Área {selected_area}: {neighborhoods.get(selected_area, 'sem bairro vinculado')}. "
                                "O vínculo do bairro é por ponto de referência; os percentuais representam a área ponderada."
                            )
                        if len(areas) == 1:
                            st.caption("Este município possui uma única área ponderada; não há detalhe dentro do município.")
                        else:
                            missing = len(areas) - len(scores)
                            note = f"{len(areas)} áreas ponderadas do Censo 2022. Passe o cursor para comparar população local e ICP."
                            if missing:
                                note += f" {missing} área(s) em cinza não têm população no arquivo deste candidato."
                            note += " Bairros vinculados pelo crosswalk territorial, sem redistribuir a população entre eles."
                            st.caption(note)
            except Exception as exc:
                st.warning(f"Não foi possível carregar o alinhamento municipal: {exc}")
    with cards_col:
        _potential_cards(card_rows, card_profile, scope)


apply_shared_visual_model()
_apply_icp_card_styles()
render_page_header("dna")

DNA_SECTIONS = [
    (
        "Identidade da Base Eleitoral",
        "Quem é o eleitor-chave e quais atributos definem o perfil do seu eleitor.",
    ),
    (
        "Distribuição do Perfil do Eleitorado",
        "Distribuição demográfica estimada dos votos, com recorte por município e perfil.",
    ),
    (
        "Matriz de Potencial Demográfico",
        "Comparativo entre o perfil do eleitor do candidato e a população local. Identificação de sobre-representação e frentes de expansão.",
    ),
]


for index, (section_title, section_subtitle) in enumerate(DNA_SECTIONS):
    major_section_header(section_title, section_subtitle)
    if index == 0:
        icp_general_df = _read_selected_parquet("icp_geral")
        _render_icp_geral_card(icp_general_df)
    elif index == 2:
        census_general = _read_selected_parquet("censo_icp_geral")
        census_clusters = _read_selected_parquet("censo_icp_clusters")
        profiles = profile_options(census_general, census_clusters)
        population = population_by_area(
            _read_selected_parquet("censo_genero"), _read_selected_parquet("censo_idade")
        )
        if not profiles or population.empty:
            st.info("Dados do ICP ou do Censo indisponíveis para o candidato selecionado.")
            continue
        section_header("Potencial Demográfico Estadual")
        _render_state_demographic_potential(population, profiles)
        section_header("Potencial demográfico municipal")
        _render_demographic_potential(population, profiles)
    else:
        render_electorate_distribution(_read_selected_parquet)
        _render_cluster_profiles(_read_selected_parquet("icp_clusters"))
        major_section_header(
            "Expansão & Oportunidades para 2030",
            "Mapeamento em nível de bairro e área ponderada. Localização dos clusters táticos e visualização de manchas de potencial de crescimento.",
        )
        render_vote_expansion()
