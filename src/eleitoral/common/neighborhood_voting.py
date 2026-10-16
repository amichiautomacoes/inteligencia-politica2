"""Votação intramunicipal de deputados estaduais, copiada de deputados_streamlit."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from eleitoral.common.raio_x_cards import _format_number, _format_percent, _normalized_text, _map_side_card
from eleitoral.maps.dna_geo_reference import load_geo_reference
from eleitoral.maps.territorial_mesh import mesoregion_options, municipality_options, municipality_mesh_map
from eleitoral.common.bh_neighborhood_voting import bh_neighborhood_voting_map
from eleitoral.common.shared_header import major_section_header

def _render_neighborhood_side_cards(df: pd.DataFrame | None, municipality_code: str | None, year: str | None = None, *, reference_df: pd.DataFrame | None = None) -> None:
    card = _map_side_card
    required = {"cd_ibge_municipio", "nm_bairro", "qt_votos"}
    municipality_rows = pd.DataFrame()
    rows = pd.DataFrame()
    if df is not None and municipality_code is not None and required.issubset(df.columns):
        codes = df["cd_ibge_municipio"].astype("string")
        municipality_rows = df.loc[codes.eq(str(municipality_code))].copy()
        rows = municipality_rows[["nm_bairro", "qt_votos"]].copy()
        if "cd_bairro" in municipality_rows:
            rows["cd_bairro"] = municipality_rows["cd_bairro"]
        rows["nm_bairro"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
        rows["qt_votos"] = pd.to_numeric(rows["qt_votos"], errors="coerce").fillna(0)
        rows = rows.loc[rows["nm_bairro"].ne("")]

    municipality_total = pd.to_numeric(
        municipality_rows.get("qt_votos", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0).sum()
    source = reference_df if reference_df is not None else df
    vote_column = f"qt_votos_candidato_bairro_{year}" if year in {"2018", "2022"} else "qt_votos"
    candidate_total = None
    if source is not None and vote_column in source:
        values = pd.to_numeric(source[vote_column], errors="coerce")
        if values.notna().any():
            candidate_total = float(values.sum())
    candidate_share = (
        municipality_total / candidate_total
        if not municipality_rows.empty and candidate_total is not None and candidate_total > 0 else None
    )
    cards = [
        card(
            "Total de votos no Município",
            _format_percent(candidate_share) if candidate_share is not None else "—",
            "",
            f"Total municipal · {_format_number(municipality_total)} votos" if not municipality_rows.empty else "",
            "good" if not municipality_rows.empty else "",
        )
    ]
    if rows.empty:
        cards.extend([
            card("Bairro principal (Top 1)", "—", "Dados de bairros indisponíveis"),
            card("Dependência do bairro principal", "—", "Dados de bairros indisponíveis"),
            card("Penetração por bairros", "—", "Dados de bairros indisponíveis"),
            card("Densidade média por bairro", "—", "Dados de bairros indisponíveis"),
        ])
    else:
        rows["_bairro"] = rows["nm_bairro"].map(_normalized_text)
        if "cd_bairro" in rows:
            rows["_bairro"] = rows["cd_bairro"].astype("string").str.strip()
            rows = rows.loc[rows["_bairro"].notna() & rows["_bairro"].ne("")]
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
            card(
                "Penetração por bairros",
                f"{_format_number(with_votes)} bairros com voto",
                "Total de bairros do município indisponível",
            ),
            card(
                "Densidade média por bairro",
                f"{_format_number(round(total / with_votes))} votos / bairro" if with_votes else "—",
                f"Considerando apenas os {_format_number(with_votes)} bairros com voto" if with_votes else "Sem votos por bairro",
            ),
        ])
    st.markdown('<div class="raiox-map-side-cards">' + "".join(cards) + '</div>', unsafe_allow_html=True)



def _municipal_votes_frame(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if "nivel_territorial" in df.columns:
        municipal = df[
            df["nivel_territorial"].astype(str).str.strip().str.lower() == "municipio"
        ].copy()
        if not municipal.empty:
            return municipal
    return df



def _leading_municipality_selection(df: pd.DataFrame | None) -> tuple[str, str]:
    municipal = _municipal_votes_frame(df)
    required = {"cd_ibge_municipio", "qt_votos"}
    if municipal is None or municipal.empty or not required.issubset(municipal.columns):
        return "", ""

    ranking = municipal.copy()
    ranking["_municipality_code"] = (
        ranking["cd_ibge_municipio"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )
    ranking["qt_votos"] = pd.to_numeric(ranking["qt_votos"], errors="coerce").fillna(0)
    ranking = ranking.loc[ranking["_municipality_code"].notna() & ranking["_municipality_code"].ne("")]
    if ranking.empty:
        return "", ""

    aggregations: dict[str, str] = {"qt_votos": "sum"}
    if "nm_mesorregiao" in ranking.columns:
        aggregations["nm_mesorregiao"] = "first"
    if "nm_municipio" in ranking.columns:
        aggregations["nm_municipio"] = "first"
    ranking = ranking.groupby("_municipality_code", as_index=False).agg(aggregations)
    sort_columns = ["qt_votos"]
    ascending = [False]
    if "nm_municipio" in ranking.columns:
        sort_columns.append("nm_municipio")
        ascending.append(True)
    leader = ranking.sort_values(sort_columns, ascending=ascending).iloc[0]
    mesoregion_value = leader.get("nm_mesorregiao", "")
    mesoregion = "" if pd.isna(mesoregion_value) else str(mesoregion_value).strip()
    return mesoregion, str(leader["_municipality_code"])



def _candidate_widget_suffix() -> str:
    filters = st.session_state.get("deputados_filters", {})
    parts = [filters.get("ano"), filters.get("cargo"), filters.get("nome")]
    normalized = "_".join(_normalized_text(part).replace(" ", "_") for part in parts if part)
    return normalized.casefold() or "padrao"



def render_neighborhood_voting(votos_municipio_df: pd.DataFrame | None, votos_bairro_df: pd.DataFrame | None, *, election_controls=None, election_renderer=None) -> None:
    major_section_header(
        "Votação por Bairros dentro dos municípios",
        "Votos por bairro no município selecionado.",
    )
    st.markdown("""
    <style>
    @media (min-width: 900px) {
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-neighborhood-voting-map) {
            align-items: stretch;
        }
        [data-testid="stColumn"]:has(.st-key-neighborhood-voting-map) > [data-testid="stVerticalBlock"],
        .st-key-neighborhood-voting-map {
            height: 100%;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-neighborhood-voting-map)
        > [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"] {
            height: 100%;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-neighborhood-voting-map)
        > [data-testid="stColumn"]:last-child [data-testid="stElementContainer"],
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-neighborhood-voting-map)
        > [data-testid="stColumn"]:last-child [data-testid="stMarkdownContainer"] {
            height: 100%;
        }
        [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-neighborhood-voting-map)
        .raiox-map-side-cards {
            height: 100%;
            grid-template-rows: repeat(5, minmax(9.25rem, 1fr));
        }
    }
    </style>
    """, unsafe_allow_html=True)
    selected_code = None
    election = "2026"
    cards_df = votos_bairro_df
    detail_map_col, detail_cards_col = st.columns([0.70, 0.30], gap="large")
    with detail_map_col:
        with st.container(border=True, key="neighborhood-voting-map"):
            try:
                if election_controls is not None:
                    election = election_controls(_candidate_widget_suffix())
                mesoregions = mesoregion_options()
                leading_mesorregiao, leading_municipality_code = _leading_municipality_selection(
                    votos_municipio_df
                )
                mesoregion_choices = ["Todas", *mesoregions]
                default_mesorregiao = next(
                    (
                        option
                        for option in mesoregion_choices
                        if _normalized_text(option) == _normalized_text(leading_mesorregiao)
                    ),
                    "Todas",
                )
                candidate_widget_suffix = _candidate_widget_suffix()
                selected_mesorregiao = st.selectbox(
                    "Mesorregião",
                    mesoregion_choices,
                    index=mesoregion_choices.index(default_mesorregiao),
                    key=f"pagina1_malha_mesorregiao_{candidate_widget_suffix}",
                )
                municipality_choices = municipality_options(selected_mesorregiao)
                if not municipality_choices:
                    selected_code = None
                    st.info("Nenhum município disponível para a mesorregião selecionada.")
                else:
                    municipality_codes = [code for code, _ in municipality_choices]
                    default_municipality_index = (
                        municipality_codes.index(leading_municipality_code)
                        if leading_municipality_code in municipality_codes
                        else 0
                    )
                    selected_code = st.selectbox(
                        "Município",
                        municipality_codes,
                        index=default_municipality_index,
                        format_func=dict(municipality_choices).get,
                        key=(
                            f"pagina1_municipio_malha_{candidate_widget_suffix}_"
                            f"{_normalized_text(selected_mesorregiao).replace(' ', '_').casefold()}"
                        ),
                    )
                if selected_code is not None and election != "2026" and election_renderer is not None:
                    cards_df = election_renderer(votos_bairro_df, selected_code, election)
                elif selected_code is not None:
                    mesh_fig, _ = (
                        bh_neighborhood_voting_map(votos_bairro_df)
                        if str(selected_code) == "3106200"
                        else municipality_mesh_map(selected_code, votos_bairro_df, allow_neighborhoods=False, candidate_neighborhood_details=True)
                    )
                    if mesh_fig is None:
                        st.info("Mapa de votos por bairro indisponível para este município.")
                    else:
                        if str(selected_code) == "3106200":
                            st.caption("Bairros e votos do candidato seguem o cadastro do TSE. O código IBGE vincula esses registros à malha oficial; cinza indica dados indisponíveis.")
                            unmatched = (mesh_fig.layout.meta or {}).get("unmatched_rows", 0)
                            if unmatched:
                                st.caption(f"{unmatched} registro(s) do candidato sem correspondência de código na malha oficial não aparecem no mapa.")
                        st.plotly_chart(mesh_fig, width="stretch", height=560, key="pagina1_malha_municipal")
                        mesh_kind = (mesh_fig.layout.meta or {}).get("mesh_kind")
                        scale_type = (mesh_fig.layout.meta or {}).get("scale_type")
                        if scale_type == "uniform":
                            st.caption(
                                "Municípios com menos de 1.000 votos usam um único tom de azul, "
                                "sem escala de intensidade. Passe o cursor para ver os bairros e seus votos."
                            )
                        elif mesh_kind != "setor":
                            scale_label = "logarítmica" if scale_type == "logarithmic" else "linear"
                            st.caption(f"Azul mais escuro indica mais votos. A escala {scale_label} depende somente do volume de votos do município: logarítmica acima de 1.000 votos e linear até 1.000. Passe o cursor para ver os bairros e seus votos.")
            except Exception as exc:
                st.warning(f"Não foi possível carregar o mapa de votos por bairro: {exc}")
    with detail_cards_col:
        _render_neighborhood_side_cards(cards_df, selected_code, election if election in {"2018", "2022"} else "2026" if election_controls else None, reference_df=votos_bairro_df)
