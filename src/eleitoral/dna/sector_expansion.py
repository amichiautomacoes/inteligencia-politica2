"""Municipal potential using Census sector keys and TSE crosswalk labels."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shapely.geometry import mapping

from eleitoral.maps.choropleth_maps import categorical_choropleth
from eleitoral.maps.dna_geo_reference import (
    load_complete_municipality_sectors, load_geo_layer,
    load_crosswalk_geometry,
)
from eleitoral.maps.territorial_mesh import mesoregion_options, municipality_options, _boundary_coordinates, _sector_tse_neighborhood_names


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


def sector_map_frame(sectors: pd.DataFrame, scores: pd.DataFrame) -> pd.DataFrame:
    frame = sectors[["code_tract"]].rename(columns={"code_tract": "setor"}).copy()
    frame["setor"] = frame["setor"].astype("string")
    if scores.empty:
        frame["_has_diagnostic"] = False
        frame["classe_expansao"] = "CINZA"
        for field in ("votos_base", "oportunidade_demografica", "similaridade"):
            frame[field] = np.nan
    else:
        frame = frame.merge(scores, on="setor", how="left", validate="one_to_one", indicator="_diagnostic_match")
        frame["_has_diagnostic"] = frame["_diagnostic_match"].eq("both")
        frame = frame.drop(columns="_diagnostic_match")
        frame["classe_expansao"] = frame["classe_expansao"].fillna("CINZA")
    return frame


def neighborhood_counts(frame: pd.DataFrame, links: pd.DataFrame) -> pd.Series:
    """Count distinct TSE neighborhoods linked to displayed sectors per class."""
    linked = links[["id_unidade", "cd_bairro"]].dropna().drop_duplicates().copy()
    linked["cd_bairro"] = linked["cd_bairro"].astype("string").str.strip()
    linked = linked.loc[linked["cd_bairro"].ne("")]
    linked = linked.merge(frame[["setor", "classe_expansao"]], left_on="id_unidade", right_on="setor", validate="many_to_one")
    return linked.groupby("classe_expansao")["cd_bairro"].nunique()


def municipal_potential_frame(sectors: pd.DataFrame, scores: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Keep the complete mesh neutral wherever no TSE crosswalk relation exists."""
    related = links.dropna(subset=["cd_bairro", "id_unidade", "geometry"])
    related = related.loc[related["cd_bairro"].astype("string").str.strip().ne("")]
    if not scores.empty:
        scores = scores.loc[scores["setor"].isin(related["id_unidade"])]
    return sector_map_frame(sectors, scores)


def municipal_potential_hover_frame(frame: pd.DataFrame, links: pd.DataFrame, municipality_code: str) -> pd.DataFrame:
    """Label every displayed sector without inventing missing diagnostics."""
    from eleitoral.dna.dna_expansion import _map_metric_label

    frame = frame.copy()
    names = _sector_tse_neighborhood_names(
        frame[["setor"]].rename(columns={"setor": "id"}), municipality_code, crosswalk=links,
    )
    frame["nome_bairro_tse"] = names.replace("", "Bairro sem referência disponível")
    frame["nome"] = names.map(lambda name: "Bairro: " + html.escape(name) if name else "Bairro sem referência disponível")
    for field in ("votos_base", "oportunidade_demografica", "similaridade"):
        frame[field + "_label"] = frame[field].map(_map_metric_label)
    # Only a missing association gets a zero display. A null vote in an
    # existing diagnostic remains unavailable, and classification is unchanged.
    frame.loc[~frame["_has_diagnostic"], "votos_base_label"] = "0"
    frame["similaridade_label"] = frame["similaridade_label"].map(
        lambda value: value if value == "Indisponível" else value + "%"
    )
    return frame


def render_municipal_expansion() -> None:
    from eleitoral.dna.dna_expansion import _read, CLASS_COLORS

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
        sectors = load_complete_municipality_sectors(code).drop_duplicates("code_tract").copy()
        if sectors.empty:
            st.info("Malha de setores censitários indisponível para este município.")
            return
        scores = sector_scores(general if profile == "ELEITOR IDEAL" else clusters, profile)
        links = load_crosswalk_geometry("setor")
        links = links.loc[links["cd_ibge_municipio"].eq(code)].dropna(subset=["id_unidade"])
        # The official mesh supplies coverage. Linked sectors retain the
        # crosswalk geometry; all other sectors keep their IBGE geometry.
        geometry_by_sector = links.dropna(subset=["geometry"]).drop_duplicates("id_unidade").set_index("id_unidade")["geometry"]
        sectors["code_tract"] = sectors["code_tract"].astype("string")
        sectors["geometry"] = sectors.apply(lambda row: geometry_by_sector.get(row["code_tract"], row["geometry"]), axis=1)
        municipalities = load_geo_layer("municipio")
        municipality = municipalities.loc[municipalities["code_muni"].astype("string").eq(code), "geometry"]
        if municipality.empty:
            st.info("Contorno municipal IBGE indisponível para este município.")
            return
        boundary = municipality.iloc[0]
        sectors["geometry"] = sectors["geometry"].map(lambda shape: shape.intersection(boundary) if shape is not None else None)
        sectors = sectors.dropna(subset=["geometry"])
        sectors = sectors.loc[sectors["geometry"].map(lambda shape: not shape.is_empty)]
        frame = municipal_potential_frame(sectors, scores, links)
        counts = neighborhood_counts(frame, links)
        frame = municipal_potential_hover_frame(frame, links, code)
        frame["classe_label"] = frame["classe_expansao"].map({k: v[0] for k, v in descriptions.items()})
        geojson = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"id": str(row.code_tract)}, "geometry": mapping(row.geometry)}
            for row in sectors.itertuples(index=False) if row.geometry is not None and not row.geometry.is_empty
        ]}
        fig = categorical_choropleth(
            frame, geojson, location="setor", category="classe_expansao",
            categories=list(CLASS_COLORS), colors=list(CLASS_COLORS.values()), hover_name="nome",
            custom_data=["classe_label", "votos_base_label", "oportunidade_demografica_label", "similaridade_label"],
        )
        fig.update_layout(height=640, coloraxis_showscale=False)
        fig.update_traces(hovertemplate=(
            "<b>%{hovertext}</b><br>%{customdata[0]}"
            "<br>Votos associados: %{customdata[1]}<br>População estimada do ICP: %{customdata[2]}"
            "<br>Parcela do ICP na população de referência: %{customdata[3]}<extra></extra>"
        ))
        lon, lat = _boundary_coordinates(boundary)
        fig.add_trace(go.Scattergeo(
            lon=lon, lat=lat, mode="lines",
            line={"color": "rgba(248,251,255,0.98)", "width": 2.2},
            hoverinfo="skip", showlegend=False,
        ))
        st.plotly_chart(fig, width="stretch", height=640, key="dna_municipal_expansion_map")
        if scores.empty:
            st.info("Diagnóstico por setor indisponível para este perfil; a malha permanece neutra.")
        st.caption("O contorno municipal vem da malha IBGE. Todos os setores do município são exibidos; setores sem vínculo no crosswalk ou sem diagnóstico permanecem cinza. Os setores vinculados usam a geometria do crosswalk e o diagnóstico pelo código exato do setor. No hover, setores sem associação mostram 0 votos e o bairro da referência quando disponível; votos nulos em diagnósticos existentes continuam indisponíveis. Os cards contam bairros TSE ligados às categorias. Votos associados a locais de votação não representam residência dos eleitores. Potencial demográfico não é previsão de votos.")
    with cards_col:
        for category, (title, description) in descriptions.items():
            with st.container(border=True, key=f"dna_municipal_class_{category.lower()}"):
                st.html(f'<div class="dna-municipal-class-title" style="background:{CLASS_COLORS[category]}">{html.escape(title)}</div>')
                st.metric("Bairros", int(counts.get(category, 0)))
                st.caption(description)
        st.caption("Bairros TSE únicos vinculados aos setores de cada categoria. Um bairro ligado a setores de categorias diferentes pode aparecer em mais de um card.")
