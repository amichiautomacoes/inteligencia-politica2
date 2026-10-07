"""Prepare compact, municipality-filterable sector polygons for Deck.gl."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from hf_sync import hf_filesystem, load_env


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "geopedia_mg" / "MG_setores_mapa_CD2022.parquet"


def main() -> None:
    env = load_env(ROOT / ".env")
    prefix = env.get("HF_GEOGRAPHY_REFERENCE_PREFIX", "IBGE/MG/dadosterritorio").strip("/")
    path = f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}/MG_setores_CD2022.parquet"
    with hf_filesystem(env.get("HF_TOKEN")).open(path, "rb") as source:
        sectors = gpd.read_parquet(source, columns=["code_tract", "code_muni", "code_neighborhood", "name_neighborhood", "geometry"])
    sectors = sectors.drop_duplicates("code_tract")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    lookup = pd.DataFrame({
        "cd_setor_censitario": sectors["code_tract"].astype("string"),
        "codigo_bairro_ibge": sectors["code_neighborhood"].astype("string"),
        "nome_bairro_ibge": sectors["name_neighborhood"].fillna("").astype(str).str.strip(),
    })
    lookup.to_parquet(OUTPUT.parent / "setor_bairro_lookup.parquet", index=False)
    sectors = sectors.drop(columns=["code_neighborhood", "name_neighborhood"])
    sectors["code_muni"] = sectors["code_muni"].astype("string")
    sectors["code_tract"] = sectors["code_tract"].astype("string")
    sectors = sectors.dropna(subset=["code_muni", "code_tract", "geometry"])
    sectors = sectors.sort_values(["code_muni", "code_tract"]).reset_index(drop=True)
    sectors["geometry"] = sectors.geometry.simplify(0.0001, preserve_topology=True)
    sectors.to_parquet(OUTPUT, index=False, row_group_size=100, compression="zstd")
    print("Sectors:", len(sectors), "bytes:", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
