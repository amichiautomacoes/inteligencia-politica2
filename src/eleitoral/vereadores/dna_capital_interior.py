"""Comparação do eleitor da capital e do interior, exclusiva de vereadores."""
from __future__ import annotations
import html
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from hf_sync import load_env, load_parquet
from eleitoral.common.shared_header import selected_files, major_section_header
from eleitoral.common.dna_copy import sentence_label
from eleitoral.common.dna_profile import _territorial_rows, _weighted_dominant, _demographic_percent, _has_profile_label
from eleitoral.dna.dna_distribution import _distribution

def _comparison_sources(icp_df: pd.DataFrame | None, _read_selected_parquet) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    capital = None
    primary_path = next(iter(selected_files()), None)
    if primary_path:
        # The selected base can be either an annual folder or bh_2026.
        parts = primary_path.replace("\\", "/").split("/")
        partition = next((index for index, part in enumerate(parts)
                          if (part.isdigit() and len(part) == 4)
                          or (part.startswith("bh_") and part[3:].isdigit())), None)
        root = "/".join(parts[:partition]) if partition is not None else ""
        for folder in ("bh_vereador", "bh_2026"):
            try:
                capital = load_parquet(f"{root}/{folder}/perfil/icp_geral_por_bairro.parquet", load_env().get("HF_TOKEN"))
                break
            except FileNotFoundError:
                continue
            except Exception:
                st.warning("Não foi possível carregar o perfil dos bairros de Belo Horizonte.")
                break
    if capital is not None:
        capital = capital.copy()
        if "situacao_icp" in capital:
            capital = capital.loc[capital["situacao_icp"].eq("calculado")].copy()
        capital = capital.rename(columns={"qt_votos_candidato_bairro": "votos_candidato"})
    interior = icp_df
    if interior is not None:
        interior = _territorial_rows(interior)
        is_capital = pd.Series(False, index=interior.index)
        if "cd_municipio" in interior:
            is_capital |= interior["cd_municipio"].astype(str).isin(["41238", "3106200"])
        if "nm_municipio" in interior:
            is_capital |= interior["nm_municipio"].astype(str).str.strip().str.casefold().eq("belo horizonte")
        interior = interior.loc[~is_capital].copy()
    if interior is not None and "metodo_icp_geo" in interior and interior["metodo_icp_geo"].eq("perfil_geral_global_replicado_no_territorio_do_stage01b").any():
        # The new stage04 repeats the statewide persona; stage02 retains local distributions.
        record = {"votos_candidato": 1.0}
        for dimension in ("genero", "idade", "escolaridade", "estado_civil"):
            frame = _read_selected_parquet(dimension)
            if frame is None:
                continue
            frame = _territorial_rows(frame)
            frame = frame.loc[~frame["cd_municipio"].astype(str).isin(["41238", "3106200"])]
            distribution = _distribution(frame, f"pct_{dimension}_")
            if not distribution.empty:
                top = distribution.iloc[0]
                record[f"{dimension}_principal"] = top["categoria"]
                record[f"pct_{dimension}_principal"] = top["percentual"]
        interior = pd.DataFrame([record])
    return capital, interior


def render_capital_interior_comparison(icp_df: pd.DataFrame | None, _read_selected_parquet) -> None:
    major_section_header(
        "Eleitor de BH x Eleitor do Interior",
        "Será que você tem o mesmo perfil de eleitor na capital e no interior?",
    )
    capital, interior = _comparison_sources(icp_df, _read_selected_parquet)
    dimensions = [
        ("Gênero", "genero_principal", "#34d399"),
        ("Idade", "idade_principal", "#60a5fa"),
        ("Escolaridade", "escolaridade_principal", "#a78bfa"),
        ("Estado civil", "estado_civil_principal", "#fbbf24"),
    ]
    for column, (scope, title, source) in zip(st.columns(2, gap="medium"), [
        ("capital", "Eleitor da capital", capital),
        ("interior", "Eleitor do Interior", interior),
    ]):
        with column:
            with st.container(border=True, key=f"dna_{scope}_profile_card"):
                st.html(f'<div class="dna-icp-heading"><h3 class="dna-subsection-title">{title}</h3></div>')
                if source is None or source.empty:
                    st.info("Perfil indisponível para este recorte.")
                    continue
                source = source.copy()
                if "votos_candidato" not in source:
                    st.info("Votos de referência indisponíveis para consolidar o perfil.")
                    continue
                source["votos_candidato"] = pd.to_numeric(source["votos_candidato"], errors="coerce").fillna(0).clip(lower=0)
                source = source.loc[source["votos_candidato"].gt(0)]
                rows = []
                for label, field, color in dimensions:
                    category, _ = _weighted_dominant(source, field)
                    percentage = _demographic_percent(source, field, category)
                    if _has_profile_label(category) and pd.notna(percentage):
                        rows.append((label, sentence_label(category.replace("_", " ")), percentage, color))
                if not rows:
                    st.info("Percentuais demográficos indisponíveis para este recorte.")
                    continue
                badges = "".join(
                    f'<span class="dna-comparison-badge" style="--badge-color:{color}">'
                    f'<b>{html.escape(label)}:</b> {html.escape(category)}</span>'
                    for label, category, _, color in rows
                )
                st.html(f'<div class="dna-icp-badges dna-comparison-badges">{badges}</div>')
                fig = go.Figure(go.Bar(
                    y=[row[0] for row in rows], x=[row[2] for row in rows], orientation="h",
                    marker_color=[row[3] for row in rows],
                    customdata=[row[1] for row in rows],
                    text=[f'{row[2]:.1f}%'.replace(".", ",") for row in rows],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="<b>%{y}: %{customdata}</b><br>%{x:.1f}%<extra></extra>",
                ))
                fig.update_layout(
                    height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin={"l": 0, "r": 48, "t": 12, "b": 20},
                    font={"color": "#eaf2ff", "size": 14}, separators=",.", bargap=.4,
                    xaxis={"range": [0, 100], "ticksuffix": "%", "gridcolor": "rgba(147,197,253,.12)", "fixedrange": True},
                    yaxis={"autorange": "reversed", "fixedrange": True}, showlegend=False,
                )
                st.plotly_chart(fig, width="stretch", key=f"dna_{scope}_profile_bars", config={"displayModeBar": False})
                if len(rows) < len(dimensions):
                    st.caption("Dimensões sem percentual válido não são exibidas.")
