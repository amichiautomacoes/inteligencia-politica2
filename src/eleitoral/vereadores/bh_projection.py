"""Classificação de bairros de BH por votação e espaço demográfico relativo."""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd


def _normalized_name(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(
        "".join(c for c in unicodedata.normalize("NFKD", str(value)) if not unicodedata.combining(c))
        .upper().split()
    )


def bh_projection_map_frame(
    potential: pd.DataFrame | None,
    reference: pd.DataFrame | None,
) -> pd.DataFrame:
    """Use each demographic dimension once; repeated votes are never summed.

    A negative mean (ICP minus population, in percentage points) indicates
    demographic space. It is a descriptive index, not an individual joint
    distribution, trend, causal risk measure or prediction of future votes.
    """
    columns = [
        "cd_ibge_municipio", "cd_ibge_bairro", "nm_bairro",
        "categoria_projecao_2028", "nr_latitude", "nr_longitude", "projection_detail",
    ]
    required = {
        "cd_bairro", "nm_bairro", "dimensao", "qt_votos_candidato_bairro",
        "pct_icp_categoria", "pct_populacao_categoria",
    }
    if (
        potential is None or potential.empty or not required.issubset(potential.columns)
        or reference is None
        or not {"cd_ibge_municipio", "cd_ibge_bairro", "nm_bairro"}.issubset(reference.columns)
    ):
        return pd.DataFrame(columns=columns)

    data = potential.copy()
    # The source uses TSE code 41238; geographic rendering uses IBGE 3106200.
    if "cd_municipio" in data:
        data = data.loc[data["cd_municipio"].astype("string").isin(["41238", "3106200"])].copy()
    data = data.loc[data["cd_bairro"].notna()].copy()
    if data.empty:
        return pd.DataFrame(columns=columns)
    data["cd_bairro"] = data["cd_bairro"].astype("string")
    for name in ("qt_votos_candidato_bairro", "pct_icp_categoria", "pct_populacao_categoria"):
        data[name] = pd.to_numeric(data[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
    data["dimensao"] = data["dimensao"].map(_normalized_name)
    valid = (
        data["pct_icp_categoria"].between(0, 100)
        & data["pct_populacao_categoria"].between(0, 100)
    )
    if "situacao_icp" in data:
        valid &= data["situacao_icp"].eq("calculado")
    data["_gap"] = (data["pct_icp_categoria"] - data["pct_populacao_categoria"]).where(valid)
    dimensions = ["GENERO", "IDADE", "ESCOLARIDADE"]
    gaps = data.loc[data["dimensao"].isin(dimensions)].pivot_table(
        index="cd_bairro", columns="dimensao", values="_gap", aggfunc="mean"
    ).reindex(columns=dimensions)
    neighborhoods = data.groupby("cd_bairro", as_index=False).agg(
        nm_bairro=("nm_bairro", "first"),
        votes=("qt_votos_candidato_bairro", "max"),
    ).set_index("cd_bairro")
    neighborhoods["gap"] = gaps.mean(axis=1).where(gaps.notna().all(axis=1))
    positive_votes = neighborhoods.loc[neighborhoods["votes"].gt(0), "votes"]
    threshold = float(positive_votes.median()) if not positive_votes.empty else np.nan
    complete = neighborhoods["gap"].notna() & neighborhoods["votes"].ge(0) & pd.notna(threshold)
    strong = neighborhoods["votes"].ge(threshold)
    space = neighborhoods["gap"].lt(0)
    neighborhoods["categoria_projecao_2028"] = np.select(
        [complete & strong & ~space, complete & strong & space, complete & ~strong & space],
        ["Base Crítica (Fortaleza)", "Vulnerável/Ameaçado", "Oportunidade BH"],
        default="Demais bairros",
    )
    neighborhoods["projection_detail"] = neighborhoods.apply(
        lambda row: (
            "Votos de referência: " + f"{row.votes:,.0f}".replace(",", ".") + "<br>"
            + "Diferença média ICP − população: " + f"{row.gap:+.2f}".replace(".", ",") + " p.p."
            if pd.notna(row.gap) and pd.notna(row.votes)
            else "Sem comparação demográfica completa nas três dimensões"
        ), axis=1,
    )
    neighborhoods = neighborhoods.reset_index()
    neighborhoods["_name"] = neighborhoods["nm_bairro"].map(_normalized_name)

    geo = reference.loc[reference["cd_ibge_municipio"].astype("string").eq("3106200")].copy()
    geo["_name"] = geo["nm_bairro"].map(_normalized_name)
    geo = geo.loc[geo["_name"].ne("")]
    payload = ["categoria_projecao_2028", "projection_detail"]
    if "cd_bairro" in geo:
        geo["cd_bairro"] = geo["cd_bairro"].astype("string")
        matched = geo.merge(neighborhoods[["cd_bairro", *payload]], on="cd_bairro", how="left")
    else:
        matched = geo.copy()
        for name in payload:
            matched[name] = pd.NA
    # Name fallback only for unambiguous source names; prefer the source TSE ID.
    fallback = neighborhoods.loc[~neighborhoods["_name"].duplicated(keep=False)].set_index("_name")
    for name in payload:
        matched[name] = matched[name].fillna(matched["_name"].map(fallback[name]))
    matched = matched.loc[matched["categoria_projecao_2028"].notna()].copy()
    for name in columns:
        if name not in matched:
            matched[name] = pd.NA
    matched["_coordinates"] = (
        pd.to_numeric(matched["nr_latitude"], errors="coerce").notna()
        & pd.to_numeric(matched["nr_longitude"], errors="coerce").notna()
    )
    result = matched.sort_values("_coordinates", ascending=False)[columns].drop_duplicates(
        ["cd_ibge_bairro", "categoria_projecao_2028"]
    )
    result.attrs["strong_vote_threshold"] = threshold
    return result
