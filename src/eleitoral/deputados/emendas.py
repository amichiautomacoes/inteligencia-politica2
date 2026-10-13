"""Seção de emendas copiada de deputados_streamlit, com dados do bucket deste app."""
from __future__ import annotations

import html
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st

from eleitoral.common.raio_x_cards import _format_number, _format_percent
from eleitoral.maps.dna_geo_reference import load_geo_reference
from eleitoral.deputados.emendas_map import ACTION_COLORS, parliamentary_map

def _major_section_header(title: str, subtitle: str) -> None:
    subtitle_html = (
        f'<div class="mapa-major-section-subtitle">{subtitle}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="mapa-major-section">
            <div class="mapa-major-section-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )



def _load_geo_reference() -> tuple[dict | None, pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    return load_geo_reference()



def _normalize_municipio_name(value: object) -> str:
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())



def _format_currency(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "R$ 0,00"
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _parliamentary_action_frame(
    votos_df: pd.DataFrame | None,
    emendas_df: pd.DataFrame | None,
) -> pd.DataFrame:
    if votos_df is None or votos_df.empty or emendas_df is None or emendas_df.empty:
        return pd.DataFrame()
    if "qt_votos" not in votos_df.columns:
        return pd.DataFrame()

    geojson_mg, df_tse_ref, df_municipios_ref, df_regioes_ref = _load_geo_reference()
    if geojson_mg is None or df_tse_ref is None or df_municipios_ref is None:
        return pd.DataFrame()

    code_col = next(
        (
            col
            for col in (
                "cd_ibge_municipio",
                "codigo_ibge",
                "CD_MUNICIPIO",
                "cd_municipio",
                "codigo_tse",
                "codigo_municipio_tse",
            )
            if col in votos_df.columns
        ),
        None,
    )
    city_col = "nm_municipio" if "nm_municipio" in votos_df.columns else None
    rank_col = next(
        (
            col
            for col in (
                "rank_municipio",
                "ranking_municipio",
                "posicao_municipio",
                "posicao_candidato_municipio",
                "rank_candidato_municipio",
                "ranking_candidato_municipio",
            )
            if col in votos_df.columns
        ),
        None,
    )
    extra_vote_cols = [rank_col] if rank_col else []

    if code_col == "cd_ibge_municipio" or code_col == "codigo_ibge":
        votos_base = votos_df[[code_col, "qt_votos"] + ([city_col] if city_col else []) + extra_vote_cols].copy()
        votos_base = votos_base.rename(columns={code_col: "codigo_ibge", city_col or code_col: "municipio"})
        votos_base["codigo_ibge"] = votos_base["codigo_ibge"].astype("string")
    elif code_col:
        votos_base = votos_df[[code_col, "qt_votos"] + ([city_col] if city_col else []) + extra_vote_cols].copy()
        votos_base = votos_base.rename(columns={code_col: "codigo_tse", city_col or code_col: "municipio"})
        votos_base["codigo_tse"] = votos_base["codigo_tse"].astype("string")
        votos_base = votos_base.merge(
            df_tse_ref[["codigo_tse", "codigo_ibge", "nome_municipio"]],
            on="codigo_tse",
            how="left",
        )
        votos_base["municipio"] = votos_base["municipio"].fillna(votos_base["nome_municipio"])
    elif city_col:
        votos_base = votos_df[[city_col, "qt_votos"] + extra_vote_cols].copy().rename(columns={city_col: "municipio"})
        votos_base["municipio_norm"] = votos_base["municipio"].map(_normalize_municipio_name)
        votos_base = votos_base.merge(
            df_tse_ref[["codigo_ibge", "nome_municipio", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    else:
        return pd.DataFrame()

    votos_base["qt_votos"] = pd.to_numeric(votos_base["qt_votos"], errors="coerce").fillna(0)
    agg_map = {"qt_votos": "sum", "municipio": "first"}
    if rank_col and rank_col in votos_base.columns:
        votos_base[rank_col] = pd.to_numeric(votos_base[rank_col], errors="coerce")
        agg_map[rank_col] = "min"
    votos_base = (
        votos_base.dropna(subset=["codigo_ibge"])
        .groupby("codigo_ibge", as_index=False)
        .agg(agg_map)
    )

    emenda_value_col = next(
        (
            col
            for col in ("valor_pago_atualizado", "valor_empenhado_ano", "valor_indicado")
            if col in emendas_df.columns
        ),
        None,
    )
    if emenda_value_col is None:
        return pd.DataFrame()

    emendas = emendas_df.copy()
    if "cd_ibge_municipio" in emendas.columns:
        emendas["codigo_ibge"] = emendas["cd_ibge_municipio"].astype("string")
    elif "nm_municipio" in emendas.columns:
        emendas["municipio_norm"] = emendas["nm_municipio"].map(_normalize_municipio_name)
        emendas = emendas.merge(
            df_tse_ref[["codigo_ibge", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    elif "municipio" in emendas.columns:
        emendas["municipio_norm"] = emendas["municipio"].map(_normalize_municipio_name)
        emendas = emendas.merge(
            df_tse_ref[["codigo_ibge", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    else:
        return pd.DataFrame()

    emendas[emenda_value_col] = pd.to_numeric(emendas[emenda_value_col], errors="coerce").fillna(0)
    extra_emenda_cols = [
        col
        for col in (
            "valor_total_emendas_municipio",
            "total_votos_municipio",
            "indice_retorno_parlamentar",
            "classificacao_retorno_parlamentar",
        )
        if col in emendas.columns
    ]
    emendas_agg = {emenda_value_col: "sum", **{col: "first" for col in extra_emenda_cols}}
    emendas_base = (
        emendas.dropna(subset=["codigo_ibge"])
        .groupby("codigo_ibge", as_index=False)
        .agg(emendas_agg)
        .rename(columns={emenda_value_col: "valor_emendas"})
    )

    result = df_municipios_ref.copy()
    result["codigo_ibge"] = result["codigo_ibge"].astype("string")
    result = result.dropna(subset=["codigo_ibge"]).merge(votos_base, on="codigo_ibge", how="left")
    result = result.merge(emendas_base, on="codigo_ibge", how="left")
    result["qt_votos"] = pd.to_numeric(result["qt_votos"], errors="coerce").fillna(0)
    if "total_votos_municipio" in result.columns:
        result["qt_votos"] = (
            pd.to_numeric(result["total_votos_municipio"], errors="coerce")
            .fillna(result["qt_votos"])
            .fillna(0)
        )
    if "valor_total_emendas_municipio" in result.columns:
        result["valor_emendas"] = (
            pd.to_numeric(result["valor_total_emendas_municipio"], errors="coerce")
            .fillna(result["valor_emendas"])
            .fillna(0)
        )
    result["valor_emendas"] = pd.to_numeric(result["valor_emendas"], errors="coerce").fillna(0)
    result["municipio"] = result["municipio"].fillna(result.get("nome"))
    if df_regioes_ref is not None and not df_regioes_ref.empty:
        result = result.merge(
            df_regioes_ref[["codigo_ibge", "mesorregiao_nome", "regiao_imediata_nome"]],
            on="codigo_ibge",
            how="left",
        )
    result["codigo_ibge_str"] = result["codigo_ibge"].astype("string")
    result["municipio_exibicao"] = result["nome"].fillna(result["municipio"]).fillna("Município")
    result["municipio_contexto"] = result["municipio"].fillna(result["municipio_exibicao"]).astype(str)
    result["mesorregiao_exibicao"] = (
        result.get("mesorregiao_nome", pd.Series(index=result.index, dtype="object"))
        .fillna("Mesorregião não informada")
        .astype(str)
    )
    total_votes = float(result["qt_votos"].sum())
    result["pct_votos_total"] = np.where(total_votes > 0, result["qt_votos"] / total_votes, 0.0)
    if "indice_retorno_parlamentar" in result.columns:
        result["indice_retorno"] = pd.to_numeric(result["indice_retorno_parlamentar"], errors="coerce").fillna(0)
    else:
        result["indice_retorno"] = 0.0
    result["indice_retorno"] = pd.to_numeric(result["indice_retorno"], errors="coerce").replace([np.inf, -np.inf], 0).fillna(0)
    if rank_col and rank_col in result.columns:
        result["is_top3_vote"] = pd.to_numeric(result[rank_col], errors="coerce").le(3)
    else:
        top3_codes = set(result.nlargest(3, "qt_votos")["codigo_ibge"].dropna().astype("string"))
        result["is_top3_vote"] = result["codigo_ibge"].astype("string").isin(top3_codes)

    result["categoria_coerencia"] = (
        result.get("classificacao_retorno_parlamentar", pd.Series(index=result.index, dtype="object"))
        .fillna("Sem Expressão")
        .astype(str)
        .str.strip()
    )
    result.loc[result["categoria_coerencia"].eq(""), "categoria_coerencia"] = "Sem Expressão"
    result["categoria_coerencia"] = result["categoria_coerencia"].replace(
        {
            "Sem Expressao": "Sem Expressão",
            "sem expressao": "Sem Expressão",
            "sem expressão": "Sem Expressão",
        }
    )
    no_emendas = result["valor_emendas"].le(0)
    result.loc[no_emendas & result["qt_votos"].gt(0), "categoria_coerencia"] = "Votos sem emendas"
    result.loc[no_emendas & result["qt_votos"].le(0), "categoria_coerencia"] = "Sem votos nem emendas"
    result["motivo_cor"] = result["categoria_coerencia"].map(
        {
            "Reduto Atendido": "Classificação de retorno parlamentar informada no parquet.",
            "Investimento": "Classificação de retorno parlamentar informada no parquet.",
            "Reduto Desassistido": "Classificação de retorno parlamentar informada no parquet.",
            "Sem Expressão": "Classificação de retorno parlamentar informada no parquet.",
            "Votos sem emendas": "O candidato recebeu votos neste município, mas não destinou emendas.",
            "Sem votos nem emendas": "O candidato não recebeu votos nem destinou emendas neste município.",
        }
    ).fillna("Classificação de retorno parlamentar informada no parquet.")
    return result




def _parliamentary_action_kpis(action_df: pd.DataFrame) -> dict[str, str]:
    if action_df.empty:
        return {
            "reciprocidade": "0,0%",
            "reciprocidade_caption": "Sem dados de emendas para calcular",
            "beneficiado": "Sem dados",
            "beneficiado_caption": "R$ 0,00 | 0 votos",
            "media_retorno": "R$ 0,00",
            "media_retorno_caption": "Média estadual por voto recebido",
        }

    total_emendas = float(pd.to_numeric(action_df["valor_emendas"], errors="coerce").fillna(0).sum())
    top3_emendas = float(
        pd.to_numeric(action_df.loc[action_df["is_top3_vote"], "valor_emendas"], errors="coerce").fillna(0).sum()
    )
    reciprocidade = top3_emendas / total_emendas if total_emendas > 0 else 0.0

    total_votes = float(pd.to_numeric(action_df["qt_votos"], errors="coerce").fillna(0).sum())
    media_retorno = total_emendas / total_votes if total_votes > 0 else 0.0

    beneficiary = action_df.sort_values("valor_emendas", ascending=False).head(1)
    if beneficiary.empty or float(beneficiary["valor_emendas"].iloc[0]) <= 0:
        beneficiado = "Sem emendas"
        beneficiado_caption = "R$ 0,00 | 0 votos"
    else:
        row = beneficiary.iloc[0]
        beneficiado = str(row.get("municipio_exibicao", "Município"))
        beneficiado_caption = (
            f"{_format_currency(float(row.get('valor_emendas', 0) or 0))} | "
            f"{_format_number(float(row.get('qt_votos', 0) or 0))} votos"
        )

    return {
        "reciprocidade": _format_percent(reciprocidade),
        "reciprocidade_caption": "Das emendas foram para municípios Top 3 do candidato",
        "beneficiado": beneficiado,
        "beneficiado_caption": beneficiado_caption,
        "media_retorno": _format_currency(media_retorno),
        "media_retorno_caption": "Valor médio de emendas por voto no estado",
    }


def _render_parliamentary_action_kpis(action_df: pd.DataFrame) -> None:
    kpis = _parliamentary_action_kpis(action_df)
    st.markdown(
        f"""
        <div class="raiox-kpi-grid">
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Taxa de Reciprocidade</div>
                <div class="mapa-kpi-value">{html.escape(kpis["reciprocidade"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["reciprocidade_caption"])}</div>
            </div>
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Maior Beneficiado (R$)</div>
                <div class="mapa-kpi-value">{html.escape(kpis["beneficiado"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["beneficiado_caption"])}</div>
            </div>
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Média R$/Voto</div>
                <div class="mapa-kpi-value">{html.escape(kpis["media_retorno"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["media_retorno_caption"])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


PARLIAMENTARY_LEGEND_COPY = {
    "Reduto Atendido": {
        "title": "🔵 BASE PRIORIZADA 🎯",
        "description": (
            "Municípios onde houve votação relevante e também emendas. "
            "É a base eleitoral que recebeu retorno parlamentar."
        ),
    },
    "Investimento": {
        "title": "🟢 APOSTA POLÍTICA 🚀",
        "description": (
            "Municípios que receberam emendas mesmo sem serem grandes redutos. "
            "Indicam aposta política ou construção de presença."
        ),
    },
    "Reduto Desassistido": {
        "title": "🟡 BASE EM RISCO ⚠️",
        "description": (
            "Municípios com votos importantes, mas pouca ou nenhuma emenda. "
            "A base pode se sentir pouco atendida."
        ),
    },
    "Sem Expressão": {
        "title": "🟠 PRESENÇA PONTUAL 🔍",
        "description": (
            "Municípios com baixa expressão eleitoral e atuação parlamentar pontual. "
            "Não são prioridade evidente nesse cruzamento."
        ),
    },
    "Votos sem emendas": {
        "title": "🔘 VOTAÇÃO ORGÂNICA 🤝",
        "description": (
            "Municípios onde houve votos para o candidato, mas nenhuma emenda registrada. "
            "A votação apareceu sem retorno parlamentar."
        ),
    },
    "Sem votos nem emendas": {
        "title": "⚪ TERRITÓRIO NEUTRO 🏳️",
        "description": (
            "Municípios sem votos e sem emendas neste recorte. "
            "Não há presença eleitoral nem atuação registrada."
        ),
    },
}


def _render_parliamentary_legend_cards(action_df: pd.DataFrame) -> None:
    if action_df.empty or "categoria_coerencia" not in action_df.columns:
        st.info("Legenda parlamentar indisponível.")
        return

    total_votes = float(pd.to_numeric(action_df.get("qt_votos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    cards = []
    for category, copy in PARLIAMENTARY_LEGEND_COPY.items():
        color = ACTION_COLORS.get(category, "#64748B")
        rows = action_df[action_df["categoria_coerencia"].astype(str).eq(category)].copy()
        cities = int(len(rows))
        votes = float(pd.to_numeric(rows.get("qt_votos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        vote_share = votes / total_votes if total_votes > 0 else 0.0
        cards.append(
            f"""
            <div class="raiox-parliament-card" style="
                --parliament-color: {html.escape(color)};
                background:
                    radial-gradient(circle at 0% 0%, {html.escape(color)}45 0%, {html.escape(color)}1f 42%, transparent 72%),
                    linear-gradient(145deg, {html.escape(color)}28 0%, rgba(7,24,54,.76) 58%, {html.escape(color)}0f 100%);
                border-color: {html.escape(color)}66;
            ">
                <div class="raiox-parliament-card-title">{html.escape(copy["title"])}</div>
                <div class="raiox-parliament-card-metric">
                    {_format_number(cities)} cidades
                    <span>{_format_percent(vote_share)} da votação</span>
                </div>
                <div class="raiox-parliament-card-description">{html.escape(copy["description"])}</div>
            </div>
            """
        )

    st.html(
        """
        <style>
        .raiox-parliament-card-stack {
            display: grid;
            gap: .58rem;
        }
        .raiox-parliament-card {
            min-height: 6rem;
            padding: .68rem .78rem .72rem;
            border: 1px solid;
            border-radius: 16px;
            color: #eaf2ff;
            box-shadow: 0 12px 30px rgba(1, 8, 24, 0.22);
            backdrop-filter: blur(7px);
            -webkit-backdrop-filter: blur(7px);
        }
        .raiox-parliament-card-title {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            padding: .25rem .48rem;
            border: 1px solid color-mix(in srgb, var(--parliament-color), white 25%);
            border-radius: 999px;
            background: color-mix(in srgb, var(--parliament-color), transparent 76%);
            color: #f8fbff;
            font-size: .68rem;
            font-weight: 900;
            line-height: 1.18;
            letter-spacing: .03em;
        }
        .raiox-parliament-card-metric {
            margin-top: .48rem;
            color: #ffffff;
            font-size: 1.06rem;
            font-weight: 900;
            line-height: 1.18;
        }
        .raiox-parliament-card-metric span {
            display: block;
            margin-top: .12rem;
            color: #dbeafe;
            font-size: .82rem;
            font-weight: 750;
        }
        .raiox-parliament-card-description {
            margin-top: .42rem;
            color: #c8d7ef;
            font-size: .74rem;
            line-height: 1.32;
        }
        </style>
        <div class="raiox-parliament-card-stack">
        """ + "".join(cards) + "</div>"
    )


def _parliamentary_map_selection(event: object | None) -> dict[str, str]:
    if event is None:
        return {}
    if hasattr(event, "selection"):
        selection = getattr(event, "selection")
    elif isinstance(event, dict):
        selection = event.get("selection", {})
    else:
        selection = {}
    if isinstance(selection, dict):
        points = selection.get("points", [])
    else:
        points = getattr(selection, "points", [])
    if not points:
        return {}
    point = points[0]
    customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    if customdata is None or len(customdata) < 4:
        return {}
    return {
        "codigo_ibge": str(customdata[3]),
    }


@st.dialog("Emendas destinadas ao município", width="large")
def _parliamentary_emendas_dialog(
    codigo_ibge: str, action_df: pd.DataFrame, emendas_df: pd.DataFrame | None,
) -> None:
    selected = action_df[action_df["codigo_ibge_str"].eq(codigo_ibge)]
    if selected.empty:
        st.info("Município não encontrado no recorte atual.")
        return
    row = selected.iloc[0]
    st.subheader(str(row["municipio_exibicao"]).title())
    st.caption(
        f'{_format_number(float(row["qt_votos"]))} votos · '
        f'{row["categoria_coerencia"]}'
    )
    st.metric("Total de emendas indicado ao município", _format_currency(float(row["valor_emendas"])))
    if emendas_df is None or emendas_df.empty or "cd_ibge_municipio" not in emendas_df.columns:
        st.info("Detalhamento das emendas indisponível.")
        return
    emendas = emendas_df.copy()
    codes = emendas["cd_ibge_municipio"].astype("string")
    emendas = emendas[codes.eq(codigo_ibge)].copy()
    if emendas.empty:
        st.info("Não há emendas registradas para este município.")
        return
    emendas["valor_indicado"] = pd.to_numeric(emendas["valor_indicado"], errors="coerce").fillna(0)
    for col in ("funcao_descricao", "tipo_indicacao"):
        emendas[col] = emendas[col].fillna("Não informado").astype(str).str.strip()
        emendas.loc[emendas[col].eq(""), col] = "Não informado"
    summary = (
        emendas.groupby(["funcao_descricao", "tipo_indicacao"], as_index=False)
        .agg(indicacoes=("valor_indicado", "size"), valor_indicado=("valor_indicado", "sum"))
        .sort_values("valor_indicado", ascending=False)
        .rename(columns={
            "funcao_descricao": "Finalidade", "tipo_indicacao": "Tipo de indicação",
            "indicacoes": "Indicações", "valor_indicado": "Valor indicado",
        })
    )
    st.dataframe(
        summary, hide_index=True, width="stretch",
        column_config={
            "Indicações": st.column_config.NumberColumn(format="%d"),
            "Valor indicado": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    st.caption("Valores indicados; o pagamento pode ser diferente. Finalidade e tipo seguem a classificação do parquet de emendas.")


def _render_parliamentary_action_section(
    votos_df: pd.DataFrame | None,
    emendas_df: pd.DataFrame | None,
) -> None:
    _major_section_header(
        "Mapa da atuação parlamentar de acordo com os votos",
        "Índice de Retorno Parlamentar: valor total de emendas no município dividido pelos votos recebidos.",
    )
    action_df = _parliamentary_action_frame(votos_df, emendas_df)
    parliamentary_map_col, parliamentary_cards_col = st.columns([0.70, 0.30], gap="large")
    with parliamentary_map_col:
        _render_parliamentary_action_kpis(action_df)
        with st.container(border=True, key="parliamentary-map-container"):
            fig = parliamentary_map(action_df)
            if fig is not None:
                revision = st.session_state.get("pagina1_parliamentary_map_revision", 0)
                event = st.plotly_chart(
                    fig, width="stretch", height=720,
                    key=f"pagina1_parliamentary_action_map_{revision}",
                    on_select="rerun", selection_mode="points",
                )
                selection = _parliamentary_map_selection(event)
                if selection:
                    st.session_state["pagina1_parliamentary_map_revision"] = revision + 1
                    _parliamentary_emendas_dialog(selection["codigo_ibge"], action_df, emendas_df)
            else:
                st.info("Mapa parlamentar indisponível.")
    with parliamentary_cards_col:
        _render_parliamentary_legend_cards(action_df)



def render_emendas(votos_df: pd.DataFrame | None, emendas_df: pd.DataFrame | None) -> None:
    """Preserva a seção original e adapta o vínculo municipal dos arquivos atuais."""
    st.html("""<style>
        .st-key-parliamentary-map-container [data-testid="stVerticalBlockBorderWrapper"] {
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
    </style>""")
    if emendas_df is not None and not emendas_df.empty and "cd_ibge_municipio" not in emendas_df:
        _, reference, _, _ = load_geo_reference()
        if reference is not None:
            emendas_df = emendas_df.copy()
            if "cd_municipio" in emendas_df:
                codes = emendas_df["cd_municipio"].astype("string").str.replace(r"\.0$", "", regex=True)
                lookup = reference.drop_duplicates("codigo_tse").set_index("codigo_tse")["codigo_ibge"]
                emendas_df["cd_ibge_municipio"] = codes.map(lookup)
                ibge_codes = set(reference["codigo_ibge"].astype("string"))
                emendas_df["cd_ibge_municipio"] = emendas_df["cd_ibge_municipio"].fillna(codes.where(codes.isin(ibge_codes)))
            else:
                emendas_df["cd_ibge_municipio"] = pd.NA
            name_column = next((col for col in ("nm_municipio", "municipio") if col in emendas_df), None)
            if name_column:
                unique_names = reference.drop_duplicates(["municipio_norm", "codigo_ibge"])
                unique_names = unique_names.loc[~unique_names["municipio_norm"].duplicated(keep=False)]
                lookup = unique_names.set_index("municipio_norm")["codigo_ibge"]
                emendas_df["cd_ibge_municipio"] = emendas_df["cd_ibge_municipio"].fillna(
                    emendas_df[name_column].map(_normalize_municipio_name).map(lookup)
                )
    _render_parliamentary_action_section(votos_df, emendas_df)
