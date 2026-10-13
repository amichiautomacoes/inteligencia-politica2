"""Consolidação do perfil usada pelo DNA e pela comparação capital/interior."""
from __future__ import annotations
import unicodedata
import pandas as pd

def _has_profile_label(value: str) -> bool:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return bool(normalized.strip()) and normalized.strip() != "nao informado"


def _weighted_dominant(df: pd.DataFrame, value_col: str) -> tuple[str, float]:
    if df.empty or value_col not in df.columns:
        return "Nao informado", 0.0
    working = df[[value_col]].copy()
    working[value_col] = working[value_col].fillna("").astype(str).str.strip()
    working = working[working[value_col].ne("")]
    if working.empty:
        return "Nao informado", 0.0
    if "votos_candidato" in df.columns:
        working["votos_candidato"] = pd.to_numeric(
            df.loc[working.index, "votos_candidato"], errors="coerce"
        ).fillna(0)
    else:
        working["votos_candidato"] = 1
    grouped = working.groupby(value_col, as_index=False)["votos_candidato"].sum()
    total = float(grouped["votos_candidato"].sum())
    top = grouped.sort_values("votos_candidato", ascending=False).iloc[0]
    pct = float(top["votos_candidato"]) / total * 100 if total > 0 else 0.0
    return str(top[value_col]), pct


def _territorial_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Use a single territorial level: municipalities, or neighborhoods as fallback."""
    if "nivel_territorial" not in df:
        return df.copy()
    levels = df["nivel_territorial"].astype(str).str.strip().str.lower()
    for level in ("municipio", "bairro"):
        if levels.eq(level).any():
            return df.loc[levels.eq(level)].copy()
    return df.iloc[:0].copy()


def _demographic_percent(df: pd.DataFrame, column: str, category: str) -> float:
    pct_column = f"pct_{column}"
    if pct_column not in df and f"{pct_column}_global" in df:
        pct_column = f"{pct_column}_global"
    if pct_column not in df or column not in df:
        return float("nan")
    # These percentages describe the category, not the profile's electoral share.
    rows = df.loc[df[column].eq(category)]
    values = pd.to_numeric(rows[pct_column], errors="coerce")
    valid = values.between(0, 100)
    if not valid.any():
        return float("nan")
    weights = pd.to_numeric(rows.loc[valid, "votos_candidato"], errors="coerce").fillna(0)
    return float((values[valid] * weights).sum() / weights.sum()) if weights.sum() > 0 else float(values[valid].mean())


def _icp_general_row(icp_df: pd.DataFrame) -> pd.DataFrame:
    if icp_df.empty:
        return icp_df
    working = _territorial_rows(icp_df)
    if "votos_candidato" not in working:
        working["votos_candidato"] = 0.0
    working["votos_candidato"] = pd.to_numeric(working["votos_candidato"], errors="coerce").fillna(0)

    persona, _ = _weighted_dominant(working, "persona_executiva")
    genero, pct_genero = _weighted_dominant(working, "genero_principal")
    idade, pct_idade = _weighted_dominant(working, "idade_principal")
    escolaridade, pct_escolaridade = _weighted_dominant(working, "escolaridade_principal")
    estado_civil, pct_estado_civil = _weighted_dominant(working, "estado_civil_principal")
    pct_genero = _demographic_percent(working, "genero_principal", genero)
    pct_idade = _demographic_percent(working, "idade_principal", idade)
    pct_escolaridade = _demographic_percent(working, "escolaridade_principal", escolaridade)
    pct_estado_civil = _demographic_percent(working, "estado_civil_principal", estado_civil)
    summary, _ = _weighted_dominant(working, "perfil_resumo")
    if summary == "Nao informado":
        summary = persona

    confidence = 0.0
    if "confianca_persona" in working.columns:
        confidence_values = pd.to_numeric(working["confianca_persona"], errors="coerce")
        if "votos_candidato" in working.columns:
            weights = pd.to_numeric(working["votos_candidato"], errors="coerce").fillna(0)
            valid = confidence_values.notna() & weights.gt(0)
            if valid.any():
                confidence = float((confidence_values[valid] * weights[valid]).sum() / weights[valid].sum())
        elif confidence_values.notna().any():
            confidence = float(confidence_values.mean())

    return pd.DataFrame(
        [
            {
                "persona_executiva": persona,
                "perfil_resumo": summary,
                "genero_principal": genero,
                "pct_genero_principal": pct_genero,
                "idade_principal": idade,
                "pct_idade_principal": pct_idade,
                "escolaridade_principal": escolaridade,
                "pct_escolaridade_principal": pct_escolaridade,
                "estado_civil_principal": estado_civil,
                "pct_estado_civil_principal": pct_estado_civil,
                "confianca_persona": confidence,
            }
        ]
    )
