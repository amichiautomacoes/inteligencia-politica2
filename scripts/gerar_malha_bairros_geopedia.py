"""Confere os bairros oficiais de MG e exporta a cobertura e a malha."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from hf_sync import hf_filesystem, load_env


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "MG_bairros_CD2022.zip"
OUTPUT = ROOT / "data" / "geopedia_mg"


def code_strings(series: pd.Series) -> pd.Series:
    return series.astype("string")


def main() -> None:
    # O DBF usa caracteres CP1252, embora o arquivo .cpg declare UTF-8.
    neighborhoods = gpd.read_file(f"zip://{SOURCE}", encoding="cp1252")
    neighborhoods = neighborhoods.rename(columns={
        "CD_MUN": "codigo_municipio_ibge",
        "NM_MUN": "municipio",
        "CD_BAIRRO": "codigo_bairro_ibge",
        "NM_BAIRRO": "bairro",
    })
    neighborhoods = neighborhoods[
        ["codigo_municipio_ibge", "municipio", "codigo_bairro_ibge", "bairro", "geometry"]
    ].copy()
    if neighborhoods.crs is None or neighborhoods.geometry.isna().any() or not neighborhoods.is_valid.all():
        raise ValueError("O ZIP contém geometrias inválidas ou sem CRS.")
    if neighborhoods.duplicated("codigo_bairro_ibge").any():
        raise ValueError("O ZIP contém códigos de bairro duplicados.")

    env = load_env(ROOT / ".env")
    prefix = env.get("HF_GEOGRAPHY_REFERENCE_PREFIX", "IBGE/MG/dadosterritorio").strip("/")
    remote = f"{env['HF_BUCKET_URL'].rstrip('/')}/{prefix}/MG_setores_CD2022.parquet"
    with hf_filesystem(env.get("HF_TOKEN")).open(remote, "rb") as source:
        sectors = pd.read_parquet(source, columns=["code_tract", "code_muni", "code_neighborhood"])
    sectors = sectors.drop_duplicates("code_tract")
    sectors["codigo_municipio_ibge"] = code_strings(sectors["code_muni"])
    sectors["codigo_bairro_ibge"] = code_strings(sectors["code_neighborhood"])
    official = sectors.loc[
        sectors["codigo_bairro_ibge"].ne("<NA>"),
        ["codigo_municipio_ibge", "codigo_bairro_ibge"],
    ].drop_duplicates()
    official = official[official["codigo_municipio_ibge"].isin(neighborhoods["codigo_municipio_ibge"])]
    mapped = neighborhoods[["codigo_municipio_ibge", "codigo_bairro_ibge"]].drop_duplicates()
    check = official.merge(mapped, on=["codigo_municipio_ibge", "codigo_bairro_ibge"], how="left", indicator=True)
    coverage = official.groupby("codigo_municipio_ibge").size().rename("bairros_oficiais")
    coverage = coverage.to_frame().join(
        check[check["_merge"].eq("both")].groupby("codigo_municipio_ibge").size().rename("bairros_com_poligono")
    ).fillna({"bairros_com_poligono": 0})
    coverage["bairros_com_poligono"] = coverage["bairros_com_poligono"].astype(int)
    coverage["cobertura_pct"] = 100 * coverage["bairros_com_poligono"] / coverage["bairros_oficiais"]
    coverage["malha_completa"] = coverage["bairros_com_poligono"].eq(coverage["bairros_oficiais"])
    names = neighborhoods[["codigo_municipio_ibge", "municipio"]].drop_duplicates().set_index("codigo_municipio_ibge")
    coverage = coverage.join(names).reset_index()
    coverage = coverage[[
        "codigo_municipio_ibge", "municipio", "bairros_oficiais", "bairros_com_poligono",
        "cobertura_pct", "malha_completa",
    ]].sort_values("municipio")
    if not coverage["malha_completa"].all() or len(coverage) != neighborhoods["codigo_municipio_ibge"].nunique():
        raise ValueError("Há municípios com bairros oficiais sem polígono no ZIP.")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    coverage.to_parquet(OUTPUT / "cobertura_municipios.parquet", index=False)
    neighborhoods.to_parquet(OUTPUT / "malha_bairros_completa.parquet", index=False)
    print(f"Municípios com malha completa: {len(coverage)}")
    print(f"Bairros com polígono: {len(neighborhoods)}")
    print(f"Saída: {OUTPUT}")


if __name__ == "__main__":
    main()
