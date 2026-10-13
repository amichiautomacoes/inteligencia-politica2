"""BH: geometria oficial por código IBGE; conteúdo exclusivamente do stage01b."""
from __future__ import annotations

import html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shapely.geometry import mapping
from shapely.ops import unary_union

from hf_sync import load_env
from eleitoral.maps.dna_geo_reference import geography_reference_path, _read_geo_parquet
from eleitoral.maps.territorial_mesh import _numeric_code_strings, _boundary_coordinates


@st.cache_data(show_spinner=False)
def load_bh_neighborhood_mesh() -> pd.DataFrame:
    env = load_env()
    mesh = _read_geo_parquet(
        geography_reference_path(env, "MG_bairros_CD2022.parquet"),
        columns=["code_muni", "code_neighborhood", "geometry"],
        filters=[("code_muni", "==", "3106200")],
    )
    mesh["id"] = _numeric_code_strings(mesh["code_neighborhood"])
    mesh = mesh.dropna(subset=["id", "geometry"])
    mesh = mesh.loc[mesh["id"].ne("") & mesh["geometry"].map(lambda shape: not shape.is_empty)]
    # Preserve all parts if an official code spans multiple polygon records.
    return mesh.groupby("id", as_index=False).agg(geometry=("geometry", lambda shapes: unary_union(list(shapes))))


def bh_neighborhood_frame(mesh: pd.DataFrame, votes: pd.DataFrame | None) -> pd.DataFrame:
    required = {"cd_ibge_municipio", "cd_ibge_bairro", "cd_bairro", "nm_bairro", "qt_votos"}
    if votes is None or not required.issubset(votes.columns):
        raise ValueError("Dados de bairros de BH indisponíveis no arquivo territorial do candidato.")
    rows = votes.loc[_numeric_code_strings(votes["cd_ibge_municipio"]).eq("3106200")].copy()
    rows["id"] = _numeric_code_strings(rows["cd_ibge_bairro"])
    rows = rows.dropna(subset=["id"])
    rows = rows.loc[rows["id"].ne("")]
    rows["qt_votos"] = pd.to_numeric(rows["qt_votos"], errors="coerce")
    rows["nm_bairro"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
    rows["cd_bairro"] = rows["cd_bairro"].fillna("").astype(str).str.strip()
    tse_rows = rows.groupby(["id", "cd_bairro", "nm_bairro"], as_index=False).agg(
        qt_votos=("qt_votos", lambda values: values.sum(min_count=1)),
    )
    tse_rows["detail"] = tse_rows.apply(
        lambda row: html.escape(row["nm_bairro"] or "Bairro TSE sem nome") + ": " +
        (f"{row['qt_votos']:,.0f}".replace(",", ".") + " votos" if pd.notna(row["qt_votos"]) else "Indisponível"),
        axis=1,
    ) if not tse_rows.empty else pd.Series(dtype=str)
    details = tse_rows.groupby("id")["detail"].agg("<br>".join)
    grouped = rows.groupby("id", as_index=False).agg(
        votes=("qt_votos", lambda values: values.sum(min_count=1)),
        name=("nm_bairro", lambda values: " / ".join(dict.fromkeys(value for value in values if value))),
    )
    result = mesh[["id", "geometry"]].merge(grouped, on="id", how="left", validate="one_to_one")
    result["name"] = result["name"].fillna("").replace("", "Bairro sem nome no arquivo do candidato")
    result["details"] = result["id"].map(details).fillna("Sem dados do candidato para este polígono")
    result["total_label"] = result["votes"].map(
        lambda value: f"{value:,.0f}".replace(",", ".") if pd.notna(value) else "Indisponível"
    )
    result.attrs["municipality_vote_total"] = float(rows["qt_votos"].sum())
    result.attrs["unmatched_rows"] = int((~rows["id"].isin(mesh["id"])).sum())
    return result


def bh_neighborhood_voting_map(votes: pd.DataFrame | None) -> tuple[go.Figure | None, int]:
    mesh = load_bh_neighborhood_mesh()
    if mesh.empty:
        return None, 0
    frame = bh_neighborhood_frame(mesh, votes)
    total = frame.attrs["municipality_vote_total"]
    logarithmic = total > 1000
    valid = frame["votes"].notna()
    maximum = frame["votes"].max()
    if pd.isna(maximum) or maximum <= 0:
        intensity = pd.Series(0.0, index=frame.index)
    elif logarithmic:
        intensity = np.log1p(frame["votes"]) / np.log1p(maximum)
    else:
        intensity = frame["votes"] / maximum
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"id": row.id},
         "geometry": mapping(row.geometry.simplify(0.0001, preserve_topology=True))}
        for row in frame.itertuples(index=False)
    ]}
    scale = [
        [0, "#e8f1ff"], [.25, "#bfd9ff"], [.5, "#60a5fa"], [.75, "#2563eb"], [1, "#0b1f4d"],
    ]
    fig = go.Figure()
    for mask, colors in ((~valid, [[0, "#64748b"], [1, "#64748b"]]), (valid, scale)):
        selected = frame.loc[mask]
        if selected.empty:
            continue
        fig.add_trace(go.Choropleth(
            geojson=geojson, locations=selected["id"],
            z=intensity.loc[mask].fillna(0), zmin=0, zmax=1,
            featureidkey="properties.id", colorscale=colors, showscale=False,
            marker_line_color="rgba(235,244,255,0.98)", marker_line_width=1.3,
            customdata=selected[["name", "total_label", "details"]].assign(name=selected["name"].map(html.escape)).to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[2]}<br>Total de votos associados: %{customdata[1]}<extra></extra>",
        ))
    lon, lat = _boundary_coordinates(unary_union(list(mesh["geometry"])))
    fig.add_trace(go.Scattergeo(lon=lon, lat=lat, mode="lines", line={"color": "rgba(248,251,255,1)", "width": 3.2}, hoverinfo="skip", showlegend=False))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0}, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font={"color": "#eaf2ff"},
        meta={"mesh_kind": "bairro", "scale_type": "logarithmic" if logarithmic else "linear", "municipality_vote_total": total, "unmatched_rows": frame.attrs["unmatched_rows"]},
    )
    return fig, len(mesh)
