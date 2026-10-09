from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

from hf_sync import file_by_kind, load_env, load_parquet
from eleitoral.maps.dna_geo_reference import load_geo_reference
from eleitoral.maps.choropleth_maps import categorical_choropleth
from eleitoral.common.shared_header import selected_files


CLASS_COLORS = {
    "VERDE": "#22c55e",
    "AZUL": "#3b82f6",
    "AMARELO": "#facc15",
    "CINZA": "#94a3b8",
}


def _read(kind: str) -> pd.DataFrame | None:
    file_name = file_by_kind(selected_files(), kind)
    if not file_name:
        return None
    try:
        return load_parquet(file_name, load_env().get("HF_TOKEN"))
    except Exception as exc:
        st.warning(f"Não consegui ler `{kind}.parquet`: {exc}")
        return None


def _canonical(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _area_codes(values: pd.Series) -> pd.Series:
    return values.astype("string")


def _municipality_codes(values: pd.Series) -> pd.Series:
    digits = _area_codes(values).str[:7]
    return digits.where(digits.str.len().eq(7))


def _census_area_profiles(
    gender: pd.DataFrame | None,
    age: pd.DataFrame | None,
    schooling: pd.DataFrame | None,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for dimension, frame, prefix, excluded in (
        ("genero", gender, "populacao_genero_", {"nao_informado"}),
        ("idade", age, "populacao_idade_", {"invalido"}),
    ):
        if frame is None or frame.empty or "cd_area_ponderada" not in frame:
            continue
        areas = _area_codes(frame["cd_area_ponderada"])
        total_col = "populacao_total_ibge"
        total = pd.to_numeric(frame.get(total_col, pd.Series(0, index=frame.index)), errors="coerce").fillna(0)
        category_columns = [column for column in frame if column.startswith(prefix)]
        counts = []
        for column in category_columns:
            category = column.removeprefix(prefix)
            if category in excluded:
                continue
            counts.append(pd.DataFrame({
                "area": areas,
                "dimensao": dimension,
                "categoria": category.replace("_", " "),
                "contagem": pd.to_numeric(frame[column], errors="coerce").fillna(0),
                "populacao_total": total,
            }))
        if counts:
            local = pd.concat(counts, ignore_index=True)
            local = local.groupby(["area", "dimensao", "categoria"], as_index=False).agg(
                contagem=("contagem", "sum"), populacao_total=("populacao_total", "max")
            )
            local["pct_populacao_categoria"] = np.where(
                local["populacao_total"].gt(0), local["contagem"] / local["populacao_total"] * 100, np.nan
            )
            rows.append(local[["area", "dimensao", "categoria", "pct_populacao_categoria", "populacao_total"]])

    if schooling is not None and not schooling.empty and {"cd_area_ponderada", "categoria", "pct_populacao_categoria"}.issubset(schooling.columns):
        education = schooling.copy()
        if "indicador" in education:
            education = education[education["indicador"].map(_canonical).eq("nivel instrucao")]
        if "faixa_etaria" in education:
            education = education[education["faixa_etaria"].map(_canonical).eq("25 anos ou mais")]
        education["area"] = _area_codes(education["cd_area_ponderada"])
        education["categoria"] = education["categoria"].astype(str).str.replace("_", " ", regex=False)
        education["dimensao"] = "escolaridade"
        education["pct_populacao_categoria"] = pd.to_numeric(education["pct_populacao_categoria"], errors="coerce")

        age_totals = None
        if age is not None and not age.empty and "cd_area_ponderada" in age:
            age_columns = [
                "populacao_idade_25_a_34_anos",
                "populacao_idade_35_a_44_anos",
                "populacao_idade_45_a_59_anos",
                "populacao_idade_60_anos_ou_mais",
            ]
            available = [column for column in age_columns if column in age]
            if available:
                age_totals = age[["cd_area_ponderada", *available]].copy()
                age_totals["area"] = _area_codes(age_totals["cd_area_ponderada"])
                age_totals["populacao_total"] = age_totals[available].apply(
                    pd.to_numeric, errors="coerce"
                ).fillna(0).sum(axis=1)
                age_totals = age_totals.groupby("area", as_index=False)["populacao_total"].sum()
        if age_totals is not None:
            education = education.merge(age_totals, on="area", how="left")
        else:
            education["populacao_total"] = np.nan
        rows.append(education[["area", "dimensao", "categoria", "pct_populacao_categoria", "populacao_total"]])

    if not rows:
        return pd.DataFrame(columns=["area", "dimensao", "categoria_key", "pct_populacao_categoria", "populacao_total"])
    result = pd.concat(rows, ignore_index=True)
    result["categoria_key"] = result["categoria"].map(_canonical).str.replace(" ", "_", regex=False)
    result["codigo_ibge"] = _municipality_codes(result["area"])
    return result.dropna(subset=["codigo_ibge", "pct_populacao_categoria"])


def _potential_profiles(potential: pd.DataFrame, selected_profile: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if potential is None or potential.empty:
        return pd.DataFrame(), pd.DataFrame()
    data = potential.copy()
    if selected_profile == "ELEITOR IDEAL":
        data = data[data["tipo_icp"].astype(str).str.strip().eq("icp_geral")]
        data["profile_key"] = "geral"
    else:
        data = data[
            data["tipo_icp"].astype(str).str.strip().eq("icp_cluster")
            & data["cluster_strategy_label"].fillna("").astype(str).str.strip().eq(selected_profile)
        ]
        data["profile_key"] = data["perfil_eleitor"].astype(str)
    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    data["area"] = _area_codes(data["cd_area_ponderada"])
    data["dimensao"] = data["dimensao"].astype(str).str.strip().str.casefold()
    data["categoria_key"] = data["categoria_icp"].astype(str).map(_canonical).str.replace(" ", "_", regex=False)
    data["pct_icp_categoria"] = pd.to_numeric(data["pct_icp_categoria"], errors="coerce")
    data["diferenca_pontos_percentuais"] = pd.to_numeric(data["diferenca_pontos_percentuais"], errors="coerce")
    data["populacao_total"] = pd.to_numeric(data["populacao_total"], errors="coerce")
    data["votos_candidato"] = pd.to_numeric(data["votos_candidato"], errors="coerce").fillna(0)
    data["qt_votos_territorio"] = pd.to_numeric(data["qt_votos_territorio"], errors="coerce").fillna(0)

    profile_weights = data.drop_duplicates(["area", "profile_key", "dimensao"])
    profile_weights = profile_weights.groupby(["profile_key", "dimensao"], as_index=False)["votos_candidato"].sum()
    denominator = profile_weights.groupby("dimensao")["votos_candidato"].transform("sum")
    profile_weights["peso_perfil"] = np.where(
        denominator.gt(0), profile_weights["votos_candidato"] / denominator,
        1.0 / profile_weights.groupby("dimensao")["profile_key"].transform("count"),
    )
    profiles = data.groupby(["profile_key", "dimensao", "categoria_key"], as_index=False).agg(
        pct_icp_categoria=("pct_icp_categoria", "mean"),
    ).merge(profile_weights[["profile_key", "dimensao", "peso_perfil"]], on=["profile_key", "dimensao"], how="left")

    direct = data[[
        "area", "profile_key", "dimensao", "categoria_key", "diferenca_pontos_percentuais", "populacao_total"
    ]].dropna(subset=["area", "diferenca_pontos_percentuais"])
    direct = direct.groupby(["area", "profile_key", "dimensao", "categoria_key"], as_index=False).agg(
        diferenca_precalculada=("diferenca_pontos_percentuais", "mean"),
        populacao_total_precalculada=("populacao_total", "mean"),
    )
    return profiles, direct


def _expansion_city_frame(
    general_potential: pd.DataFrame,
    selected_potential: pd.DataFrame,
    selected_profile: str,
    census_values: pd.DataFrame,
    *, by_area: bool = False,
) -> pd.DataFrame:
    profiles, direct = _potential_profiles(selected_potential, selected_profile)
    if profiles.empty or census_values.empty:
        return pd.DataFrame()

    comparison = census_values.merge(profiles, on=["dimensao", "categoria_key"], how="inner")
    comparison = comparison.merge(direct, on=["area", "profile_key", "dimensao", "categoria_key"], how="left")
    comparison["diff"] = comparison["diferenca_precalculada"].where(
        comparison["diferenca_precalculada"].notna(),
        comparison["pct_icp_categoria"] - comparison["pct_populacao_categoria"],
    )
    comparison["pop_total"] = comparison["populacao_total_precalculada"].where(
        comparison["populacao_total_precalculada"].gt(0), comparison["populacao_total"]
    )
    comparison["peso_perfil"] = pd.to_numeric(comparison["peso_perfil"], errors="coerce").fillna(0)
    comparison["peso_pop"] = comparison["pop_total"].fillna(0).clip(lower=0) * comparison["peso_perfil"]
    comparison["oportunidade_area"] = (
        (-comparison["diff"]).clip(lower=0) / 100 * comparison["pop_total"].fillna(0)
    )
    comparison["oportunidade_ponderada"] = comparison["oportunidade_area"] * comparison["peso_perfil"]
    comparison["gap_ponderado"] = comparison["diff"].abs() * comparison["peso_pop"]

    area_dimension = comparison.groupby(["area", "codigo_ibge", "dimensao"], as_index=False).agg(
        peso=("peso_perfil", "sum"),
        oportunidade=("oportunidade_ponderada", "sum"),
        gap_ponderado=("gap_ponderado", "sum"),
        peso_pop=("peso_pop", "sum"),
    )
    area_dimension["oportunidade"] = np.where(
        area_dimension["peso"].gt(0), area_dimension["oportunidade"] / area_dimension["peso"], 0
    )
    area_dimension["gap_medio"] = np.where(
        area_dimension["peso_pop"].gt(0), area_dimension["gap_ponderado"] / area_dimension["peso_pop"], np.nan
    )
    territory_key = "area" if by_area else "codigo_ibge"
    municipal_dimension = area_dimension.groupby([territory_key, "dimensao"], as_index=False).agg(
        oportunidade=("oportunidade", "sum"),
        gap_ponderado=("gap_ponderado", "sum"),
        peso_pop=("peso_pop", "sum"),
    )
    municipal_dimension["gap_medio"] = np.where(
        municipal_dimension["peso_pop"].gt(0),
        municipal_dimension["gap_ponderado"] / municipal_dimension["peso_pop"],
        np.nan,
    )
    municipalities = municipal_dimension.groupby(territory_key, as_index=False).agg(
        oportunidade_demografica=("oportunidade", "mean"),
        diferenca_media_absoluta=("gap_medio", "mean"),
        dimensoes_com_dados=("dimensao", "nunique"),
    )
    municipalities["similaridade"] = (100 - municipalities["diferenca_media_absoluta"]).clip(0, 100)

    base = general_potential.copy()
    if not base.empty and {"cd_area_ponderada", "qt_votos_territorio"}.issubset(base.columns):
        base["area"] = _area_codes(base["cd_area_ponderada"])
        base["codigo_ibge"] = _municipality_codes(base["area"])
        base["qt_votos_territorio"] = pd.to_numeric(base["qt_votos_territorio"], errors="coerce").fillna(0)
        base = base.drop_duplicates("area")
        votes = base.groupby(territory_key, as_index=False)["qt_votos_territorio"].sum().rename(
            columns={"qt_votos_territorio": "votos_base"}
        )
        municipalities = votes.merge(municipalities, on=territory_key, how="outer")
    else:
        municipalities["votos_base"] = 0.0
    municipalities["votos_base"] = municipalities["votos_base"].fillna(0.0)
    valid = municipalities[municipalities["dimensoes_com_dados"].eq(3)].copy()
    if valid.empty:
        positive_votes = municipalities.loc[municipalities["votos_base"].gt(0), "votos_base"]
        threshold = float(positive_votes.quantile(0.75)) if not positive_votes.empty else np.inf
        municipalities["classe_expansao"] = np.where(
            municipalities["votos_base"].ge(threshold) & municipalities["votos_base"].gt(0), "AZUL", "CINZA"
        )
        return municipalities
    positive_votes = municipalities.loc[municipalities["votos_base"].gt(0), "votos_base"]
    vote_threshold = float(positive_votes.quantile(0.75)) if not positive_votes.empty else np.inf
    positive_opportunity = valid.loc[valid["oportunidade_demografica"].gt(0), "oportunidade_demografica"]
    opportunity_threshold = float(positive_opportunity.quantile(0.75)) if not positive_opportunity.empty else np.inf
    similarity_low = float(valid["similaridade"].quantile(0.25))
    similarity_mid = float(valid["similaridade"].median())

    classes = []
    for row in municipalities.itertuples(index=False):
        if row.votos_base >= vote_threshold and row.votos_base > 0:
            classes.append("AZUL")
        elif row.dimensoes_com_dados != 3:
            classes.append("CINZA")
        elif row.similaridade < similarity_low or row.oportunidade_demografica <= 0:
            classes.append("CINZA")
        elif row.oportunidade_demografica >= opportunity_threshold and row.similaridade >= similarity_mid:
            classes.append("VERDE")
        elif row.oportunidade_demografica > 0:
            classes.append("AMARELO")
        else:
            classes.append("CINZA")
    municipalities["classe_expansao"] = classes
    return municipalities


def _expansion_legend() -> None:
    items = [
        ("VERDE", "Oportunidade de expansão", "Potencial demográfico alto e boa aderência ao perfil."),
        ("AZUL", "Proteger a base", "Municípios com mais votos atuais; proteger essas bases."),
        ("AMARELO", "Potencial a desenvolver", "Há população em oportunidade, com menor aderência ao perfil."),
        ("CINZA", "Baixa similaridade", "Baixa similaridade, sem sinal de expansão ou sem dados completos."),
    ]
    cards = "".join(
        f'<div class="dna-expansion-legend-item" style="--class-color:{CLASS_COLORS[key]}"><div class="dna-expansion-class-badge"><span></span>{key}</div><h3>{title}</h3><p>{description}</p></div>'
        for key, title, description in items
    )
    st.html(f"""
    <style>
    .dna-expansion-legend {{display:grid;grid-template-columns:1fr;gap:16px}}
    .dna-expansion-legend-item {{border:1px solid color-mix(in srgb,var(--class-color) 45%,transparent);border-radius:16px;background:radial-gradient(ellipse at top left,color-mix(in srgb,var(--class-color) 25%,transparent),transparent 85%),linear-gradient(145deg,rgba(11,31,77,.9),rgba(7,24,54,.85));padding:22px 24px;color:#eaf2ff;box-shadow:0 10px 24px rgba(0,0,0,.16);min-height:156px;box-sizing:border-box}}
    .dna-expansion-class-badge {{display:inline-flex;gap:8px;align-items:center;border:1px solid color-mix(in srgb,var(--class-color) 40%,transparent);border-radius:999px;padding:5px 10px;font-size:.68rem;font-weight:800;letter-spacing:.08em;background:color-mix(in srgb,var(--class-color) 12%,transparent)}}
    .dna-expansion-class-badge span {{width:9px;height:9px;border-radius:50%;background:var(--class-color)}}
    .dna-expansion-legend-item h3 {{margin:12px 0 7px;padding:0;font-size:clamp(1.15rem,1.5vw,1.45rem);font-weight:850;line-height:1.2;color:#f8fbff}}
    .dna-expansion-legend-item p {{margin:0;color:#cbd8ed;font-size:.84rem;line-height:1.5}}
    @media(max-width:640px){{.dna-expansion-legend-item{{min-height:0;padding:18px}}}}
    </style><div class="dna-expansion-legend">{cards}</div>
    """)


def _expansion_map(city_data: pd.DataFrame) -> object | None:
    geojson, _, municipalities, _ = load_geo_reference()
    if not geojson or municipalities is None or municipalities.empty:
        return None
    geo_ids = sorted({str(feature.get("properties", {}).get("id", "")) for feature in geojson.get("features", [])})
    if not geo_ids:
        return None
    frame = pd.DataFrame({"codigo_ibge": geo_ids})
    names = municipalities[["codigo_ibge", "nome"]].copy()
    names["codigo_ibge"] = _municipality_codes(names["codigo_ibge"])
    frame = frame.merge(names, on="codigo_ibge", how="left")
    display_cols = [
        "codigo_ibge", "oportunidade_demografica", "diferenca_media_absoluta", "similaridade",
        "dimensoes_com_dados", "votos_base", "classe_expansao",
    ]
    frame = frame.merge(city_data[display_cols], on="codigo_ibge", how="left")
    frame["classe_expansao"] = frame["classe_expansao"].fillna("CINZA")
    frame["votos_base"] = pd.to_numeric(frame["votos_base"], errors="coerce").fillna(0.0)
    frame["oportunidade_demografica"] = pd.to_numeric(frame["oportunidade_demografica"], errors="coerce").fillna(0.0)
    frame["municipio"] = frame["nome"].fillna("Município")
    frame["classe_label"] = frame["classe_expansao"].map({
        "VERDE": "Pode buscar muitos votos",
        "AZUL": "Base com muitos votos: proteger",
        "AMARELO": "Oportunidade com menor aderência",
        "CINZA": "Baixa similaridade ou sem dados completos",
    })
    fig = categorical_choropleth(
        frame, geojson, location="codigo_ibge", category="classe_expansao",
        categories=list(CLASS_COLORS), colors=list(CLASS_COLORS.values()),
        hover_name="municipio", custom_data=["classe_label", "votos_base", "oportunidade_demografica", "similaridade"],
    )
    fig.update_traces(hovertemplate=(
        "<b>%{hovertext}</b><br>%{customdata[0]}<br>Votos: %{customdata[1]:,.0f}"
        "<br>Oportunidade: %{customdata[2]:,.0f}<br>Similaridade: %{customdata[3]:.1f}<extra></extra>"
    ))
    return fig


def render_vote_expansion() -> None:
    potential_general = _read("potencial_geral")
    potential_clusters = _read("potencial_clusters")
    labels = ["ELEITOR IDEAL"]
    if potential_clusters is not None and "cluster_strategy_label" in potential_clusters:
        labels.extend(sorted(
            value for value in potential_clusters["cluster_strategy_label"].dropna().astype(str).str.strip().unique()
            if value
        ))
    st.html('''<style>
    .st-key-dna_expansion_map_card{padding:24px!important;border:1px solid rgba(96,165,250,.3)!important;border-radius:20px!important;background:linear-gradient(135deg,rgba(11,31,77,.76),rgba(7,24,54,.68))!important;box-shadow:0 12px 30px rgba(0,0,0,.14)}
    @media(max-width:640px){.st-key-dna_expansion_map_card{padding:16px!important}}
    </style>''')
    map_col, cards_col = st.columns([0.70, 0.30], gap="large")
    with map_col:
        map_card = st.container(border=True, key="dna_expansion_map_card")
    with map_card:
        _, control = st.columns([0.55, 0.45], vertical_alignment="bottom")
    with control:
        selected_profile = st.selectbox("Perfil para expansão", labels, key="dna_expansion_profile")
    selected_potential = potential_general if selected_profile == "ELEITOR IDEAL" else potential_clusters
    census_values = _census_area_profiles(
        _read("censo_genero"), _read("censo_idade"), _read("censo_escolaridade")
    )
    city_data = _expansion_city_frame(
        potential_general if potential_general is not None else pd.DataFrame(),
        selected_potential if selected_potential is not None else pd.DataFrame(),
        selected_profile,
        census_values,
    )
    with cards_col:
        _expansion_legend()
    with map_card:
        if city_data.empty:
            st.info("Ainda não há dados completos de Censo e potencial demográfico para montar este mapa.")
            return
        fig = _expansion_map(city_data)
        if fig is None:
            st.info("A malha municipal de Minas Gerais não está disponível.")
            return
        fig.update_layout(height=560, coloraxis_showscale=False, margin={"l": 0, "r": 0, "t": 8, "b": 0})
        st.plotly_chart(fig, width="stretch", height=560, key="dna_vote_expansion_map")
        st.caption(
            "O potencial combina a população acima da participação do ICP (`diferenca_pontos_percentuais` negativa) nas dimensões de gênero, idade e escolaridade. "
            "As faixas são relativas ao ICP selecionado: azul destaca o quartil superior de votos atuais; verde exige potencial demográfico no quartil superior e similaridade acima da mediana; "
            "amarelo indica oportunidade positiva com similaridade acima do quartil inferior. Potencial demográfico orienta busca territorial e não é previsão de votos."
        )



def render_municipal_expansion() -> None:
    """Display expansion at its source resolution: Census weighted areas."""
    import html
    from eleitoral.maps.dna_geo_reference import load_geo_layer, load_area_ponderada_bairro_crosswalk
    from eleitoral.maps.territorial_mesh import mesoregion_options, municipality_options
    from eleitoral.dna.demographic_alignment import weighted_area_geojson, area_neighborhoods

    general = _read("potencial_geral")
    clusters = _read("potencial_clusters")
    labels = ["ELEITOR IDEAL"]
    if clusters is not None and "cluster_strategy_label" in clusters:
        labels.extend(sorted({str(v).strip() for v in clusters["cluster_strategy_label"].dropna() if str(v).strip()}))
    st.html('''<style>
    .st-key-dna_municipal_expansion_layout [class*="st-key-dna_municipal_class_"]{
        padding:.9rem 1rem!important;border:1px solid rgba(177,211,255,.34)!important;
        border-radius:16px!important;
        background:linear-gradient(145deg,rgba(11,31,77,.76) 0%,rgba(7,24,54,.68) 100%)!important;
        box-shadow:0 12px 30px rgba(1,8,24,.22)!important;box-sizing:border-box;
    }
    .dna-municipal-class-title{
        display:inline-flex;align-items:center;max-width:100%;box-sizing:border-box;
        padding:.4rem .75rem;border-radius:999px;color:#fff;font-weight:800;
        font-size:.92rem;line-height:1.35;box-shadow:inset 0 1px 0 rgba(255,255,255,.15);
    }
    @media(min-width:900px){
        .st-key-dna_municipal_expansion_layout > [data-testid="stHorizontalBlock"],
        .st-key-dna_municipal_expansion_layout > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]{align-items:stretch}
        .st-key-dna_municipal_expansion_layout [data-testid="stColumn"] > [data-testid="stVerticalBlock"]{height:100%}
        .st-key-dna_municipal_expansion_layout [data-testid="stColumn"]:last-child > [data-testid="stVerticalBlock"]{gap:1rem}
        .st-key-dna_municipal_expansion_layout [class*="st-key-dna_municipal_class_"]{flex:1;min-height:0}
        .st-key-dna_municipal_expansion_layout .st-key-dna_potential_map_card{height:100%}
    }
    </style>''')
    with st.container(key="dna_municipal_expansion_layout"):
        map_col, cards_col = st.columns([0.70, 0.30], gap="large")
    frame = pd.DataFrame()
    descriptions = {
        "VERDE": ("Oportunidade alta", "Potencial demogr\u00e1fico alto e boa ader\u00eancia ao perfil."),
        "AZUL": ("Proteger a base", "\u00c1reas com mais votos atuais; proteger essas bases."),
        "AMARELO": ("Oportunidade com menor ader\u00eancia", "H\u00e1 popula\u00e7\u00e3o em oportunidade, com menor ader\u00eancia ao perfil."),
        "CINZA": ("Baixa similaridade ou dados incompletos", "Baixa similaridade, sem sinal de expans\u00e3o ou sem dados completos."),
    }
    with map_col:
        with st.container(border=True, key="dna_potential_map_card"):
            meso = st.selectbox("Mesorregi\u00e3o", ["Todas", *mesoregion_options()], key="dna_potential_mesorregiao")
            choices = municipality_options(meso)
            if not choices:
                st.info("Nenhum munic\u00edpio dispon\u00edvel para a mesorregi\u00e3o selecionada.")
                return
            code = st.selectbox("Munic\u00edpio", [c for c, _ in choices], format_func=dict(choices).get,
                                key=f"dna_potential_municipio_{meso}")
            profile = st.selectbox("Perfil para expans\u00e3o", labels, key="dna_municipal_expansion_profile")
            census = _census_area_profiles(_read("censo_genero"), _read("censo_idade"), _read("censo_escolaridade"))
            results = _expansion_city_frame(
                general if general is not None else pd.DataFrame(),
                (general if profile == "ELEITOR IDEAL" else clusters), profile, census, by_area=True,
            )
            areas = load_geo_layer("area_ponderada")
            areas = areas.loc[areas["code_muni"].astype("string").eq(code)].copy()
            areas["area"] = areas["code_weighting"].astype("string").str.zfill(10)
            areas["code_weighting"] = areas["area"]
            areas = areas.drop_duplicates("area")
            if areas.empty:
                st.info("Malha de \u00e1reas ponderadas indispon\u00edvel para este munic\u00edpio.")
                return
            neighborhoods = area_neighborhoods(load_area_ponderada_bairro_crosswalk(), code)
            frame = areas[["area"]].copy()
            if results.empty:
                st.info("Dados de Censo ou potencial indispon\u00edveis; as \u00e1reas permanecem neutras.")
                frame["classe_expansao"] = "CINZA"
                for col in ["votos_base", "oportunidade_demografica", "similaridade"]:
                    frame[col] = np.nan
            else:
                frame = frame.merge(results, on="area", how="left", validate="one_to_one")
                frame["classe_expansao"] = frame["classe_expansao"].fillna("CINZA")
            frame["nome"] = "\u00c1rea ponderada " + frame["area"]
            frame["bairros"] = frame["area"].map(neighborhoods).fillna("Sem bairro TSE vinculado")
            frame["classe_label"] = frame["classe_expansao"].map({k: v[0] for k, v in descriptions.items()})
            for col in ["votos_base", "oportunidade_demografica", "similaridade"]:
                frame[col + "_label"] = frame[col].map(lambda v: "Indispon\u00edvel" if pd.isna(v) else f"{v:,.1f}".replace(",", "_").replace(".", ",").replace("_", "."))
            fig = categorical_choropleth(frame, weighted_area_geojson(areas), location="area", category="classe_expansao",
                categories=list(CLASS_COLORS), colors=list(CLASS_COLORS.values()), hover_name="nome",
                custom_data=["classe_label", "votos_base_label", "oportunidade_demografica_label", "similaridade_label", "bairros"])
            fig.update_layout(coloraxis_showscale=False)
            fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<br>Votos da \u00e1rea: %{customdata[1]}<br>Oportunidade: %{customdata[2]}<br>Similaridade: %{customdata[3]}<br>Bairros TSE de refer\u00eancia: %{customdata[4]}<extra></extra>")
            st.plotly_chart(fig, width="stretch", height=640, key="dna_municipal_expansion_map")
            st.caption("M\u00e9tricas por \u00e1rea ponderada, vinculadas diretamente por c\u00f3digo IBGE. Bairros TSE s\u00e3o refer\u00eancias por ponto, sem rateio dos valores. As faixas usam todas as \u00e1reas dispon\u00edveis para o perfil: quartil superior dos votos para prote\u00e7\u00e3o; quartil superior da oportunidade e similaridade acima da mediana para verde. Amarelo exige oportunidade positiva e similaridade acima do quartil inferior. Potencial n\u00e3o \u00e9 previs\u00e3o de votos.")
    with cards_col:
        for category, (title, description) in descriptions.items():
            count = int(frame["classe_expansao"].eq(category).sum())
            with st.container(border=True, key=f"dna_municipal_class_{category.lower()}"):
                st.html(f'<div class="dna-municipal-class-title" style="background:{CLASS_COLORS[category]}">{html.escape(title)}</div>')
                st.metric("\u00c1reas ponderadas", count)
                st.caption(description)
