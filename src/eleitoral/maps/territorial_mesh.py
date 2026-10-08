"""Municipal geometry with electoral neighborhood votes for Raio X."""

from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shapely import make_valid, union_all
from shapely.geometry import MultiPolygon, Point, Polygon, mapping
from shapely.geometry.polygon import orient

from eleitoral.maps.dna_geo_reference import (
    load_geo_layer,
    load_geo_reference,
    load_municipality_sectors,
    load_sector_neighborhood_lookup,
    load_tse_neighborhood_sector_crosswalk,
)


MIN_MUNICIPAL_COVERAGE = 0.95
MIN_WEIGHTED_AREAS_FOR_MESH = 2
BH_PROJECTION_CATEGORY_COLORS = {
    "Base Crítica (Fortaleza)": "#2563eb",
    "Vulnerável/Ameaçado": "#facc15",
    "Oportunidade BH": "#22c55e",
    "Demais bairros": "#52627a",
}


def mesoregion_options() -> list[str]:
    """Return the official Minas Gerais mesoregions used by the filters."""
    _, _, _, regions = load_geo_reference()
    if regions is None or regions.empty or "mesorregiao_nome" not in regions.columns:
        return []
    return sorted(
        {
            str(value).strip()
            for value in regions["mesorregiao_nome"].dropna()
            if str(value).strip()
        },
        key=str.casefold,
    )


def municipality_options(mesorregiao: str | None = None) -> list[tuple[str, str]]:
    municipalities = load_geo_layer("municipio")
    rows = municipalities[["code_muni", "name_muni"]].dropna().drop_duplicates("code_muni")
    if mesorregiao and mesorregiao != "Todas":
        _, _, _, regions = load_geo_reference()
        if regions is not None and not regions.empty and {
            "codigo_ibge", "mesorregiao_nome"
        }.issubset(regions.columns):
            selected_codes = regions.loc[
                regions["mesorregiao_nome"].astype(str).str.strip().eq(mesorregiao),
                "codigo_ibge",
            ].astype("string")
            rows = rows.loc[rows["code_muni"].astype("string").isin(selected_codes)]
    return sorted(
        ((str(row.code_muni), str(row.name_muni)) for row in rows.itertuples(index=False)),
        key=lambda item: item[1].casefold(),
    )


def _municipality_geometry(municipality_code: str):
    municipalities = load_geo_layer("municipio")
    municipality_rows = municipalities.loc[
        municipalities["code_muni"].astype("string").eq(str(municipality_code))
    ]
    return municipality_rows.iloc[0]["geometry"] if not municipality_rows.empty else None


def _mesh_covers_municipality(mesh: pd.DataFrame, municipality_geometry) -> bool:
    """Return whether a subdivision mesh represents the whole municipality."""
    if municipality_geometry is None or municipality_geometry.is_empty:
        return True
    geometries = [
        make_valid(geometry) if not geometry.is_valid else geometry
        for geometry in mesh.get("geometry", pd.Series(dtype=object)).dropna()
        if not geometry.is_empty
    ]
    if not geometries:
        return False
    municipality = (
        make_valid(municipality_geometry)
        if not municipality_geometry.is_valid
        else municipality_geometry
    )
    if municipality.is_empty or municipality.area <= 0:
        return False
    covered_area = union_all(geometries).intersection(municipality).area
    return covered_area / municipality.area >= MIN_MUNICIPAL_COVERAGE


def municipality_mesh(municipality_code: str) -> tuple[str, pd.DataFrame, str, str]:
    """Select geometry by availability, without joining electoral data."""
    municipality_geometry = _municipality_geometry(municipality_code)
    neighborhoods = load_geo_layer("bairro")
    neighborhoods = neighborhoods.loc[
        neighborhoods["code_muni"].astype("string").eq(str(municipality_code))
    ]
    if not neighborhoods.empty and _mesh_covers_municipality(neighborhoods, municipality_geometry):
        return "bairro", neighborhoods, "code_neighborhood", "name_neighborhood"

    areas = load_geo_layer("area_ponderada")
    areas = areas.loc[areas["code_muni"].astype("string").eq(str(municipality_code))]
    # A single weighted area would not subdivide the municipality, so only
    # that case falls back to census sectors. Municipalities with two or more
    # weighted areas use that coarser and more legible official mesh.
    if areas["code_weighting"].dropna().nunique() >= MIN_WEIGHTED_AREAS_FOR_MESH:
        return "area_ponderada", areas, "code_weighting", "code_weighting"

    sectors = load_municipality_sectors(municipality_code)
    return "setor", sectors, "code_tract", "code_tract"


def _attach_coordinate_matches(rows: pd.DataFrame, mesh: pd.DataFrame) -> pd.DataFrame:
    """Associate rows without a territorial code using their polling coordinates.

    ``stage01b_bairros`` contains a few electoral rows aggregated by bairro where
    the census-sector code is empty or does not belong to the selected mesh.  A
    strict code-only join silently drops those votes.  Coordinates are the only
    non-invented fallback available in that situation, so assign each row to the
    polygon that contains its polling point (or the nearest polygon when a point
    lies exactly on a boundary).
    """
    if rows.empty or not {"nr_latitude", "nr_longitude"}.issubset(rows.columns):
        return rows

    unmatched = rows[rows["_code"].eq("") | ~rows["_code"].isin(mesh["id"])].copy()
    if unmatched.empty:
        return rows

    lat = pd.to_numeric(unmatched["nr_latitude"], errors="coerce")
    lon = pd.to_numeric(unmatched["nr_longitude"], errors="coerce")
    valid = lat.between(-23.5, -14.0) & lon.between(-52.5, -39.0)
    if not valid.any():
        return rows

    geometries = list(mesh["geometry"])
    ids = list(mesh["id"])
    for index in unmatched.index[valid]:
        point = Point(float(lon.loc[index]), float(lat.loc[index]))
        containing = [position for position, geometry in enumerate(geometries) if geometry.covers(point)]
        if containing:
            rows.loc[index, "_code"] = ids[containing[0]]
            continue
        # A polling point can be a few metres outside a simplified polygon.
        nearest = min(range(len(geometries)), key=lambda position: geometries[position].distance(point))
        if geometries[nearest].distance(point) <= 0.002:
            rows.loc[index, "_code"] = ids[nearest]
    return rows


def _boundary_coordinates(geometry) -> tuple[list[float | None], list[float | None]]:
    """Return Plotly-compatible coordinates for a polygon's exterior boundary."""
    if geometry is None or geometry.is_empty:
        return [], []
    boundary = geometry.boundary
    parts = list(boundary.geoms) if hasattr(boundary, "geoms") else [boundary]
    lon: list[float | None] = []
    lat: list[float | None] = []
    for part in parts:
        if not hasattr(part, "coords"):
            continue
        for x, y in part.coords:
            lon.append(float(x))
            lat.append(float(y))
        lon.append(None)
        lat.append(None)
    return lon, lat


def _numeric_code_strings(values: pd.Series) -> pd.Series:
    return (
        pd.to_numeric(values, errors="coerce")
        .round()
        .astype("Int64")
        .astype("string")
    )


def _sector_tse_neighborhood_names(
    mesh: pd.DataFrame, municipality_code: str,
) -> pd.Series:
    """Label every sector from the complete TSE-neighborhood crosswalk.

    The crosswalk has one representative census sector for every TSE
    neighborhood. Sectors without a direct representative inherit the label
    from the nearest reference sector inside the same municipality so the
    tooltip remains informative even when the selected candidate had no votes
    there.
    """
    empty = pd.Series("", index=mesh.index, dtype="string")
    try:
        crosswalk = load_tse_neighborhood_sector_crosswalk()
    except Exception:
        return empty

    required = {"cd_ibge_municipio", "id_unidade", "nm_bairro"}
    if crosswalk.empty or not required.issubset(crosswalk.columns):
        return empty

    rows = crosswalk.copy()
    rows["_municipality_code"] = _numeric_code_strings(rows["cd_ibge_municipio"])
    rows = rows.loc[rows["_municipality_code"].eq(str(municipality_code))].copy()
    if rows.empty:
        return empty

    rows["_sector_code"] = _numeric_code_strings(rows["id_unidade"])
    rows["_tse_name"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
    if "nm_bairro_atribuido" in rows.columns:
        attributed = rows["nm_bairro_atribuido"].fillna("").astype(str).str.strip()
        rows.loc[rows["_tse_name"].eq(""), "_tse_name"] = attributed
    rows = rows.loc[rows["_sector_code"].notna() & rows["_tse_name"].ne("")]
    if rows.empty:
        return empty

    direct_names = rows.groupby("_sector_code")["_tse_name"].apply(
        lambda names: " / ".join(dict.fromkeys(names))
    )
    result = mesh["id"].map(direct_names).fillna("").astype("string")
    reference_rows = mesh.loc[mesh["id"].isin(direct_names.index), ["id", "geometry"]]
    reference_rows = reference_rows.loc[
        reference_rows["geometry"].map(lambda geometry: geometry is not None and not geometry.is_empty)
    ]
    if reference_rows.empty:
        return result

    references = [
        (row.geometry.representative_point(), str(direct_names.loc[row.id]))
        for row in reference_rows.itertuples(index=False)
    ]
    for index in result.index[result.eq("")]:
        geometry = mesh.at[index, "geometry"]
        if geometry is None or geometry.is_empty:
            continue
        point = geometry.representative_point()
        _, nearest_name = min(
            references,
            key=lambda reference: point.distance(reference[0]),
        )
        result.at[index] = nearest_name
    return result


def _plotly_polygon_geometry(geometry, municipality_geometry):
    """Clip a sector to the municipality and use Plotly's ring orientation.

    The compact census-sector layer uses counter-clockwise exterior rings. In
    Plotly's geographic projection those rings can be interpreted as the
    polygon complement, painting the area outside the municipality. Clipping
    also removes the small differences between the sector and corrected
    municipal layers.
    """
    if geometry is None or geometry.is_empty:
        return None

    sector = make_valid(geometry) if not geometry.is_valid else geometry
    municipality = (
        make_valid(municipality_geometry)
        if not municipality_geometry.is_valid
        else municipality_geometry
    )
    clipped = sector.intersection(municipality)
    if clipped.is_empty:
        return None

    polygons: list[Polygon] = []

    def collect_polygon_parts(candidate) -> None:
        if isinstance(candidate, Polygon):
            polygons.append(orient(candidate, sign=-1.0))
        elif isinstance(candidate, MultiPolygon) or hasattr(candidate, "geoms"):
            for part in candidate.geoms:
                collect_polygon_parts(part)

    collect_polygon_parts(clipped)
    if not polygons:
        return None
    if len(polygons) == 1:
        return polygons[0]
    return MultiPolygon(polygons)


def _municipality_comparison_map(
    mesh: pd.DataFrame,
    geojson: dict[str, object],
    municipality_geometry,
    kind: str,
    rows: pd.DataFrame,
    year: str,
) -> tuple[go.Figure | None, int]:
    history_votes = f"qt_votos_candidato_bairro_{year}"
    history_valid = f"qt_votos_validos_bairro_{year}"
    current_matched_votes = f"qt_votos_candidato_bairro_2026_locais_correspondidos_{year}"
    current_matched_valid = f"qt_votos_validos_bairro_2026_locais_correspondidos_{year}"
    source_diff = f"diff_market_share_bairro_pp_vs_{year}"
    required = {
        history_votes, history_valid, current_matched_votes,
        current_matched_valid, source_diff,
    }
    if not required.issubset(rows.columns):
        return None, 0

    for column in required:
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    full_votes = (
        rows.groupby("_code", as_index=False)
        .agg(votos_2026=("qt_votos", "sum"))
    )
    comparable = rows.loc[
        rows[source_diff].notna()
        & rows[history_votes].notna()
        & rows[history_valid].notna()
        & rows[current_matched_votes].notna()
        & rows[current_matched_valid].notna()
    ]
    if comparable.empty:
        return None, 0

    comparison = (
        comparable.groupby("_code", as_index=False)
        .agg(
            votos_referencia=(history_votes, "sum"),
            validos_referencia=(history_valid, "sum"),
            votos_2026_comparaveis=(current_matched_votes, "sum"),
            validos_2026_comparaveis=(current_matched_valid, "sum"),
        )
    )
    comparison["share_referencia"] = np.where(
        comparison["validos_referencia"].gt(0),
        comparison["votos_referencia"] / comparison["validos_referencia"] * 100,
        np.nan,
    )
    comparison["share_2026"] = np.where(
        comparison["validos_2026_comparaveis"].gt(0),
        comparison["votos_2026_comparaveis"] / comparison["validos_2026_comparaveis"] * 100,
        np.nan,
    )
    comparison["diff_pp"] = comparison["share_2026"] - comparison["share_referencia"]
    comparison = full_votes.merge(comparison, on="_code", how="left")

    by_code = comparison.set_index("_code")
    mesh["votos_2026"] = mesh["id"].map(by_code["votos_2026"]).fillna(0)
    mesh["votos_referencia"] = mesh["id"].map(by_code["votos_referencia"])
    mesh["diff_pp"] = mesh["id"].map(by_code["diff_pp"])
    epsilon = 1e-9
    mesh["classe_diff"] = 0
    mesh.loc[mesh["diff_pp"].lt(-epsilon), "classe_diff"] = 1
    mesh.loc[mesh["diff_pp"].abs().le(epsilon), "classe_diff"] = 2
    mesh.loc[mesh["diff_pp"].gt(epsilon), "classe_diff"] = 3

    def format_votes(value: object) -> str:
        if pd.isna(value):
            return "Sem dados"
        return f"{int(round(float(value))):,}".replace(",", ".")

    def format_diff(value: object) -> str:
        if pd.isna(value):
            return "Sem comparação disponível"
        numeric = float(value)
        if abs(numeric) <= epsilon:
            return "Sem variação (0,00 p.p.)"
        direction = "Ganho" if numeric > 0 else "Perda"
        return f"{direction} de {abs(numeric):.2f} p.p.".replace(".", ",", 1)

    mesh["bairro_hover"] = mesh["_mesh_name"].fillna("").astype(str).str.strip()
    mesh.loc[mesh["bairro_hover"].eq(""), "bairro_hover"] = "Bairro sem nome disponível"
    mesh["votos_referencia_label"] = mesh["votos_referencia"].map(format_votes)
    mesh["votos_2026_label"] = mesh["votos_2026"].map(format_votes)
    mesh["diff_label"] = mesh["diff_pp"].map(format_diff)
    customdata = mesh[[
        "bairro_hover", "votos_referencia_label", "votos_2026_label", "diff_label",
    ]].to_numpy()
    colorscale = [
        [0.00, "#94a3b8"], [0.25, "#94a3b8"],
        [0.2501, "#ef4444"], [0.50, "#ef4444"],
        [0.5001, "#3b82f6"], [0.75, "#3b82f6"],
        [0.7501, "#22c55e"], [1.00, "#22c55e"],
    ]
    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=mesh["id"],
        z=mesh["classe_diff"],
        zmin=0,
        zmax=3,
        featureidkey="properties.id",
        colorscale=colorscale,
        showscale=False,
        marker_line_color="rgba(235,244,255,0.98)",
        marker_line_width=1.3,
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"Votos {year}: %{{customdata[1]}}<br>"
            "Votos 2026: %{customdata[2]}<br>"
            f"Diferença de participação (2026 vs {year}): %{{customdata[3]}}"
            "<extra></extra>"
        ),
    ))
    boundary_lon, boundary_lat = _boundary_coordinates(municipality_geometry)
    if boundary_lon and boundary_lat:
        fig.add_trace(go.Scattergeo(
            lon=boundary_lon,
            lat=boundary_lat,
            mode="lines",
            line={"color": "rgba(248,251,255,1)", "width": 3.2},
            hoverinfo="skip",
            showlegend=False,
        ))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        meta={"mesh_kind": kind, "comparison_year": year, "display_mode": "market_share_change"},
    )
    return fig, len(mesh)


def municipality_mesh_map(
    municipality_code: str,
    votes: pd.DataFrame | None,
    *,
    neutral: bool = False,
    comparison_year: str | int | None = None,
) -> tuple[go.Figure | None, int]:
    if comparison_year is not None:
        comparison_year = str(comparison_year)
        if comparison_year not in {"2020", "2024"}:
            return None, 0
    kind, mesh, code_column, label_column = municipality_mesh(municipality_code)
    mesh = mesh.dropna(subset=[code_column, "geometry"]).copy()
    mesh = mesh.loc[mesh["geometry"].map(lambda shape: not shape.is_empty)]
    mesh["id"] = mesh[code_column].astype("string")
    mesh = mesh.loc[mesh["id"].notna() & mesh["id"].ne("")].drop_duplicates("id")
    if mesh.empty:
        return None, 0

    # The municipality layer is the invariant geographic frame. The selected
    # neighborhood/weighted-area/sector mesh is only the interior subdivision;
    # its vote coverage must never determine whether the municipal boundary is
    # visible.
    municipality_geometry = _municipality_geometry(municipality_code)
    if kind == "setor" and municipality_geometry is not None and not municipality_geometry.is_empty:
        mesh["geometry"] = mesh["geometry"].map(
            lambda geometry: _plotly_polygon_geometry(geometry, municipality_geometry)
        )
        mesh = mesh.dropna(subset=["geometry"])
        mesh = mesh.loc[mesh["geometry"].map(lambda shape: not shape.is_empty)]
        if mesh.empty:
            return None, 0

    # Official neighborhood geometry carries its own name. The compact sector
    # geometry does not, so recover the corresponding IBGE neighborhood names
    # from the lightweight sector lookup when it is available.
    mesh["_mesh_name"] = ""
    if label_column in mesh.columns and label_column != code_column:
        mesh["_mesh_name"] = mesh[label_column].fillna("").astype(str).str.strip()
    if kind == "setor":
        try:
            lookup = load_sector_neighborhood_lookup()
            if {"cd_setor_censitario", "nome_bairro_ibge"}.issubset(lookup.columns):
                lookup = lookup.copy()
                lookup["_code"] = lookup["cd_setor_censitario"].astype("string")
                lookup["_name"] = lookup["nome_bairro_ibge"].fillna("").astype(str).str.strip()
                lookup = lookup.loc[lookup["_code"].ne("") & lookup["_name"].ne("")]
                names = lookup.groupby("_code")["_name"].apply(
                    lambda values: " / ".join(dict.fromkeys(values))
                )
                mesh["_mesh_name"] = mesh["id"].map(names).fillna(mesh["_mesh_name"])
        except Exception:
            # The map remains usable if the optional reference table is absent.
            pass
        mesh["_tse_neighborhoods"] = _sector_tse_neighborhood_names(
            mesh, municipality_code
        )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": row.id},
                "geometry": mapping(row.geometry.simplify(0.0001, preserve_topology=True)),
            }
            for row in mesh.itertuples(index=False)
        ],
    }

    if neutral:
        fig = go.Figure(go.Choropleth(
            geojson=geojson,
            locations=mesh["id"],
            z=np.zeros(len(mesh)),
            zmin=0,
            zmax=1,
            featureidkey="properties.id",
            colorscale=[[0, "#e8f1ff"], [1, "#e8f1ff"]],
            showscale=False,
            marker_line_color="rgba(197,221,255,0.86)",
            marker_line_width=0.65,
            hoverinfo="skip",
        ))
        boundary_lon, boundary_lat = _boundary_coordinates(municipality_geometry)
        if boundary_lon and boundary_lat:
            fig.add_trace(go.Scattergeo(
                lon=boundary_lon,
                lat=boundary_lat,
                mode="lines",
                line={"color": "rgba(248,251,255,0.98)", "width": 2.2},
                hoverinfo="skip",
                showlegend=False,
            ))
        fig.update_geos(
            fitbounds="locations",
            visible=False,
            projection_type="mercator",
            bgcolor="rgba(0,0,0,0)",
        )
        fig.update_layout(
            margin={"l": 0, "r": 0, "t": 0, "b": 0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#eaf2ff"},
            meta={"mesh_kind": kind, "display_mode": "neutral"},
        )
        return fig, len(mesh)

    vote_code = {
        "bairro": "cd_ibge_bairro",
        "area_ponderada": "cd_area_ponderada",
        "setor": "cd_setor_censitario",
    }[kind]
    required = {"cd_ibge_municipio", vote_code, "nm_bairro", "qt_votos"}
    if votes is None or not required.issubset(votes.columns):
        return None, 0
    rows = votes.loc[votes["cd_ibge_municipio"].astype("string").eq(str(municipality_code))].copy()
    rows["_code"] = rows[vote_code].astype("string")
    rows["_name"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
    rows["qt_votos"] = pd.to_numeric(rows["qt_votos"], errors="coerce").fillna(0)
    municipality_vote_total = float(rows["qt_votos"].sum())
    rows = _attach_coordinate_matches(rows, mesh)
    rows = rows.loc[rows["_code"].notna() & rows["_code"].ne("")].copy()
    if comparison_year is not None:
        return _municipality_comparison_map(
            mesh, geojson, municipality_geometry, kind, rows, comparison_year
        )
    by_neighborhood = rows.groupby(["_code", "_name"], as_index=False)["qt_votos"].sum()
    by_neighborhood["_name"] = by_neighborhood["_name"].replace("", "Bairro não informado")
    by_neighborhood = by_neighborhood.groupby(["_code", "_name"], as_index=False)["qt_votos"].sum()
    totals = by_neighborhood.groupby("_code")["qt_votos"].sum()
    details = by_neighborhood.groupby("_code").apply(
        lambda group: "<br>".join(
            f"{html.escape(str(name))}: {int(count):,} votos".replace(",", ".")
            for name, count in zip(group.sort_values("_name")["_name"], group.sort_values("_name")["qt_votos"])
        ),
        include_groups=False,
    ) if not by_neighborhood.empty else pd.Series(dtype=str)

    mesh["votes"] = mesh["id"].map(totals).fillna(0)
    matched_rows = rows.loc[rows["_code"].isin(mesh["id"]), "qt_votos"].sum()
    if not np.isclose(mesh["votes"].sum(), matched_rows):
        raise ValueError("A soma dos votos na malha diverge dos registros eleitorais associados.")
    mesh["details"] = mesh["id"].map(details).fillna("")
    def territory_details(row: pd.Series) -> str:
        if kind == "setor" and str(row.get("_tse_neighborhoods") or "").strip():
            tse_names = html.escape(str(row["_tse_neighborhoods"]))
            vote_details = row["details"] or "Sem votos do candidato"
            return f"<b>Bairros TSE de referência:</b> {tse_names}<br>{vote_details}"
        if row["details"]:
            return str(row["details"])
        if row["_mesh_name"]:
            return f"{html.escape(str(row['_mesh_name']))}: 0 votos"
        return "Sem votos associados"

    mesh["details"] = mesh.apply(territory_details, axis=1)
    mesh["total_label"] = mesh["votes"].map(lambda value: f"{int(value):,}".replace(",", "."))
    active_share = float(mesh["votes"].gt(0).mean())
    max_votes = float(mesh["votes"].max())
    # A sector mesh can contain hundreds of polygons while the electoral file
    # has one row per named bairro/local. Penalizing the colors by sector
    # coverage makes legitimate votes practically indistinguishable from zero.
    # Keep the coverage factor for the coarser meshes, but use the full local
    # color range when sectors are the geographic fallback.
    coverage_factor = 1.0 if kind == "setor" else np.sqrt(active_share)
    use_uniform_color = 0 < municipality_vote_total < 1_000
    use_log_scale = municipality_vote_total > 5_000
    if max_votes <= 0:
        relative_intensity = 0.0
    elif use_uniform_color:
        relative_intensity = np.ones(len(mesh))
    elif use_log_scale:
        relative_intensity = np.log1p(mesh["votes"]) / np.log1p(max_votes)
    else:
        relative_intensity = mesh["votes"] / max_votes
    mesh["color_intensity"] = (
        relative_intensity
        if use_uniform_color
        else relative_intensity * coverage_factor
    )
    colorscale = (
        [[0, "#2563eb"], [1, "#2563eb"]]
        if use_uniform_color
        else [
            [0, "#e8f1ff"], [0.25, "#bfd9ff"], [0.5, "#60a5fa"],
            [0.75, "#2563eb"], [1, "#0b1f4d"],
        ]
    )
    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=mesh["id"],
        z=mesh["color_intensity"],
        zmin=0,
        zmax=1,
        featureidkey="properties.id",
        colorscale=colorscale,
        showscale=False,
        marker_line_color="rgba(235,244,255,0.98)",
        marker_line_width=1.3,
        customdata=mesh[["total_label", "details"]],
        hovertemplate="<b>Total de votos: %{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
    ))
    boundary_lon, boundary_lat = _boundary_coordinates(municipality_geometry)
    if boundary_lon and boundary_lat:
        fig.add_trace(go.Scattergeo(
            lon=boundary_lon,
            lat=boundary_lat,
            mode="lines",
            line={"color": "rgba(248,251,255,1)", "width": 3.2},
            hoverinfo="skip",
            showlegend=False,
        ))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        meta={
            "mesh_kind": kind,
            "scale_type": (
                "uniform"
                if use_uniform_color
                else "logarithmic" if use_log_scale else "linear"
            ),
            "municipality_vote_total": municipality_vote_total,
        },
    )
    return fig, len(mesh)


def municipality_neighborhood_category_map(
    municipality_code: str,
    categories: pd.DataFrame | None,
) -> tuple[go.Figure | None, int]:
    """Render BH neighborhoods using strategic category colors."""
    required = {
        "cd_ibge_municipio",
        "cd_ibge_bairro",
        "nm_bairro",
        "categoria_projecao_2028",
    }
    if categories is None or categories.empty or not required.issubset(categories.columns):
        return None, 0

    kind, mesh, code_column, label_column = municipality_mesh(municipality_code)
    if kind != "bairro":
        return None, 0
    mesh = mesh.dropna(subset=[code_column, "geometry"]).copy()
    mesh = mesh.loc[mesh["geometry"].map(lambda shape: not shape.is_empty)]
    mesh["id"] = mesh[code_column].astype("string")
    mesh = mesh.loc[mesh["id"].notna() & mesh["id"].ne("")].drop_duplicates("id")
    if mesh.empty:
        return None, 0

    municipality_geometry = _municipality_geometry(municipality_code)
    mesh["_mesh_name"] = ""
    if label_column in mesh.columns and label_column != code_column:
        mesh["_mesh_name"] = mesh[label_column].fillna("").astype(str).str.strip()

    rows = categories.loc[
        categories["cd_ibge_municipio"].astype("string").eq(str(municipality_code))
    ].copy()
    rows["_code"] = rows["cd_ibge_bairro"].astype("string")
    rows["_name"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
    rows["_category"] = rows["categoria_projecao_2028"].fillna("Demais bairros").astype(str)
    rows = _attach_coordinate_matches(rows, mesh)
    rows = rows.loc[rows["_code"].notna() & rows["_code"].isin(mesh["id"])].copy()
    if rows.empty:
        return None, 0

    category_priority = {
        "Demais bairros": 0,
        "Oportunidade BH": 1,
        "Vulnerável/Ameaçado": 2,
        "Base Crítica (Fortaleza)": 3,
    }
    rows["_priority"] = rows["_category"].map(category_priority).fillna(0)
    category_by_code = (
        rows.sort_values("_priority")
        .drop_duplicates("_code", keep="last")
        .set_index("_code")["_category"]
    )
    mesh["_category"] = mesh["id"].map(category_by_code).fillna("Demais bairros")

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": row.id},
                "geometry": mapping(row.geometry.simplify(0.0001, preserve_topology=True)),
            }
            for row in mesh.itertuples(index=False)
        ],
    }
    fig = go.Figure()
    for category, color in BH_PROJECTION_CATEGORY_COLORS.items():
        selected = mesh.loc[mesh["_category"].eq(category)]
        if selected.empty:
            continue
        fig.add_trace(go.Choropleth(
            geojson=geojson,
            locations=selected["id"],
            z=np.ones(len(selected)),
            zmin=0,
            zmax=1,
            featureidkey="properties.id",
            colorscale=[[0, color], [1, color]],
            showscale=False,
            marker_line_color="rgba(235,244,255,0.98)",
            marker_line_width=1.3,
            customdata=selected[["_mesh_name"]].assign(
                category=selected["_category"]
            ).to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>",
            showlegend=False,
        ))

    boundary_lon, boundary_lat = _boundary_coordinates(municipality_geometry)
    if boundary_lon and boundary_lat:
        fig.add_trace(go.Scattergeo(
            lon=boundary_lon,
            lat=boundary_lat,
            mode="lines",
            line={"color": "rgba(248,251,255,1)", "width": 3.2},
            hoverinfo="skip",
            showlegend=False,
        ))
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        projection_type="mercator",
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        meta={"mesh_kind": kind, "display_mode": "category_projection_2028"},
    )
    return fig, len(mesh)
