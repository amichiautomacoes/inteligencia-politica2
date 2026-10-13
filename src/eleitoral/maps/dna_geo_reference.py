import unicodedata

import json
import pandas as pd
import pyarrow.parquet as pq
import streamlit as st
from pyproj import CRS, Transformer
from shapely import wkb
from shapely.geometry import mapping
from shapely.ops import transform, unary_union

from hf_sync import hf_filesystem, load_env


GEOGRAPHY_FILES = {
    "municipio": "MG_municipios_2022.parquet",
    "mesorregiao": "MG_mesorregioes_2022.parquet",
    "bairro": "MG_bairros_CD2022.parquet",
    "setor": "MG_setores_mapa_CD2022.parquet",
}

GEOGRAPHY_COLUMNS = {
    "municipio": ["code_muni", "name_muni", "geometry"],
    "mesorregiao": ["name_meso", "geometry"],
    "bairro": ["code_muni", "code_neighborhood", "name_neighborhood", "geometry"],
    "setor": ["code_tract", "code_muni", "geometry"],
}

MUNICIPAL_GEOMETRY_TOLERANCE = 0.002

CROSSWALK_FILES = {
    "setor": "crosswalk_setor_bairro.parquet",
}


def territorial_codes(values: pd.Series) -> pd.Series:
    """Preserve textual TSE keys and remove numeric Parquet's decimal suffix."""
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


@st.cache_data(show_spinner=False)
def load_crosswalk_geometry(kind: str) -> pd.DataFrame:
    env = load_env()
    frame = _read_geo_parquet(
        geography_reference_path(env, CROSSWALK_FILES[kind]),
        columns=["cd_ibge_municipio", "cd_bairro", "id_unidade", "nm_bairro", "geometry"],
    )
    for column in ("cd_ibge_municipio", "cd_bairro", "id_unidade"):
        frame[column] = territorial_codes(frame[column])
    return frame


def crosswalk_mesh(kind: str, municipality_code: str | None = None) -> pd.DataFrame:
    """One polygon per unit, even when several TSE neighborhoods share it."""
    frame = load_crosswalk_geometry(kind)
    if municipality_code is not None:
        frame = frame.loc[frame["cd_ibge_municipio"].eq(str(municipality_code))]
    frame = frame.dropna(subset=["id_unidade", "geometry"])
    frame = frame.loc[frame["geometry"].map(lambda shape: not shape.is_empty)]
    code_column = "code_tract"
    return frame.drop_duplicates(["cd_ibge_municipio", "id_unidade"]).rename(
        columns={"cd_ibge_municipio": "code_muni", "id_unidade": code_column}
    ).reset_index(drop=True)


def attach_crosswalk_units(rows: pd.DataFrame, kind: str, municipality_code: str) -> pd.DataFrame:
    """Join candidate records by TSE neighborhood, without spatial guesses."""
    links = load_crosswalk_geometry(kind)
    links = links.loc[links["cd_ibge_municipio"].eq(str(municipality_code))]
    links = links.dropna(subset=["cd_bairro", "id_unidade", "geometry"])
    links = links[["cd_bairro", "id_unidade"]].drop_duplicates()
    # An ambiguous neighborhood must not multiply its electoral totals.
    links = links.loc[~links["cd_bairro"].duplicated(keep=False)]
    result = rows.copy()
    result["cd_bairro"] = territorial_codes(result["cd_bairro"])
    units = links.set_index("cd_bairro")["id_unidade"]
    result["_code"] = result["cd_bairro"].map(units)
    return result


def geography_path(env: dict[str, str], filename: str) -> str:
    prefix = env.get("HF_GEOGRAPHY_PREFIX", "IBGE/malha_mapas").strip("/")
    return f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}/{filename}"


def geography_reference_path(env: dict[str, str], filename: str) -> str:
    prefix = env.get("HF_GEOGRAPHY_REFERENCE_PREFIX", "IBGE/MG/dadosterritorio").strip("/")
    return f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}/{filename}"


@st.cache_data(show_spinner=False)
def load_sector_neighborhood_lookup() -> pd.DataFrame:
    """Read the compact sector-to-neighborhood index, without geometries."""
    env = load_env()
    path = geography_reference_path(env, "setor_bairro_lookup.parquet")
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        return pd.read_parquet(source)


@st.cache_data(show_spinner=False)
def load_tse_neighborhood_sector_crosswalk() -> pd.DataFrame:
    """Read TSE neighborhoods and their census-sector reference points."""
    env = load_env()
    path = geography_reference_path(env, "crosswalk_setor_bairro.parquet")
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        return pd.read_parquet(
            source,
            columns=[
                "cd_ibge_municipio",
                "id_unidade",
                "nm_bairro",
                "nm_bairro_atribuido",
            ],
        )


@st.cache_data(show_spinner=False)
def load_sector_ibge_crosswalk() -> pd.DataFrame:
    """Exact sector keys and IBGE neighborhood attributes from the crosswalk."""
    env = load_env()
    path = geography_reference_path(env, "crosswalk_setor_bairro.parquet")
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        return pd.read_parquet(source, columns=[
            "id_unidade", "ibge_codigo_bairro_do_ponto", "ibge_bairro_do_ponto",
        ])


@st.cache_data(show_spinner=False)
def load_area_ponderada_bairro_crosswalk() -> pd.DataFrame:
    """Map TSE reference neighborhoods to their weighted Census area."""
    env = load_env()
    path = geography_reference_path(env, "crosswalk_area_ponderada_bairro.parquet")
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        return pd.read_parquet(
            source,
            columns=["cd_ibge_municipio", "id_unidade", "nm_bairro", "id_bairro_tse"],
        )


def _read_geo_parquet(
    path: str, *, columns: list[str], filters: list[tuple] | None = None
) -> pd.DataFrame:
    """Read GeoParquet with pandas and decode its WKB geometry for Plotly."""
    env = load_env()
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        metadata = pq.read_metadata(source).metadata or {}
        geo_metadata = json.loads(metadata.get(b"geo", b"{}"))
        geometry_column = geo_metadata.get("primary_column", "geometry")
        crs_value = geo_metadata.get("columns", {}).get(geometry_column, {}).get("crs")
        if not crs_value:
            raise ValueError(f"A malha {path} não informa o sistema de coordenadas.")
        source.seek(0)
        layer = pd.read_parquet(source, columns=columns, filters=filters)
    source_crs = CRS.from_user_input(crs_value)
    target_crs = CRS.from_epsg(4326)
    transformer = None if source_crs == target_crs else Transformer.from_crs(source_crs, target_crs, always_xy=True)
    layer[geometry_column] = layer[geometry_column].map(
        lambda value: (
            transform(transformer.transform, wkb.loads(value)) if transformer is not None else wkb.loads(value)
        ) if pd.notna(value) else None
    )
    return layer


@st.cache_data(show_spinner=False)
def load_complete_municipality_sectors(municipality_code: str) -> pd.DataFrame:
    """Complete IBGE sector coverage, including units absent from the crosswalk."""
    env = load_env()
    return _read_geo_parquet(
        geography_path(env, GEOGRAPHY_FILES["setor"]),
        columns=GEOGRAPHY_COLUMNS["setor"],
        filters=[("code_muni", "==", str(municipality_code))],
    )


@st.cache_data(show_spinner=False)
def load_municipality_sectors(municipality_code: str) -> pd.DataFrame:
    """Complete IBGE mesh, retaining crosswalk geometry for linked sectors."""
    sectors = load_complete_municipality_sectors(municipality_code).copy()
    sectors["code_tract"] = territorial_codes(sectors["code_tract"])
    linked = crosswalk_mesh("setor", municipality_code).set_index("code_tract")["geometry"]
    sectors["geometry"] = sectors.apply(lambda row: linked.get(row["code_tract"], row["geometry"]), axis=1)
    return sectors.drop_duplicates("code_tract")


@st.cache_data(show_spinner=False)
def load_geo_layer(granularity: str) -> pd.DataFrame:
    """Read an official IBGE GeoParquet with pandas in EPSG:4326."""
    if granularity not in GEOGRAPHY_FILES:
        raise ValueError(f"Granularidade geogrÃ¡fica desconhecida: {granularity}")
    if granularity in CROSSWALK_FILES:
        return crosswalk_mesh(granularity)
    env = load_env()
    bucket_url = env.get("HF_BUCKET_URL", "").rstrip("/")
    if not bucket_url:
        raise RuntimeError("HF_BUCKET_URL nÃ£o foi configurado.")
    path = geography_path(env, GEOGRAPHY_FILES[granularity])
    return _read_geo_parquet(path, columns=GEOGRAPHY_COLUMNS[granularity])


@st.cache_data(show_spinner=False)
def load_geo_reference() -> tuple[dict | None, pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    env = load_env()
    bucket_url = env.get("HF_BUCKET_URL", "").rstrip("/")
    if not bucket_url:
        return None, None, None, None

    fs = hf_filesystem(env.get("HF_TOKEN"))
    try:
        municipalities = load_geo_layer("municipio")[["code_muni", "name_muni", "geometry"]]
        mesoregions = load_geo_layer("mesorregiao")[["name_meso", "geometry"]]
        with fs.open(geography_reference_path(env, "municipios_mg_mesorregioes.parquet"), "rb") as source:
            reference = pd.read_parquet(source)
    except Exception as exc:
        st.warning(
            "Não foi possível carregar a malha municipal de MG. "
            f"Prefixo das malhas: {env.get('HF_GEOGRAPHY_PREFIX', 'IBGE/malha_mapas')}. "
            f"Prefixo das referências: {env.get('HF_GEOGRAPHY_REFERENCE_PREFIX', 'IBGE/MG/dadosterritorio')}. "
            f"Detalhe: {exc}"
        )
        return None, None, None, None

    municipalities["codigo_ibge"] = municipalities["code_muni"].astype("string")
    municipalities = municipalities.dropna(subset=["codigo_ibge", "geometry"])
    features = []
    coordinates = []
    for row in municipalities.itertuples(index=False):
        geometry = row.geometry
        municipality_id = str(row.codigo_ibge)
        features.append({
            "type": "Feature",
            "properties": {"id": municipality_id},
            "geometry": mapping(geometry.simplify(MUNICIPAL_GEOMETRY_TOLERANCE, preserve_topology=True)),
        })
        point = geometry.representative_point()
        coordinates.append((str(row.codigo_ibge), row.name_muni, point.y, point.x))
    region_geometries = list(mesoregions.geometry.dropna())
    mesoregion_centers = []
    mesoregion_features = []
    for row in mesoregions.itertuples(index=False):
        if row.geometry is None or row.geometry.is_empty:
            continue
        mesoregion_features.append({
            "type": "Feature",
            "properties": {"id": str(row.name_meso)},
            "geometry": mapping(row.geometry.simplify(MUNICIPAL_GEOMETRY_TOLERANCE, preserve_topology=True)),
        })
        point = row.geometry.representative_point()
        mesoregion_centers.append({
            "name": str(row.name_meso), "lon": float(point.x), "lat": float(point.y),
        })
    geojson_mg = {
        "type": "FeatureCollection",
        "features": features,
        "mesoregions": {"type": "FeatureCollection", "features": mesoregion_features},
        "regional_lines": {
            "mesoregions": _boundary_coordinates([geometry.boundary for geometry in region_geometries]),
            "state": _boundary_coordinates([unary_union(region_geometries).boundary]),
        },
        "mesoregion_centers": mesoregion_centers,
    }

    df_municipios = pd.DataFrame(coordinates, columns=["codigo_ibge", "nome", "latitude", "longitude"])
    df_municipios["codigo_ibge"] = df_municipios["codigo_ibge"].astype("string")

    reference["codigo_ibge"] = reference["codigo_ibge"].astype("string")
    reference["codigo_tse"] = reference["codigo_tse"].astype("string")
    df_tse = reference[["codigo_tse", "codigo_ibge", "nm_municipio_ibge"]].rename(
        columns={"nm_municipio_ibge": "nome_municipio"}
    ).copy()
    df_tse["municipio_norm"] = df_tse["nome_municipio"].map(normalize_municipio_name)

    df_regioes = reference[["codigo_ibge", "nm_municipio_ibge", "nm_mesorregiao"]].rename(
        columns={"nm_municipio_ibge": "municipio_ibge_nome", "nm_mesorregiao": "mesorregiao_nome"}
    ).copy()
    df_regioes["regiao_imediata_nome"] = ""
    return geojson_mg, df_tse, df_municipios, df_regioes


def normalize_municipio_name(value: object) -> str:
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def _boundary_coordinates(boundaries: list) -> tuple[list[float | None], list[float | None]]:
    lon: list[float | None] = []
    lat: list[float | None] = []
    for boundary in boundaries:
        simplified = boundary.simplify(0.002, preserve_topology=True)
        parts = simplified.geoms if hasattr(simplified, "geoms") else [simplified]
        for part in parts:
            for x, y in part.coords:
                lon.append(float(x))
                lat.append(float(y))
            lon.append(None)
            lat.append(None)
    return lon, lat

