"""Força política local: mapa, cards de classe e diálogo municipal."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from hf_sync import DEFAULT_VISUALIZATION_YEAR
from eleitoral.common.raio_x_cards import _format_number, _format_percent, _normalized_text
from eleitoral.common.shared_header import major_section_header, read_selected_parquet
from eleitoral.maps.choropleth_maps import (
    LOCAL_STRENGTH_COLORS,
    LOCAL_STRENGTH_ICONS,
    LOCAL_STRENGTH_LABELS,
    LOCAL_STRENGTH_LEGEND,
    local_political_strength_map,
    local_political_strength_municipality_map,
)
from eleitoral.maps.dna_geo_reference import load_geo_reference


LOCAL_STRENGTH_SELECTION_KEY = "pagina1_forca_local_classe_selecionada"
LOCAL_STRENGTH_MAP_REVISION_KEY = "pagina1_forca_local_mapa_revisao"


def _render_local_politics_cards(
    summaries: list[dict[str, object]],
    selected_class: str | None,
) -> None:
    card_copy = {
        "Máquina eficiente": (
            "Apoio local forte e votação acima da média estadual.",
            "Manter e fortalecer",
        ),
        "Traição ou máquina inoperante": (
            "Há aliados locais, mas a votação ficou abaixo da média estadual.",
            "Revisar articulação",
        ),
        "Voto orgânico / opinião": (
            "Boa votação mesmo sem uma estrutura política local forte.",
            "Construir novas alianças",
        ),
        "Sem penetração": (
            "Pouco apoio local e votação abaixo da média estadual.",
            "Priorizar com critério",
        ),
    }
    if not summaries:
        st.info("Indicadores de força política local indisponíveis.")
        return

    style_rules = []
    for index, summary in enumerate(summaries):
        classification = str(summary["classification"])
        color = LOCAL_STRENGTH_COLORS[classification]
        is_selected = classification == selected_class
        selected_shadow = (
            f"0 0 0 2px {color}, 0 14px 32px rgba(1,8,24,.34)"
            if is_selected else "0 12px 30px rgba(1,8,24,.22)"
        )
        card_background = (
            f"radial-gradient(circle at 0% 0%, {color}52 0%, {color}26 42%, transparent 72%), "
            f"linear-gradient(145deg, {color}30 0%, rgba(7,24,54,.76) 58%, {color}12 100%)"
            if is_selected
            else (
                f"radial-gradient(circle at 0% 0%, {color}38 0%, {color}18 42%, transparent 72%), "
                f"linear-gradient(145deg, {color}24 0%, rgba(7,24,54,.72) 58%, {color}0d 100%)"
            )
        )
        wrapper_margin = "0" if index == len(summaries) - 1 else "0 0 .55rem 0"
        style_rules.append(f"""
        .st-key-pagina1_forca_local_card_{index} {{
            margin: {wrapper_margin};
        }}
        .st-key-pagina1_forca_local_card_{index} button {{
            min-height: 10.65rem;
            height: auto;
            align-items: flex-start;
            justify-content: flex-start;
            padding: .82rem .95rem .86rem;
            border: 1px solid {color}66;
            border-radius: 16px;
            background: {card_background};
            box-shadow: {selected_shadow};
            color: #eaf2ff;
            text-align: left;
            backdrop-filter: blur(7px);
            -webkit-backdrop-filter: blur(7px);
        }}
        .st-key-pagina1_forca_local_card_{index} button:hover {{
            border-color: {color};
            background:
                radial-gradient(circle at 0% 0%, {color}52 0%, {color}28 44%, transparent 74%),
                linear-gradient(145deg, {color}30 0%, rgba(7,24,54,.78) 58%, {color}14 100%);
            color: #ffffff;
        }}
        .st-key-pagina1_forca_local_card_{index} button p {{
            white-space: pre-line;
            width: 100%;
            margin: 0;
            text-align: left;
            line-height: 1.28;
        }}
        .st-key-pagina1_forca_local_card_{index} button p br {{
            display: block;
            content: "";
            margin-top: 0.42rem;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:first-of-type {{
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            padding: 0.28rem 0.52rem;
            border: 1px solid {color}99;
            border-radius: 999px;
            background: {color}2b;
            color: #f8fbff;
            font-size: 0.72rem;
            font-weight: 900;
            line-height: 1.2;
            letter-spacing: 0.035em;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(2),
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(3) {{
            color: #ffffff;
            font-size: 1.12rem;
            font-weight: 900;
            line-height: 1.08;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(4) {{
            color: #b7c7e6;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .st-key-pagina1_forca_local_card_{index} button p em {{
            color: #dbeafe;
            font-style: normal;
            font-weight: 750;
        }}
        .st-key-pagina1_forca_local_card_{index} button p code {{
            display: inline-block;
            max-width: 100%;
            padding: 0.34rem 0.56rem;
            border: 1px solid {color}73;
            border-radius: 999px;
            background: {color}24;
            color: #f8fbff;
            font-family: inherit;
            font-size: 0.72rem;
            font-weight: 800;
            line-height: 1.25;
            white-space: normal;
        }}
        """)
    st.html("<style>" + "".join(style_rules) + "</style>")

    for index, summary in enumerate(summaries):
        classification = str(summary["classification"])
        title = LOCAL_STRENGTH_LABELS[classification]
        icon = LOCAL_STRENGTH_ICONS[classification]
        description, action = card_copy[classification]
        municipalities = int(summary["municipalities"])
        vote_share = float(summary["vote_share"])
        leader = str(summary["leader"])
        leader_votes = float(summary["leader_votes"])
        selected_suffix = " · EXIBINDO" if classification == selected_class else ""
        cities_label = "Cidade" if municipalities == 1 else "Cidades"
        label = (
            f"**{icon} {title.upper()}{selected_suffix}**  \n"
            f"**{_format_number(municipalities)} {cities_label}** | "
            f"**{_format_percent(vote_share)} da sua votação**  \n"
            f"**Cidade-chave:** {leader} *({_format_number(leader_votes)} votos)*  \n"
            f"`Estratégia · {action}`"
        )
        if st.button(
            label,
            key=f"pagina1_forca_local_card_{index}",
            use_container_width=True,
            help=description,
        ):
            st.session_state[LOCAL_STRENGTH_SELECTION_KEY] = (
                None if classification == selected_class else classification
            )
            st.rerun()



def _render_local_strength_map_legend(statewide_market_share: float | None) -> None:
    legend_items = [
        (
            "Máquina eficiente",
            "🟢 Prefeito/vereadores entregaram votos",
        ),
        (
            "Traição ou máquina inoperante",
            "🔴 Prefeito/vereadores não entregaram votos",
        ),
        (
            "Voto orgânico / opinião",
            "🔵 Votação própria sem prefeito/vereadores",
        ),
        (
            "Sem penetração",
            "⚪ Sem prefeito/vereadores e sem votos",
        ),
    ]
    items_html = "".join(
        f"""
        <div class="raiox-local-map-legend-item" style="--local-color: {html.escape(LOCAL_STRENGTH_COLORS[classification])};">
            <span>{html.escape(copy)}</span>
        </div>
        """
        for classification, copy in legend_items
    )
    st.html(
        f"""
        <style>
        .st-key-pagina1_forca_local_map_card [data-testid="stVerticalBlockBorderWrapper"] {{
            min-height: 50rem;
            padding: 0.92rem 1rem 1rem !important;
        }}
        .raiox-local-map-legend {{
            margin: 0 0 0.6rem;
            padding: 0.12rem 0 0.78rem;
            border-bottom: 1px solid rgba(177, 211, 255, 0.16);
        }}
        .raiox-local-map-legend-title {{
            display: none;
        }}
        .raiox-local-map-legend-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.65rem;
            margin-top: 0;
        }}
        .raiox-local-map-legend-item {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 4.5rem;
            padding: 0.8rem 0.9rem;
            border: 2px solid color-mix(in srgb, var(--local-color), transparent 16%);
            border-radius: 18px;
            background: color-mix(in srgb, var(--local-color), transparent 72%);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
            color: #f8fbff;
            font-size: 1rem;
            font-weight: 850;
            line-height: 1.4;
            letter-spacing: 0;
            text-align: center;
        }}
        @media (max-width: 900px) {{
            .st-key-pagina1_forca_local_map_card [data-testid="stVerticalBlockBorderWrapper"] {{
                min-height: 0;
            }}
            .raiox-local-map-legend-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
        @media (max-width: 560px) {{
            .raiox-local-map-legend-grid {{
                grid-template-columns: 1fr;
            }}
            .raiox-local-map-legend-item {{
                border-radius: 14px;
            }}
        }}
        </style>
        <div class="raiox-local-map-legend">
            <div class="raiox-local-map-legend-grid">
                {items_html}
            </div>
        </div>
        """
    )



def _local_politics_map_selection(event: object | None) -> dict[str, str]:
    if event is None:
        return {}
    if hasattr(event, "selection"):
        selection = getattr(event, "selection")
    elif isinstance(event, dict):
        selection = event.get("selection", {})
    else:
        selection = {}
    points = (
        selection.get("points", [])
        if isinstance(selection, dict)
        else getattr(selection, "points", [])
    )
    if not points:
        return {}

    point = points[0]
    customdata = (
        point.get("customdata")
        if isinstance(point, dict)
        else getattr(point, "customdata", None)
    )
    customdata = list(customdata) if customdata is not None else []
    location = (
        point.get("location")
        if isinstance(point, dict)
        else getattr(point, "location", None)
    )
    code = str(location or (customdata[5] if len(customdata) > 5 else "")).strip()
    municipality = str(customdata[6] if len(customdata) > 6 else "").strip()
    if not municipality:
        hovertext = (
            point.get("hovertext")
            if isinstance(point, dict)
            else getattr(point, "hovertext", None)
        )
        municipality = str(hovertext or "").strip()
    if not municipality and code:
        _, _, municipalities, _ = load_geo_reference()
        if municipalities is not None and not municipalities.empty:
            match = municipalities[
                municipalities["codigo_ibge"].astype("string").eq(code)
            ]
            if not match.empty:
                municipality = str(match.iloc[0]["nome"])
    classification = str(customdata[0] if customdata else "").strip()
    if not code or not municipality or classification not in LOCAL_STRENGTH_COLORS:
        return {}
    return {
        "codigo_ibge": code,
        "municipio": municipality,
        "classificacao": classification,
    }



def _format_percentage_points(value: object, digits: int = 1) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "—"
    return f"{float(numeric):.{digits}f}%".replace(".", ",")



def _format_score(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "—"
    return f"{float(numeric):.1f}/100".replace(".", ",")



def _local_political_link_label(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    labels = {
        "mesmo_partido": "Mesmo partido",
        "federacao": "Federação partidária",
        "partido_aliado": "Partido aliado",
        "aliado": "Aliado",
        "sem_vinculo": "Sem vínculo partidário",
    }
    return labels.get(normalized, normalized.replace("_", " ").title() or "Não informado")



@st.dialog("Força política local", width="large")
def _local_politics_municipality_dialog(
    selection: dict[str, str],
    capital_local_df: pd.DataFrame | None,
    votes_df: pd.DataFrame | None,
    elected_df: pd.DataFrame | None,
    statewide_market_share: float | None,
) -> None:
    municipality = selection["municipio"]
    municipality_key = _normalized_text(municipality)
    classification = selection["classificacao"]
    code = selection["codigo_ibge"]
    color = LOCAL_STRENGTH_COLORS[classification]
    icon = LOCAL_STRENGTH_ICONS[classification]
    reading, criteria = LOCAL_STRENGTH_LEGEND[classification]

    capital_rows = pd.DataFrame()
    if (
        capital_local_df is not None
        and not capital_local_df.empty
        and "nm_municipio" in capital_local_df.columns
    ):
        capital_rows = capital_local_df[
            capital_local_df["nm_municipio"]
            .map(_normalized_text)
            .eq(municipality_key)
        ].copy()
    if capital_rows.empty:
        st.subheader(municipality.title())
        st.info("Os detalhes de força local deste município não estão disponíveis.")
        return
    capital = capital_rows.iloc[0]

    municipal_votes = pd.DataFrame()
    if votes_df is not None and not votes_df.empty and "nm_municipio" in votes_df.columns:
        municipal_votes = votes_df.copy()
        if "nivel_territorial" in municipal_votes.columns:
            level = municipal_votes["nivel_territorial"].astype(str).str.casefold()
            if level.eq("municipio").any():
                municipal_votes = municipal_votes[level.eq("municipio")].copy()
        municipal_votes = municipal_votes[
            municipal_votes["nm_municipio"]
            .map(_normalized_text)
            .eq(municipality_key)
        ]

    votes = pd.to_numeric(
        municipal_votes.get("qt_votos", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0).sum()
    if votes <= 0:
        selected_year = str(
            st.session_state.get("deputados_filters", {}).get("ano")
            or DEFAULT_VISUALIZATION_YEAR
        )
        votes = pd.to_numeric(
            pd.Series([capital.get(f"qt_votos_candidato_{selected_year}")]),
            errors="coerce",
        ).fillna(0).iloc[0]
    market_share_values = pd.to_numeric(
        municipal_votes.get("pct_market_share", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()
    market_share = (
        float(market_share_values.iloc[0])
        if not market_share_values.empty
        else None
    )

    strategic_reading = {
        "Máquina eficiente": (
            "A estrutura política local é forte e o desempenho eleitoral ficou "
            "acima da referência estadual. Aqui, o apoio se converteu em voto."
        ),
        "Traição ou máquina inoperante": (
            "Existe estrutura política local, mas o desempenho ficou abaixo da "
            "referência estadual. Vale revisar a entrega e o engajamento dos aliados."
        ),
        "Voto orgânico / opinião": (
            "O município entregou votação acima da referência mesmo sem uma "
            "estrutura local forte. Há espaço para transformar apoio popular em alianças."
        ),
        "Sem penetração": (
            "A estrutura local e o desempenho eleitoral estão abaixo dos cortes. "
            "É um território para priorizar somente com objetivo e estratégia claros."
        ),
    }

    st.markdown(f"## {html.escape(municipality.title())}")
    st.markdown(
        f"""
        <div style="
            display:inline-flex;align-items:center;gap:.55rem;padding:.45rem .75rem;
            margin:.05rem 0 .8rem;border:1px solid {color};border-radius:999px;
            background:rgba(8,28,64,.72);color:#f8fbff;font-weight:800;">
            <span style="width:.72rem;height:.72rem;border-radius:50%;background:{color};"></span>
            {icon} {html.escape(reading)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("Votos no município", _format_number(votes))
    metric_columns[1].metric(
        "Market share local",
        _format_percentage_points(market_share, 2),
    )
    metric_columns[2].metric(
        "Referência estadual",
        _format_percentage_points(statewide_market_share, 2),
    )
    metric_columns[3].metric(
        "Capital político local",
        _format_score(capital.get("capital_local_0a100")),
    )
    st.info(strategic_reading[classification])
    st.caption(f"Critério da cor: {criteria}.")

    map_column, composition_column = st.columns([0.43, 0.57], gap="large")
    with map_column:
        st.markdown("#### Mapa do município")
        municipality_fig = local_political_strength_municipality_map(
            code,
            municipality,
            classification,
        )
        if municipality_fig is not None:
            st.plotly_chart(
                municipality_fig,
                width="stretch",
                height=330,
                key=f"pagina1_forca_local_detalhe_mapa_{code}",
                config={"displayModeBar": False},
            )
        else:
            st.info("Malha municipal indisponível.")

        mayor_party = str(capital.get("sg_partido_prefeito_2024") or "Não informado")
        mayor_link = _local_political_link_label(capital.get("vinculo_prefeito"))
        council_total = int(
            pd.to_numeric(
                pd.Series([capital.get("qt_vereadores_camara")]),
                errors="coerce",
            ).fillna(0).iloc[0]
        )
        council_allies = int(
            pd.to_numeric(
                pd.Series([capital.get("qt_vereadores_aliados")]),
                errors="coerce",
            ).fillna(0).iloc[0]
        )
        allied_parties = str(capital.get("partidos_aliados") or "Não informado")
        base_year = str(capital.get("ano_base_eleitos") or "Não informado")
        data_status = str(capital.get("situacao_dados") or "Não informado")
        detail_cards = [
            (
                "Prefeitura",
                f"{mayor_party} · {mayor_link}",
                f"Contribuição para a nota: {_format_score(capital.get('pontos_prefeito'))}",
            ),
            (
                "Câmara municipal",
                f"{council_allies} aliados em {council_total} vereadores",
                (
                    f"{_format_percentage_points(capital.get('pct_vereadores_aliados_camara'))} "
                    f"da Câmara · contribuição: {_format_score(capital.get('pontos_camara'))}"
                ),
            ),
            (
                "Partidos considerados aliados",
                allied_parties,
                (
                    "Capital apenas do mesmo partido: "
                    f"{_format_score(capital.get('capital_local_mesmo_partido_0a100'))}"
                ),
            ),
            (
                "Base dos dados",
                f"Eleitos em {base_year}",
                (
                    f"Faixa {str(capital.get('faixa_capital_local') or 'não informada').title()} "
                    f"· situação {data_status.replace('_', ' ')}"
                ),
            ),
        ]
        cards_html = "".join(
            (
                '<div style="padding:.75rem .85rem;border:1px solid rgba(177,211,255,.24);'
                'border-radius:12px;background:rgba(8,28,64,.5);margin:.55rem 0;">'
                f'<div style="color:#93c5fd;font-size:.72rem;font-weight:850;'
                f'text-transform:uppercase;">{html.escape(label)}</div>'
                f'<div style="color:#f8fbff;font-weight:800;margin-top:.2rem;">'
                f'{html.escape(value)}</div>'
                f'<div style="color:#b7c7e6;font-size:.78rem;margin-top:.15rem;">'
                f'{html.escape(caption)}</div></div>'
            )
            for label, value, caption in detail_cards
        )
        st.markdown(cards_html, unsafe_allow_html=True)

    with composition_column:
        st.markdown("#### Prefeito e vereadores")
        local_elected = pd.DataFrame()
        if elected_df is not None and not elected_df.empty:
            municipality_code = str(capital.get("cd_municipio") or "").strip()
            if municipality_code and "cd_municipio" in elected_df.columns:
                local_elected = elected_df[
                    elected_df["cd_municipio"].astype("string").str.strip().eq(
                        municipality_code
                    )
                ].copy()
            if local_elected.empty and "nm_municipio" in elected_df.columns:
                local_elected = elected_df[
                    elected_df["nm_municipio"]
                    .map(_normalized_text)
                    .eq(municipality_key)
                ].copy()

        if local_elected.empty:
            st.info("A composição nominal deste município não está disponível.")
        else:
            for column in (
                "cargo_eleito",
                "nm_eleito",
                "sg_partido_eleito",
                "vinculo_politico",
                "afinidade_eleito_0a100",
            ):
                if column not in local_elected.columns:
                    local_elected[column] = None
            local_elected["_cargo_ordem"] = (
                local_elected["cargo_eleito"]
                .astype(str)
                .str.casefold()
                .map(lambda value: 0 if "prefeit" in value else 1)
            )
            local_elected["afinidade_eleito_0a100"] = pd.to_numeric(
                local_elected["afinidade_eleito_0a100"],
                errors="coerce",
            )
            local_elected = local_elected.sort_values(
                ["_cargo_ordem", "afinidade_eleito_0a100", "nm_eleito"],
                ascending=[True, False, True],
            )
            composition = pd.DataFrame(
                {
                    "Cargo": local_elected["cargo_eleito"].map(
                        lambda value: (
                            "Prefeito"
                            if "prefeit" in str(value).casefold()
                            else "Vereador"
                        )
                    ),
                    "Nome": local_elected["nm_eleito"].fillna("Não informado").map(
                        lambda value: str(value).title()
                    ),
                    "Partido": local_elected["sg_partido_eleito"].fillna("—"),
                    "Vínculo": local_elected["vinculo_politico"].map(
                        _local_political_link_label
                    ),
                    "Afinidade": local_elected["afinidade_eleito_0a100"],
                }
            )
            mayor_count = int(composition["Cargo"].eq("Prefeito").sum())
            council_count = int(composition["Cargo"].eq("Vereador").sum())
            st.caption(
                f"{mayor_count} prefeito · {council_count} vereadores · "
                f"base eleitoral municipal de {base_year}"
            )
            st.dataframe(
                composition,
                hide_index=True,
                width="stretch",
                height=590,
                column_config={
                    "Cargo": st.column_config.TextColumn(width="small"),
                    "Nome": st.column_config.TextColumn(width="medium"),
                    "Partido": st.column_config.TextColumn(width="small"),
                    "Vínculo": st.column_config.TextColumn(width="medium"),
                    "Afinidade": st.column_config.NumberColumn(
                        "Afinidade",
                        help="Afinidade política e eleitoral do eleito com o candidato, de 0 a 100.",
                        format="%.1f",
                    ),
                },
            )



def render_local_political_strength(votos_municipio_df: pd.DataFrame | None) -> None:
    major_section_header(
        "Força da política local",
        "Veja se vereadores e prefeitos das cidades foram decisivos na sua votação",
    )
    capital_local_df = read_selected_parquet("capital_local")
    local_elected_df = read_selected_parquet("afinidade_eleitos")
    selected_local_strength_class = st.session_state.get(LOCAL_STRENGTH_SELECTION_KEY)
    local_politics_fig, statewide_market_share, local_politics_summaries = local_political_strength_map(
        capital_local_df,
        votos_municipio_df,
        selected_local_strength_class,
    )
    local_map_col, local_cards_col = st.columns([0.70, 0.30], gap="large")
    with local_map_col:
        with st.container(border=True, key="pagina1_forca_local_map_card"):
            if local_politics_fig is None:
                st.info("Mapa de força política local indisponível.")
            else:
                _render_local_strength_map_legend(statewide_market_share)
                local_map_revision = st.session_state.get(
                    LOCAL_STRENGTH_MAP_REVISION_KEY,
                    0,
                )
                local_map_event = st.plotly_chart(
                    local_politics_fig,
                    width="stretch",
                    height=682,
                    key=f"pagina1_forca_politica_mapa_municipal_{local_map_revision}",
                    config={"displayModeBar": False},
                    on_select="rerun",
                    selection_mode="points",
                )
                local_map_selection = _local_politics_map_selection(local_map_event)
                if local_map_selection:
                    st.session_state[LOCAL_STRENGTH_MAP_REVISION_KEY] = (
                        local_map_revision + 1
                    )
                    _local_politics_municipality_dialog(
                        local_map_selection,
                        capital_local_df,
                        votos_municipio_df,
                        local_elected_df,
                        statewide_market_share,
                    )
    with local_cards_col:
        _render_local_politics_cards(
            local_politics_summaries,
            selected_local_strength_class,
        )
