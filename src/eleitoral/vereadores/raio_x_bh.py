"""Histórico de BH, projeção demográfica e indicadores exclusivos de vereadores."""
from __future__ import annotations
import html
import pandas as pd
import streamlit as st
from eleitoral.common.shared_header import major_section_header
from eleitoral.common.raio_x_cards import _format_number, _format_percent, _normalized_text, _map_side_card
from eleitoral.vereadores.bh_projection import bh_projection_map_frame as _bh_projection_map_frame
from eleitoral.maps.territorial_mesh import BH_PROJECTION_CATEGORY_COLORS, municipality_mesh_map, municipality_neighborhood_category_map

def _candidate_total_votes_for_year(
    votes_df: pd.DataFrame | None,
    year: str,
) -> float | None:
    if votes_df is None or votes_df.empty:
        return None
    vote_column = {
        "2020": "qt_votos_candidato_2020",
        "2024": "qt_votos_candidato_2024",
        "2026": "qt_votos",
    }.get(str(year))
    if vote_column is None or vote_column not in votes_df.columns:
        return None
    rows = votes_df
    if "nivel_territorial" in rows.columns:
        municipal_rows = rows.loc[
            rows["nivel_territorial"].astype(str).str.strip().str.casefold().eq("municipio")
        ]
        if not municipal_rows.empty:
            rows = municipal_rows
    values = pd.to_numeric(rows[vote_column], errors="coerce")
    if not values.notna().any():
        return None
    return float(values.fillna(0).sum())


def _render_neighborhood_side_cards(
    df: pd.DataFrame | None,
    municipality_code: str | None,
    *,
    year: str | int = "2026",
    municipality_votes_df: pd.DataFrame | None = None,
    statewide_votes_df: pd.DataFrame | None = None,
    total_neighborhoods: int | None = None,
) -> None:
    card = _map_side_card
    year = str(year)
    required = {"cd_ibge_municipio", "nm_bairro", "qt_votos"}
    municipality_rows = pd.DataFrame()
    rows = pd.DataFrame()
    if df is not None and municipality_code is not None and required.issubset(df.columns):
        codes = df["cd_ibge_municipio"].astype("string")
        municipality_rows = df.loc[codes.eq(str(municipality_code))].copy()
        rows = municipality_rows[["nm_bairro", "qt_votos"]].copy()
        rows["nm_bairro"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
        rows["qt_votos"] = pd.to_numeric(rows["qt_votos"], errors="coerce").fillna(0)
        rows = rows.loc[rows["nm_bairro"].ne("")]

    municipal_vote_column = {
        "2020": "qt_votos_candidato_2020",
        "2024": "qt_votos_candidato_2024",
        "2026": "qt_votos",
    }.get(year, "qt_votos")
    municipal_total = None
    if (
        municipality_votes_df is not None
        and municipality_code is not None
        and {"cd_ibge_municipio", municipal_vote_column}.issubset(municipality_votes_df.columns)
    ):
        municipal_codes = municipality_votes_df["cd_ibge_municipio"].astype("string")
        selected_municipality = municipality_votes_df.loc[
            municipal_codes.eq(str(municipality_code)), municipal_vote_column
        ]
        if not selected_municipality.empty:
            numeric_total = pd.to_numeric(selected_municipality, errors="coerce")
            if numeric_total.notna().any():
                municipal_total = float(numeric_total.fillna(0).sum())
    if municipal_total is None and not municipality_rows.empty:
        neighborhood_total = pd.to_numeric(
            municipality_rows.get("qt_votos", pd.Series(dtype=float)), errors="coerce"
        )
        if neighborhood_total.notna().any():
            municipal_total = float(neighborhood_total.fillna(0).sum())
    candidate_total = _candidate_total_votes_for_year(statewide_votes_df, year)
    if candidate_total is None and year in {"2020", "2024"}:
        # In these two municipal elections, the selected candidacies represented in this dataset were in Belo Horizonte.
        candidate_total = municipal_total
    candidate_share = (
        municipal_total / candidate_total
        if municipal_total is not None and candidate_total is not None and candidate_total > 0
        else None
    )
    municipal_badge = (
        f"Total municipal · {_format_number(municipal_total)} votos"
        if municipal_total is not None else ""
    )
    cards = [
        card(
            f"Votos em Belo Horizonte ({year})",
            _format_percent(candidate_share) if candidate_share is not None else "—",
            "",
            municipal_badge,
            "good" if municipal_badge else "",
        )
    ]

    def neighborhood_concentration(with_votes: int) -> tuple[str, str]:
        if total_neighborhoods is None or total_neighborhoods <= 0:
            return "", ""
        coverage = min(with_votes / total_neighborhoods, 1.0)
        if coverage < 1 / 3:
            return "Concentração baixa", "bad"
        if coverage <= 2 / 3:
            return "Concentração moderada", "warn"
        return "Concentração alta", "good"

    def neighborhood_coverage_card(with_votes: int) -> str:
        concentration, tone = neighborhood_concentration(with_votes)
        if total_neighborhoods is None or total_neighborhoods <= 0:
            return card(
                "Penetração por bairros",
                f"{_format_number(with_votes)} bairros com voto",
                "Total de bairros oficiais indisponível",
            )
        coverage = min(with_votes / total_neighborhoods, 1.0)
        return card(
            "Penetração por bairros",
            f"{_format_number(with_votes)} bairros com voto",
            f"{_format_percent(coverage)} dos {_format_number(total_neighborhoods)} bairros oficiais",
            concentration,
            tone,
        )

    def density_concentration(votes_per_neighborhood: int) -> tuple[str, str]:
        if votes_per_neighborhood < 100:
            return "Concentração baixa", "bad"
        if votes_per_neighborhood <= 300:
            return "Concentração moderada", "warn"
        return "Concentração alta", "good"

    if rows.empty:
        cards.extend([
            card("Bairro principal (Top 1)", "—", "Dados de bairros indisponíveis"),
            card("Dependência do bairro principal", "—", "Dados de bairros indisponíveis"),
            neighborhood_coverage_card(0) if not municipality_rows.empty else card(
                "Penetração por bairros", "—", "Dados de bairros indisponíveis"
            ),
            card("Densidade média por bairro", "—", "Dados de bairros indisponíveis"),
        ])
    else:
        rows["_bairro"] = rows["nm_bairro"].map(_normalized_text)
        by_name = rows.groupby("_bairro")["qt_votos"].sum()
        by_name = by_name.loc[by_name.index != ""]
        total = float(by_name.sum())
        with_votes = int(by_name.gt(0).sum())
        leader_key = str(by_name.idxmax()) if total > 0 else ""
        leader_name = (
            str(rows.loc[rows["_bairro"].eq(leader_key), "nm_bairro"].iloc[0]).title()
            if leader_key else "—"
        )
        leader_votes = float(by_name.max()) if total > 0 else 0.0
        share = leader_votes / total if total > 0 else 0.0
        average_votes_per_neighborhood = round(total / with_votes) if with_votes else None
        density_badge, density_tone = (
            density_concentration(average_votes_per_neighborhood)
            if average_votes_per_neighborhood is not None
            else ("", "")
        )
        cards.extend([
            card(
                "Bairro principal (Top 1)",
                f"{leader_name} ({_format_percent(share)})" if total > 0 else "—",
                f"{_format_number(leader_votes)} votos no bairro líder" if total > 0 else "Sem votos por bairro",
                "Alta concentração" if share > 0.30 else "Bairro líder",
                "warn" if share > 0.30 else "good",
            ),
            card(
                "Dependência do bairro principal",
                _format_percent(share) if total > 0 else "—",
                "Dos votos nos bairros do município" if total > 0 else "Sem votos por bairro",
                "Alerta de concentração" if share > 0.30 else "Concentração moderada",
                "warn" if share > 0.30 else "good",
            ),
            neighborhood_coverage_card(with_votes),
            card(
                "Densidade média por bairro",
                f"{_format_number(average_votes_per_neighborhood)} votos"
                if average_votes_per_neighborhood is not None else "—",
                "Por Bairro" if with_votes else "Sem votos por bairro",
                density_badge,
                density_tone,
            ),
        ])
    st.markdown('<div class="raiox-map-side-cards">' + "".join(cards) + '</div>', unsafe_allow_html=True)


def _render_bh_comparison_legend() -> None:
    legend_items = [
        ("Ganhou participação", "#86efac", "rgba(34, 197, 94, 0.16)", "#22c55e"),
        ("Sem variação", "#93c5fd", "rgba(59, 130, 246, 0.16)", "#3b82f6"),
        ("Perdeu participação", "#fca5a5", "rgba(239, 68, 68, 0.16)", "#ef4444"),
        ("Sem comparação", "#cbd5e1", "rgba(148, 163, 184, 0.16)", "#94a3b8"),
    ]
    badges_html = "".join(
        '<span style="display:inline-flex;align-items:center;gap:7px;white-space:nowrap;'
        f'padding:5px 10px;border:1px solid {marker_color};border-radius:999px;'
        f'background:{background};color:{text_color};font-size:.76rem;font-weight:700">'
        f'<span aria-hidden="true" style="width:8px;height:8px;border-radius:50%;'
        f'background:{marker_color}"></span>{html.escape(label)}</span>'
        for label, text_color, background, marker_color in legend_items
    )
    st.html(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px">{badges_html}</div>'
    )


def _render_bh_projection_legend() -> None:
    legend_items = [
        ("Base Crítica (Fortaleza)", "Base Crítica (Fortaleza)", "#bfdbfe", "rgba(37, 99, 235, 0.18)"),
        ("Vulnerável/Ameaçado", "Vulnerável", "#fef08a", "rgba(250, 204, 21, 0.18)"),
        ("Oportunidade BH", "Oportunidade", "#86efac", "rgba(34, 197, 94, 0.18)"),
        ("Demais bairros", "Demais bairros", "#cbd5e1", "rgba(148, 163, 184, 0.16)"),
    ]
    badges_html = "".join(
        '<span style="display:inline-flex;align-items:center;gap:7px;white-space:nowrap;'
        f'padding:5px 10px;border:1px solid {BH_PROJECTION_CATEGORY_COLORS[category]};'
        f'border-radius:999px;background:{background};color:{text_color};'
        f'font-size:.76rem;font-weight:700">'
        f'<span aria-hidden="true" style="width:8px;height:8px;border-radius:50%;'
        f'background:{BH_PROJECTION_CATEGORY_COLORS[category]}"></span>{html.escape(label)}</span>'
        for category, label, text_color, background in legend_items
    )
    st.html(
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px">{badges_html}</div>'
    )


def render_bh_voting(votos_municipio_df, votos_bairro_df, _read_selected_parquet) -> None:
    major_section_header(
        "Como foi sua votação em Belo Horizonte",
        "Veja o histórico dos seus votos na sua Base Eleitoral",
    )
    selected_bh_neighborhood_df = votos_bairro_df
    selected_bh_municipality_df = votos_municipio_df
    bh_cards_year = "2026"
    bh_mesh_neighborhood_count = None
    detail_map_col, detail_cards_col = st.columns([0.70, 0.30], gap="large")
    with detail_map_col:
        with st.container(border=True):
            bh_map_year_key = "bh_neighborhood_map_year_segmented"
            bh_map_year_options = ["2020", "2024", "2026", "Projeção 2028"]
            if st.session_state.get(bh_map_year_key) not in bh_map_year_options:
                st.session_state[bh_map_year_key] = "2026"
            bh_map_year = st.segmented_control(
                "Eleição exibida no mapa",
                bh_map_year_options,
                selection_mode="single",
                key=bh_map_year_key,
            )
            try:
                # Belo Horizonte is fixed for this section (IBGE municipality code).
                if bh_map_year in {"2020", "2024"}:
                    bh_cards_year = bh_map_year
                    _render_bh_comparison_legend()
                    comparison_df = _read_selected_parquet("votos_bairro", scope="bh")
                    history_vote_column = f"qt_votos_candidato_bairro_{bh_map_year}"
                    if comparison_df is not None and history_vote_column in comparison_df.columns:
                        selected_bh_neighborhood_df = comparison_df.copy()
                        selected_bh_neighborhood_df["qt_votos"] = pd.to_numeric(
                            selected_bh_neighborhood_df[history_vote_column], errors="coerce"
                        ).fillna(0)
                    else:
                        selected_bh_neighborhood_df = None
                    selected_bh_municipality_df = _read_selected_parquet(
                        "votos_municipio", scope="bh"
                    )
                    mesh_fig, mesh_count = municipality_mesh_map(
                        "3106200", comparison_df, comparison_year=bh_map_year
                    )
                elif bh_map_year == "Projeção 2028":
                    projection_df = _read_selected_parquet(
                        "bh_potencial_bairro", scope="bh"
                    )
                    projection_map_df = _bh_projection_map_frame(
                        projection_df, _read_selected_parquet("votos_bairro", scope="bh")
                    )
                    _render_bh_projection_legend()
                    mesh_fig, mesh_count = municipality_neighborhood_category_map(
                        "3106200", projection_map_df
                    )
                else:
                    mesh_fig, mesh_count = municipality_mesh_map(
                        "3106200",
                        votos_bairro_df,
                        log_scale_gamma=0.8,
                        zero_vote_color="#64748b",
                    )
                if mesh_fig is not None and (mesh_fig.layout.meta or {}).get("mesh_kind") == "bairro":
                    bh_mesh_neighborhood_count = mesh_count
                if mesh_fig is None:
                    if bh_map_year in {"2020", "2024"}:
                        st.info(f"Comparação de votos por bairro para {bh_map_year} indisponível nesta pasta.")
                    elif bh_map_year == "Projeção 2028":
                        st.info("Projeção estratégica de 2028 indisponível para Belo Horizonte nesta pasta.")
                    else:
                        st.info("Mapa de votos por bairro indisponível para Belo Horizonte.")
                else:
                    st.plotly_chart(
                        mesh_fig,
                        width="stretch",
                        height=680,
                        key=f"pagina1_malha_belo_horizonte_{bh_map_year}",
                    )
                    mesh_kind = (mesh_fig.layout.meta or {}).get("mesh_kind")
                    scale_type = (mesh_fig.layout.meta or {}).get("scale_type")
                    if bh_map_year in {"2020", "2024"}:
                        st.caption(
                            f"O mapa compara a participação do candidato em {bh_map_year} e 2026. "
                            "O tooltip mostra os votos totais de cada eleição e a diferença em pontos percentuais, "
                            "calculada nos locais de votação correspondidos. Os cards laterais mostram os indicadores "
                            f"da eleição selecionada ({bh_map_year})."
                        )
                    elif bh_map_year == "Projeção 2028":
                        st.caption(
                            "Classificação descritiva por votos de referência e espaço demográfico. "
                            "A diferença média compara separadamente gênero, idade e escolaridade; "
                            "não representa cruzamento individual, perda histórica ou previsão de votos em 2028. "
                            "Os cards laterais continuam mostrando os indicadores da votação de 2026."
                        )
                    elif scale_type == "uniform":
                        st.caption(
                            "Bairros com votos usam um único tom de azul, sem escala de intensidade; "
                            "bairros sem votos ficam cinza. Passe o cursor para ver os bairros e seus votos."
                        )
                    elif mesh_kind == "setor":
                        scale_label = "logarítmica" if scale_type == "logarithmic" else "linear"
                        st.caption(f"Azul mais escuro indica mais votos; cinza indica nenhum voto. A escala {scale_label} é relativa ao maior valor de Belo Horizonte e, nos setores censitários, ocupa toda a faixa de cores para manter visíveis os setores com votos. O tooltip identifica os bairros do TSE mesmo onde o candidato não recebeu votos; setores sem referência direta usam o bairro territorialmente mais próximo na cidade.")
                    else:
                        scale_label = "logarítmica" if scale_type == "logarithmic" else "linear"
                        st.caption(f"Azul mais escuro indica mais votos; cinza indica nenhum voto. A escala {scale_label} considera também a proporção de bairros com votos em Belo Horizonte. Passe o cursor para ver os bairros e seus votos.")
            except Exception as exc:
                st.warning(f"Não foi possível carregar o mapa de bairros de Belo Horizonte: {exc}")
    with detail_cards_col:
        _render_neighborhood_side_cards(
            selected_bh_neighborhood_df,
            "3106200",
            year=bh_cards_year,
            municipality_votes_df=selected_bh_municipality_df,
            statewide_votes_df=votos_municipio_df,
            total_neighborhoods=bh_mesh_neighborhood_count,
        )
