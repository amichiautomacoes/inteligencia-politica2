"""Municipal potential using Census sectors and exact IBGE neighborhood keys."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import streamlit as st
from shapely.geometry import mapping
from shapely.ops import unary_union

from eleitoral.maps.choropleth_maps import categorical_choropleth
from eleitoral.maps.dna_geo_reference import (
    load_municipality_sectors, load_sector_ibge_crosswalk, load_sector_neighborhood_lookup, load_geo_layer,
)
from eleitoral.maps.territorial_mesh import mesoregion_options, municipality_options


def sector_neighborhoods(crosswalk: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    """One label per sector; conflicting exact matches remain explicit."""
    rows = crosswalk.rename(columns={
        "id_unidade": "setor", "ibge_codigo_bairro_do_ponto": "codigo_bairro_ibge",
        "ibge_bairro_do_ponto": "nome_bairro_ibge",
    }).copy()
    rows["setor"] = pd.to_numeric(rows["setor"], errors="coerce").astype("Int64").astype("string")
    official = lookup.rename(columns={"cd_setor_censitario": "setor"}).copy()
    official["setor"] = official["setor"].astype("string")
    rows = pd.concat([rows, official], ignore_index=True)
    for field in ("codigo_bairro_ibge", "nome_bairro_ibge"):
        rows[field] = rows[field].astype("string").str.strip()
        rows[field] = rows[field].mask(rows[field].isin(["", "<NA>", "nan", "None"]))
    rows = rows.dropna(subset=["setor", "nome_bairro_ibge"])
    return rows.groupby("setor", as_index=False).agg(
        codigo_bairro_ibge=("codigo_bairro_ibge", lambda x: " / ".join(sorted(set(x.dropna())))),
        nome_bairro_ibge=("nome_bairro_ibge", lambda x: " / ".join(sorted(set(x.dropna())))),
    )


def sector_scores(data: pd.DataFrame | None, label: str) -> pd.DataFrame:
    from eleitoral.dna.dna_expansion import _diagnostic_city_frame

    if data is None or data.empty:
        return pd.DataFrame()
    data = data.copy()
    if label != "ELEITOR IDEAL":
        data = data.loc[data["cluster_strategy_label"].eq(label)].copy()
    if data.empty:
        return pd.DataFrame()
    # Reuse the same relative classification at sector resolution. Reference
    # population repeats per cluster, so the classifier retains it once.
    data["cd_ibge_municipio_setor"] = data["cd_setor_censitario"].astype("string")
    data["cobertura_dados_completa"] = data["dados_completos_09a"]
    return _diagnostic_city_frame(data).rename(columns={"codigo_ibge": "setor"})


def sector_map_frame(sectors: pd.DataFrame, scores: pd.DataFrame, neighborhoods: pd.DataFrame) -> pd.DataFrame:
    frame = sectors[["code_tract"]].rename(columns={"code_tract": "setor"}).copy()
    frame["setor"] = frame["setor"].astype("string")
    if scores.empty:
        frame["classe_expansao"] = "CINZA"
        for field in ("votos_base", "oportunidade_demografica", "similaridade"):
            frame[field] = np.nan
    else:
        frame = frame.merge(scores, on="setor", how="left", validate="one_to_one")
        frame["classe_expansao"] = frame["classe_expansao"].fillna("CINZA")
    frame = frame.merge(neighborhoods, on="setor", how="left", validate="one_to_one")
    frame["nome_bairro_ibge"] = frame["nome_bairro_ibge"].fillna("Sem bairro IBGE vinculado")
    frame["codigo_bairro_ibge"] = frame["codigo_bairro_ibge"].fillna("")
    return frame


def render_municipal_expansion() -> None:
    from eleitoral.dna.dna_expansion import _read, CLASS_COLORS, _diagnostic_city_frame

    general = _read("diagnostico_geral_setor")
    clusters = _read("diagnostico_clusters_setor")
    labels = ["ELEITOR IDEAL"]
    if clusters is not None and "cluster_strategy_label" in clusters:
        labels.extend(sorted(clusters["cluster_strategy_label"].dropna().unique()))
    descriptions = {
        "VERDE": ("Oportunidade alta", "População estimada do ICP no quartil superior e participação acima da mediana."),
        "AZUL": ("Proteger a base", "Setores no quartil superior dos votos associados."),
        "AMARELO": ("Potencial a desenvolver", "População estimada do ICP positiva fora dos critérios da oportunidade alta."),
        "CINZA": ("Sem potencial ou dados incompletos", "Sem diagnóstico, cobertura incompleta ou sem população estimada positiva."),
    }
    st.html('''<style>
    .st-key-dna_potential_map_card,[class*="st-key-dna_municipal_class_"]{padding:20px!important;border:1px solid rgba(177,211,255,.34)!important;border-radius:16px!important;background:linear-gradient(145deg,rgba(11,31,77,.76),rgba(7,24,54,.68))!important;box-shadow:0 12px 30px rgba(1,8,24,.22)!important}
    .dna-municipal-class-title{display:inline-flex;padding:.4rem .75rem;border-radius:999px;color:white;font-weight:800;line-height:1.35}
    </style>''')
    map_col, cards_col = st.columns([.70, .30], gap="large")
    with map_col, st.container(border=True, key="dna_potential_map_card"):
        meso = st.selectbox("Mesorregião", ["Todas", *mesoregion_options()], key="dna_potential_mesorregiao")
        choices = municipality_options(meso)
        if not choices:
            st.info("Nenhum município disponível para este recorte.")
            return
        code = st.selectbox("Município", [c for c, _ in choices], format_func=dict(choices).get,
                            key=f"dna_potential_municipio_{meso}")
        profile = st.selectbox("Perfil para expansão", labels, key="dna_municipal_expansion_profile")
        sectors = load_municipality_sectors(code).drop_duplicates("code_tract")
        if sectors.empty:
            st.info("Malha de setores censitários indisponível para este município.")
            return
        scores = sector_scores(general if profile == "ELEITOR IDEAL" else clusters, profile)
        try:
            neighborhoods = sector_neighborhoods(load_sector_ibge_crosswalk(), load_sector_neighborhood_lookup())
        except Exception:
            neighborhoods = pd.DataFrame(columns=["setor", "nome_bairro_ibge", "codigo_bairro_ibge"])
            st.info("Vínculos de bairros IBGE indisponíveis neste momento.")
        frame = sector_map_frame(sectors, scores, neighborhoods)
        if code == "3106200":
            # Aggregate only diagnosed sectors linked by exact IBGE neighborhood
            # code; never distribute neighborhood totals back over sectors.
            linked = scores.reindex(columns=["setor", "votos_base", "oportunidade_demografica", "reference", "complete"]).merge(neighborhoods, on="setor", how="inner", validate="one_to_one")
            linked = linked.loc[linked["codigo_bairro_ibge"].str.fullmatch(r"\d+", na=False)]
            grouped = linked.groupby("codigo_bairro_ibge", as_index=False).agg(
                votos_obtidos_2026=("votos_base", lambda x: x.sum(min_count=len(x))),
                populacao_estimada_icp=("oportunidade_demografica", lambda x: x.sum(min_count=len(x))),
                populacao_total_referencia=("reference", lambda x: x.sum(min_count=len(x))),
                cobertura_dados_completa=("complete", "all"),
            ).rename(columns={"codigo_bairro_ibge": "cd_ibge_municipio_setor"})
            results = _diagnostic_city_frame(grouped).rename(columns={"codigo_ibge": "setor"})
            bairros = load_geo_layer("bairro")
            bairros = bairros.loc[bairros["code_muni"].astype("string").eq(code)].copy()
            sectors = bairros.rename(columns={"code_neighborhood": "code_tract"})
            sectors["code_tract"] = sectors["code_tract"].astype("string")
            sectors = sectors.groupby("code_tract", as_index=False).agg(
                name_neighborhood=("name_neighborhood", "first"),
                geometry=("geometry", lambda x: unary_union(list(x.dropna()))),
            )
            if sectors.empty:
                st.info("Malha de bairros indisponível para Belo Horizonte.")
                return
            names = sectors[["code_tract", "name_neighborhood"]].rename(columns={"code_tract": "setor", "name_neighborhood": "nome_bairro_ibge"})
            names["setor"] = names["setor"].astype("string")
            names["codigo_bairro_ibge"] = names["setor"]
            frame = sector_map_frame(sectors, results, names)
        frame["nome"] = "Bairro: " + frame["nome_bairro_ibge"].replace("Sem bairro IBGE vinculado", "Sem bairro vinculado")
        frame["classe_label"] = frame["classe_expansao"].map({k: v[0] for k, v in descriptions.items()})
        for field in ("votos_base", "oportunidade_demografica", "similaridade"):
            frame[field + "_label"] = frame[field].map(
                lambda v: "Indisponível" if pd.isna(v) else f"{v:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")
            )
        geojson = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"id": str(row.code_tract)}, "geometry": mapping(row.geometry)}
            for row in sectors.itertuples(index=False) if row.geometry is not None and not row.geometry.is_empty
        ]}
        fig = categorical_choropleth(
            frame, geojson, location="setor", category="classe_expansao",
            categories=list(CLASS_COLORS), colors=list(CLASS_COLORS.values()), hover_name="nome",
            custom_data=["classe_label", "votos_base_label", "oportunidade_demografica_label", "similaridade_label", "nome_bairro_ibge", "codigo_bairro_ibge"],
        )
        fig.update_layout(height=640, coloraxis_showscale=False)
        fig.update_traces(hovertemplate=(
            "<b>%{hovertext}</b><br>%{customdata[0]}"
            "<br>Votos associados: %{customdata[1]}<br>População estimada do ICP: %{customdata[2]}"
            "<br>Parcela do ICP na população de referência: %{customdata[3]}%<extra></extra>"
        ))
        st.plotly_chart(fig, width="stretch", height=640, key="dna_municipal_expansion_map")
        if scores.empty:
            st.info("Diagnóstico por setor indisponível para este perfil; a malha permanece neutra.")
        st.caption("Em Belo Horizonte, os resultados são agregados por bairro a partir dos territórios com diagnóstico e vínculo exato no crosswalk. Nos demais municípios, os bairros identificam as unidades exibidas. Áreas sem diagnóstico permanecem cinza. Votos associados a locais de votação não representam residência dos eleitores. Potencial demográfico não é previsão de votos.")
    with cards_col:
        for category, (title, description) in descriptions.items():
            with st.container(border=True, key=f"dna_municipal_class_{category.lower()}"):
                st.html(f'<div class="dna-municipal-class-title" style="background:{CLASS_COLORS[category]}">{html.escape(title)}</div>')
                st.metric("Bairros" if code == "3106200" else "Áreas", int(frame["classe_expansao"].eq(category).sum()))
                st.caption(description.replace("Setores", "Bairros" if code == "3106200" else "Áreas"))
