"""Cruza a malha de bairros de MG com os votos territoriais no HF."""

from pathlib import Path
import re
import unicodedata

import geopandas as gpd
import pandas as pd

from hf_sync import hf_filesystem, hf_visualizacao_path, load_env


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "geopedia_mg"
VOTE_COLUMNS = [
    "cd_ibge_municipio", "cd_setor_censitario", "cd_bairro", "nm_bairro",
    "qt_votos", "nr_latitude", "nr_longitude",
]


def normalized(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).upper())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def code_strings(series: pd.Series) -> pd.Series:
    return series.astype("string")


def main() -> None:
    mesh = gpd.read_parquet(OUT / "malha_bairros_completa.parquet")
    mesh["bairro_norm"] = mesh["bairro"].map(normalized)
    cities = set(mesh["codigo_municipio_ibge"])
    official = mesh[["codigo_municipio_ibge", "codigo_bairro_ibge"]].drop_duplicates()
    official_keys = set(map(tuple, official.itertuples(index=False, name=None)))
    official_names = mesh[["codigo_municipio_ibge", "bairro_norm", "codigo_bairro_ibge"]].drop_duplicates()
    official_names = official_names[~official_names.duplicated(["codigo_municipio_ibge", "bairro_norm"], keep=False)]
    name_lookup = official_names.set_index(["codigo_municipio_ibge", "bairro_norm"])["codigo_bairro_ibge"]

    env = load_env(ROOT / ".env")
    fs = hf_filesystem(env.get("HF_TOKEN"))
    prefix = env.get("HF_GEOGRAPHY_REFERENCE_PREFIX", "IBGE/MG/dadosterritorio").strip("/")
    sector_path = f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}/MG_setores_CD2022.parquet"
    with fs.open(sector_path, "rb") as source:
        sectors = pd.read_parquet(source, columns=["code_tract", "code_muni", "code_neighborhood"])
    sectors = sectors.drop_duplicates("code_tract")
    sectors["cd_setor_censitario"] = code_strings(sectors["code_tract"])
    sectors["setor_municipio"] = code_strings(sectors["code_muni"])
    sectors["bairro_setor"] = code_strings(sectors["code_neighborhood"])

    paths = sorted(path for path in fs.find(hf_visualizacao_path(env)) if path.endswith("territorio/stage01b_bairros.parquet"))
    frames = []
    for path in paths:
        with fs.open(path, "rb") as source:
            frame = pd.read_parquet(source, columns=VOTE_COLUMNS)
        frame["candidato"] = path.split("/")[-3]
        frames.append(frame)
    votes = pd.concat(frames, ignore_index=True)
    votes = votes[votes["cd_ibge_municipio"].isin(cities)].copy().reset_index(drop=True)
    votes["registro"] = votes.index
    votes["qt_votos"] = pd.to_numeric(votes["qt_votos"], errors="coerce").fillna(0)
    votes = votes.merge(
        sectors[["cd_setor_censitario", "setor_municipio", "bairro_setor"]],
        on="cd_setor_censitario", how="left", validate="many_to_one",
    )
    sector_ok = [
        (mun, bairro) in official_keys and mun == sector_mun
        for mun, bairro, sector_mun in zip(votes["cd_ibge_municipio"], votes["bairro_setor"], votes["setor_municipio"])
    ]
    votes["metodo_match"] = "sem_correspondencia"
    votes["codigo_bairro_malha"] = pd.NA
    votes.loc[sector_ok, "metodo_match"] = "setor"
    votes.loc[sector_ok, "codigo_bairro_malha"] = votes.loc[sector_ok, "bairro_setor"]

    # O identificador eleitoral preserva o nome sem acentos mesmo quando o campo nm_bairro tem codificação ruim.
    votes["bairro_eleitoral"] = votes["cd_bairro"].fillna("").str.extract(r"_BAIRRO:(.*)$", expand=False)
    votes["bairro_eleitoral"] = votes["bairro_eleitoral"].fillna(votes["nm_bairro"])
    votes["bairro_norm"] = votes["bairro_eleitoral"].map(normalized)
    remaining = votes["metodo_match"].eq("sem_correspondencia") & votes["bairro_norm"].ne("")
    for idx in votes.index[remaining]:
        key = (votes.at[idx, "cd_ibge_municipio"], votes.at[idx, "bairro_norm"])
        if key in name_lookup.index:
            votes.at[idx, "metodo_match"] = "nome"
            votes.at[idx, "codigo_bairro_malha"] = name_lookup[key]

    remaining = votes["metodo_match"].eq("sem_correspondencia")
    valid_coords = (
        remaining & pd.to_numeric(votes["nr_latitude"], errors="coerce").between(-23, -14)
        & pd.to_numeric(votes["nr_longitude"], errors="coerce").between(-52, -39)
    )
    if valid_coords.any():
        points = gpd.GeoDataFrame(
            votes.loc[valid_coords, ["registro", "cd_ibge_municipio"]].copy(),
            geometry=gpd.points_from_xy(votes.loc[valid_coords, "nr_longitude"], votes.loc[valid_coords, "nr_latitude"]),
            crs="EPSG:4326",
        ).to_crs(mesh.crs)
        spatial = gpd.sjoin(
            points,
            mesh[["codigo_municipio_ibge", "codigo_bairro_ibge", "geometry"]],
            how="inner", predicate="within",
        )
        spatial = spatial[
            spatial["cd_ibge_municipio"].eq(spatial["codigo_municipio_ibge"])
        ].drop_duplicates("registro")
        found = spatial.set_index("registro")["codigo_bairro_ibge"]
        votes.loc[found.index, "metodo_match"] = "ponto"
        votes.loc[found.index, "codigo_bairro_malha"] = found

    keys = ["candidato", "cd_ibge_municipio"]
    vote_totals = votes.groupby(keys).agg(
        registros=("registro", "size"), votos=("qt_votos", "sum"),
        bairros_eleitorais=("cd_bairro", "nunique"),
    )
    matched = votes[votes["metodo_match"].ne("sem_correspondencia")].groupby(keys).agg(
        registros_cobertos=("registro", "size"), votos_cobertos=("qt_votos", "sum"),
        bairros_eleitorais_cobertos=("cd_bairro", "nunique"),
    )
    summary = vote_totals.join(matched).fillna(0).reset_index()
    summary["pct_votos_cobertos"] = 100 * summary["votos_cobertos"] / summary["votos"]
    summary["todos_registros_cobertos"] = summary["registros_cobertos"].eq(summary["registros"])
    names = mesh[["codigo_municipio_ibge", "municipio"]].drop_duplicates()
    summary = summary.merge(names, left_on="cd_ibge_municipio", right_on="codigo_municipio_ibge", how="left")
    summary = summary.drop(columns="codigo_municipio_ibge")

    OUT.mkdir(parents=True, exist_ok=True)
    votes.drop(columns=["nr_latitude", "nr_longitude"]).to_parquet(OUT / "auditoria_votos_bairros.parquet", index=False)
    summary.to_parquet(OUT / "cobertura_votacao_por_municipio.parquet", index=False)
    print("Arquivos territoriais:", len(paths), "| municípios da malha com votos:", votes["cd_ibge_municipio"].nunique())
    print("Registros:", len(votes), "| votos:", int(votes["qt_votos"].sum()))
    print(votes.groupby("metodo_match").agg(registros=("registro", "size"), votos=("qt_votos", "sum")).to_string())
    print("Pares candidato-município com todos os registros cobertos:", int(summary["todos_registros_cobertos"].sum()), "/", len(summary))
    print("Bairros eleitorais distintos sem correspondência:", votes.loc[votes["metodo_match"].eq("sem_correspondencia"), "cd_bairro"].nunique())
    print("Saída:", OUT)


if __name__ == "__main__":
    main()
