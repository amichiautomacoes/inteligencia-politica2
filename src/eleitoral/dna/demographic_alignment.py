"""Descriptive comparison of Census 2022 population and candidate ICP profiles."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shapely.geometry import mapping


GREEN_SCALE = [
    [0.0, "#eaf8ec"],
    [0.60, "#d7f2dd"],
    [0.75, "#a6dfb4"],
    [0.85, "#65bd80"],
    [0.93, "#278657"],
    [1.0, "#075137"],
]
AGE_CATEGORIES = (
    "16_ou_17_anos", "18_a_24_anos", "25_a_34_anos",
    "35_a_44_anos", "45_a_59_anos", "60_anos_ou_mais",
)


@dataclass(frozen=True)
class Profile:
    key: str
    label: str
    categories: dict[str, str]
    percentages: dict[str, float]


def _slug(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def profile_options(general: pd.DataFrame | None, clusters: pd.DataFrame | None) -> list[Profile]:
    """Keep cluster IDs distinct even when their strategy labels repeat."""
    options: list[Profile] = []
    for frame, is_cluster in ((general, False), (clusters, True)):
        if frame is None or frame.empty or not {"dimensao", "categoria_icp", "pct_icp_categoria"}.issubset(frame):
            continue
        if is_cluster:
            groups = frame.loc[frame["perfil_eleitor"].notna()].groupby("perfil_eleitor", sort=True)
        else:
            groups = [(None, frame)]
        for identifier, group in groups:
            rows = group.drop_duplicates("dimensao").set_index("dimensao")
            categories = {str(dimension): _slug(row["categoria_icp"]) for dimension, row in rows.iterrows()}
            percentages = {
                str(dimension): float(pd.to_numeric(row["pct_icp_categoria"], errors="coerce"))
                for dimension, row in rows.iterrows()
            }
            if is_cluster:
                cluster_id = str(int(float(identifier)))
                strategy = str(group["cluster_strategy_label"].dropna().iloc[0]).strip().title()
                persona = str(group["persona_executiva"].dropna().iloc[0]).strip()
                label = f"{strategy} · Cluster {cluster_id} · {persona}"
                key = f"cluster_{cluster_id}"
            else:
                label, key = "Eleitor ideal · ICP geral", "geral"
            options.append(Profile(key, label, categories, percentages))
    return options


def population_by_area(gender: pd.DataFrame | None, age: pd.DataFrame | None) -> pd.DataFrame:
    """One row per weighted area with separate, count-based denominators."""
    if gender is None or age is None or gender.empty or age.empty:
        return pd.DataFrame()
    gender_columns = ["populacao_genero_feminino", "populacao_genero_masculino"]
    age_columns = [f"populacao_idade_{category}" for category in AGE_CATEGORIES]
    required_gender = {"cd_area_ponderada", *gender_columns}
    required_age = {"cd_area_ponderada", *age_columns}
    if not required_gender.issubset(gender) or not required_age.issubset(age):
        return pd.DataFrame()
    left = gender[["cd_area_ponderada", *gender_columns]].drop_duplicates("cd_area_ponderada").copy()
    right = age[["cd_area_ponderada", *age_columns]].drop_duplicates("cd_area_ponderada").copy()
    left["area"] = left["cd_area_ponderada"].astype("string").str.zfill(10)
    right["area"] = right["cd_area_ponderada"].astype("string").str.zfill(10)
    frame = left.drop(columns="cd_area_ponderada").merge(
        right.drop(columns="cd_area_ponderada"), on="area", how="inner", validate="one_to_one"
    )
    for column in [*gender_columns, *age_columns]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").clip(lower=0)
    frame["municipio"] = frame["area"].str[:7]
    return frame


def area_neighborhoods(crosswalk: pd.DataFrame, municipality_code: str) -> pd.Series:
    """Return reference TSE neighborhoods per weighted area, without reallocating population."""
    required = {"cd_ibge_municipio", "id_unidade", "nm_bairro", "id_bairro_tse"}
    if crosswalk is None or crosswalk.empty or not required.issubset(crosswalk):
        return pd.Series(dtype="string")
    rows = crosswalk.copy()
    rows["municipio"] = pd.to_numeric(rows["cd_ibge_municipio"], errors="coerce").astype("Int64").astype("string")
    rows = rows.loc[rows["municipio"].eq(str(municipality_code))]
    rows["area"] = pd.to_numeric(rows["id_unidade"], errors="coerce").astype("Int64").astype("string").str.zfill(10)
    rows["bairro"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
    rows = rows.loc[rows["area"].notna() & rows["area"].str.startswith(str(municipality_code))]
    rows = rows.loc[rows["bairro"].ne("")].drop_duplicates(["area", "id_bairro_tse"])
    return rows.groupby("area")["bairro"].apply(lambda names: ", ".join(dict.fromkeys(names))).astype("string")


def _similarity(local: pd.Series, reference: float) -> pd.Series:
    if not np.isfinite(reference) or reference <= 0 or reference > 100:
        return pd.Series(np.nan, index=local.index)
    return (np.minimum(local, reference) / np.maximum(local, reference) * 100).where(local.notna())


def alignment(frame: pd.DataFrame, profile: Profile, *, by_municipality: bool) -> pd.DataFrame:
    """Compare independent gender/age shares; never multiply marginal shares."""
    if frame.empty:
        return pd.DataFrame()
    key = "municipio" if by_municipality else "area"
    count_columns = [column for column in frame if column.startswith("populacao_genero_") or column.startswith("populacao_idade_")]
    result = frame.groupby(key, as_index=False)[count_columns].sum(min_count=1) if by_municipality else frame[[key, *count_columns]].copy()
    result["populacao"] = result[["populacao_genero_feminino", "populacao_genero_masculino"]].sum(axis=1, min_count=2)
    dimensions = []
    for dimension in ("genero", "idade"):
        category = profile.categories.get(dimension, "")
        column = f"populacao_{dimension}_{category}"
        denominator_columns = (
            ["populacao_genero_feminino", "populacao_genero_masculino"]
            if dimension == "genero" else [f"populacao_idade_{item}" for item in AGE_CATEGORIES]
        )
        denominator = result[denominator_columns].sum(axis=1, min_count=len(denominator_columns))
        local_column = f"local_{dimension}"
        score_column = f"score_{dimension}"
        if category == "nao_informado" or column not in result:
            result[local_column] = np.nan
            result[score_column] = np.nan
            continue
        result[local_column] = (result[column] / denominator * 100).where(denominator.gt(0))
        result[score_column] = _similarity(result[local_column], profile.percentages.get(dimension, np.nan))
        dimensions.append(score_column)
    result["dimensoes"] = result[["score_genero", "score_idade"]].notna().sum(axis=1)
    result["alinhamento"] = result[["score_genero", "score_idade"]].mean(axis=1)
    result.loc[result["dimensoes"].eq(0), "alinhamento"] = np.nan
    return result


def alignment_map(
    scores: pd.DataFrame, geojson: dict, *, key: str, names: pd.Series | None = None,
    profile: Profile | None = None, context: pd.Series | None = None,
    selected_code: str = "", height: int = 560,
) -> go.Figure:
    frame = scores.copy()
    frame[key] = frame[key].astype(str)
    frame["nome"] = frame[key].map(names).fillna(frame[key]) if names is not None else frame[key]
    frame["alinhamento_label"] = frame["alinhamento"].map(
        lambda value: f"{value:.1f}/100" if pd.notna(value) else "indisponível"
    )
    frame["icp_genero"] = profile.percentages.get("genero", np.nan) if profile else np.nan
    frame["icp_idade"] = profile.percentages.get("idade", np.nan) if profile else np.nan
    frame["contexto"] = frame[key].map(context).fillna("Sem bairro vinculado") if context is not None else ""
    context_hover = "<br>Bairros de referência: %{customdata[7]}" if context is not None else ""
    figure = go.Figure(go.Choropleth(
        geojson=geojson, locations=frame[key], z=frame["alinhamento"],
        zmin=0, zmax=100, featureidkey="properties.id", colorscale=GREEN_SCALE,
        colorbar={"title": "Alinhamento", "tickvals": [0, 60, 75, 85, 93, 100], "ticksuffix": "/100"},
        marker_line_color="rgba(201,230,214,0.78)", marker_line_width=0.55,
        customdata=frame[["nome", "alinhamento_label", "local_genero", "icp_genero",
                          "local_idade", "icp_idade", "dimensoes", "contexto"]].to_numpy(),
        hovertemplate=("<b>%{customdata[0]}</b><br>Alinhamento: %{customdata[1]}"
                       "<br>Gênero local × ICP: %{customdata[2]:.1f}% × %{customdata[3]:.1f}%"
                       "<br>Idade local × ICP: %{customdata[4]:.1f}% × %{customdata[5]:.1f}%"
                       "<br>Dimensões válidas: %{customdata[6]:.0f}/2"
                       + context_hover + "<extra></extra>"),
    ))
    if key == "area":
        geometry_ids = {str(feature.get("properties", {}).get("id", "")) for feature in geojson.get("features", [])}
        missing = sorted(geometry_ids - set(frame[key]))
        if missing:
            figure.add_trace(go.Choropleth(
                geojson=geojson, locations=missing, z=[0] * len(missing),
                featureidkey="properties.id", colorscale=[[0, "#617087"], [1, "#617087"]],
                showscale=False, marker_line_color="rgba(201,230,214,0.78)",
                marker_line_width=0.55,
                hovertemplate="Área ponderada %{location}<br>Sem dados populacionais<extra></extra>",
            ))
    if selected_code:
        figure.add_trace(go.Choropleth(
            geojson=geojson, locations=[str(selected_code)], z=[1],
            featureidkey="properties.id", colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            showscale=False, marker_line_color="#ffffff", marker_line_width=2.5,
            hoverinfo="skip",
        ))
    figure.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    figure.update_layout(
        height=height, margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
    )
    return figure


def weighted_area_geojson(areas: pd.DataFrame) -> dict:
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": str(row.code_weighting)},
         "geometry": mapping(row.geometry.simplify(0.0001, preserve_topology=True))}
        for row in areas.itertuples(index=False)
        if row.geometry is not None and not row.geometry.is_empty
    ]}
