from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import streamlit as st
from huggingface_hub import HfFileSystem


SUPPORTED_SUFFIXES = {".csv", ".parquet", ".json", ".jsonl", ".xlsx", ".xls", ".jpg", ".jpeg", ".png"}
DEFAULT_VISUALIZATION_YEAR = "2026"
DEFAULT_VISUALIZACAO_PREFIX = ""
DEFAULT_CANDIDATE_CARGO = "Vereadores"
SHARED_BUCKET_DIRS = {"ibge", "forca-local", "intermediate", "votacao"}
CARGO_BUCKET_DIRS = {"deputados", "estaduais", "federais", "vereadores"}


def _year_partition(value: str) -> tuple[str, str] | None:
    """Return (year, scope) for a candidate data folder such as 2026 or bh_2026."""
    value = value.strip()
    if value.isdigit() and len(value) == 4:
        return value, ""
    match = re.fullmatch(r"(?P<scope>.+)_(?P<year>\d{4})", value)
    if match:
        return match.group("year"), match.group("scope")
    return None


def load_env(path: str | Path = ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = Path(path)
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    for key, value in os.environ.items():
        values[key] = value
    return values


def _visualizacao_prefix(config: dict[str, str]) -> str:
    prefix = config.get("HF_VISUALIZACAO_PREFIX", DEFAULT_VISUALIZACAO_PREFIX).strip("/")
    # The previous bucket layout stored candidates under this prefix. Treat a
    # stale EasyPanel setting as the new bucket root.
    return "" if prefix.casefold() == "vereadores" else prefix


def hf_visualizacao_path(env: dict[str, str] | None = None) -> str:
    config = env or load_env()
    bucket_url = config.get("HF_BUCKET_URL", "").rstrip("/")
    prefix = _visualizacao_prefix(config)
    if not bucket_url:
        raise RuntimeError("HF_BUCKET_URL nao foi configurado no .env.")
    return f"{bucket_url}/{prefix}" if prefix else bucket_url


def _visualizacao_relative_parts(file_name: str) -> tuple[str, ...]:
    """Remove bucket e prefixo configurado de um caminho retornado pelo HF."""
    normalized = file_name.replace("\\", "/").removeprefix("hf://").strip("/")
    parts = PurePosixPath(normalized).parts
    env = load_env()
    prefix = _visualizacao_prefix(env)
    prefix_parts = PurePosixPath(prefix).parts

    bucket = env.get("HF_BUCKET_URL", "").removeprefix("hf://").strip("/")
    bucket_parts = PurePosixPath(bucket).parts if bucket else ()
    roots = (bucket_parts + prefix_parts, prefix_parts)
    for root in roots:
        if not root:
            continue
        for start in range(len(parts) - len(root) + 1):
            if parts[start : start + len(root)] == root:
                return parts[start + len(root) :]

    return parts


@st.cache_resource(show_spinner=False)
def hf_filesystem(token: str | None) -> HfFileSystem:
    return HfFileSystem(token=token)


@st.cache_data(show_spinner=False, ttl=600)
def remote_data_files(remote_base: str, token: str | None) -> list[str]:
    fs = hf_filesystem(token)
    candidate_roots: list[str] = []
    for entry in fs.ls(remote_base, detail=False):
        folder_name = PurePosixPath(entry.rstrip("/")).name.casefold()
        if folder_name in SHARED_BUCKET_DIRS:
            continue
        if folder_name in CARGO_BUCKET_DIRS:
            candidate_roots.append(entry)
            continue
        try:
            children = fs.ls(entry, detail=False)
        except Exception:
            continue
        if any(_year_partition(PurePosixPath(child.rstrip("/")).name) for child in children):
            candidate_roots.append(entry)

    files: set[str] = set()
    for candidate_root in candidate_roots:
        try:
            files.update(
                file_path
                for file_path in fs.find(candidate_root)
                if PurePosixPath(file_path).suffix.lower() in SUPPORTED_SUFFIXES
            )
        except Exception:
            continue
    return sorted(files)


def sync_deputados(force: bool = False) -> dict[str, Any]:
    env = load_env()
    remote_base = hf_visualizacao_path(env)
    token = env.get("HF_TOKEN")
    if force:
        remote_data_files.clear()
        load_tables.clear()
        load_parquet.clear()
    files = remote_data_files(remote_base, token)
    return {"remote": remote_base, "files": len(files)}


def data_files() -> list[str]:
    env = load_env()
    return remote_data_files(hf_visualizacao_path(env), env.get("HF_TOKEN"))


def _preferred_visualization_year(available_years: set[str]) -> str | None:
    numeric_years = {str(year) for year in available_years if str(year).isdigit()}
    if DEFAULT_VISUALIZATION_YEAR in numeric_years:
        return DEFAULT_VISUALIZATION_YEAR
    return max(numeric_years, key=int) if numeric_years else None


def deputado_parts(file_name: str) -> dict[str, str] | None:
    parts = _visualizacao_relative_parts(file_name)
    if len(parts) < 3:
        return None

    cargo: str
    nome_slug: str
    if parts[0].casefold() in {"estaduais", "federais"} and parts[1].isdigit():
        cargo, ano, nome_slug = parts[0], parts[1], parts[2]
        scope = ""
        base_path = ano
    elif len(parts) >= 4 and parts[0].casefold() in CARGO_BUCKET_DIRS:
        year_scope = _year_partition(parts[2])
        if year_scope is None:
            return None
        cargo, nome_slug = parts[0], parts[1]
        ano, scope = year_scope
        base_path = parts[2]
    elif len(parts) >= 3 and _year_partition(parts[1]) is not None:
        nome_slug = parts[0]
        ano, scope = _year_partition(parts[1]) or ("", "")
        prefix_name = PurePosixPath(_visualizacao_prefix(load_env())).name
        cargo = prefix_name or DEFAULT_CANDIDATE_CARGO
        base_path = parts[1]
    else:
        return None

    slug_parts = nome_slug.split("_")
    if slug_parts and slug_parts[0].isdigit():
        nome_tokens = slug_parts[1:]
    elif len(slug_parts) > 1 and slug_parts[0].casefold() == "bh":
        nome_tokens = slug_parts[1:]
    else:
        nome_tokens = slug_parts
    return {
        "ano": ano,
        "cargo": cargo.replace("_", " ").title(),
        "cargo_slug": cargo,
        "nome": " ".join(nome_tokens).title(),
        "nome_slug": nome_slug,
        "pasta": nome_slug,
        "base": scope,
        "base_path": base_path,
    }


@st.cache_data(show_spinner=False)
def load_tables(files: tuple[str, ...], token: str | None = None) -> pd.DataFrame:
    fs = hf_filesystem(token)
    frames: list[pd.DataFrame] = []
    for file_name in files:
        path = Path(file_name)
        try:
            if path.suffix.lower() == ".csv":
                with fs.open(file_name, "rb") as source:
                    frame = pd.read_csv(source)
            elif path.suffix.lower() == ".parquet":
                with fs.open(file_name, "rb") as source:
                    frame = pd.read_parquet(source)
            elif path.suffix.lower() in {".json", ".jsonl"}:
                with fs.open(file_name, "rb") as source:
                    frame = pd.read_json(source, lines=path.suffix.lower() == ".jsonl")
            elif path.suffix.lower() in {".xlsx", ".xls"}:
                with fs.open(file_name, "rb") as source:
                    frame = pd.read_excel(source)
            else:
                continue
        except Exception:
            continue

        frame["_arquivo_origem"] = file_name
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def first_existing_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    normalized = {column.lower().strip(): column for column in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def path_filter_options(files: list[str]) -> dict[str, list[str]]:
    anos: set[str] = set()
    cargos: set[str] = set()
    nomes: set[str] = set()

    for file_name in files:
        parsed = deputado_parts(file_name)
        if not parsed or parsed["base_path"] != parsed["ano"]:
            continue

        ano = parsed["ano"]
        if ano.isdigit():
            anos.add(ano)
        cargos.add(parsed["cargo"])
        nomes.add(parsed["nome"])

    return {
        "anos": sorted(anos),
        "cargos": sorted(cargos),
        "nomes": sorted(nomes),
    }


def deputados_index(files: list[str]) -> list[dict[str, str]]:
    years_by_candidate: dict[tuple[str, str], set[str]] = {}
    candidate_details: dict[tuple[str, str], dict[str, str]] = {}

    for file_name in files:
        parsed = deputado_parts(file_name)
        if not parsed or parsed["base_path"] != parsed["ano"]:
            continue

        key = (parsed["cargo"], parsed["pasta"])
        years_by_candidate.setdefault(key, set()).add(parsed["ano"])
        candidate_details[key] = parsed

    rows: list[dict[str, str]] = []
    for key, years in years_by_candidate.items():
        cargo, pasta = key
        selected_year = _preferred_visualization_year(years)
        if selected_year is None:
            continue
        rows.append(
            {
                "Ano": selected_year,
                "Cargo": cargo,
                "Nome": candidate_details[key]["nome"],
                "Pasta": pasta,
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            -int(row["Ano"]),
            row["Cargo"],
            row["Nome"],
            row["Pasta"],
        ),
    )


def selected_deputado_files(
    files: list[str], filters: dict[str, str], *, scope: str | None = None,
) -> list[str]:
    if filters.get("pasta") in (None, "", "Todos"):
        return []

    parsed_files = [(file_name, deputado_parts(file_name)) for file_name in files]
    candidate_files = [
        (file_name, parsed)
        for file_name, parsed in parsed_files
        if parsed
        and (
            parsed["base_path"] == parsed["ano"]
            if scope is None
            else parsed["base"].casefold() == scope.casefold()
            and parsed["base_path"].casefold() == f"{scope}_{parsed['ano']}".casefold()
        )
        and filters.get("cargo") in (None, "Todos", parsed["cargo"])
        and filters.get("nome") in (None, "Todos", parsed["nome"])
        and filters.get("pasta") in (None, "", "Todos", parsed["pasta"])
    ]

    requested_year = filters.get("ano")
    available_years = {parsed["ano"] for _, parsed in candidate_files}
    if requested_year in (None, "", "Todos") or requested_year not in available_years:
        requested_year = _preferred_visualization_year(available_years) or DEFAULT_VISUALIZATION_YEAR

    return [
        file_name
        for file_name, parsed in candidate_files
        if parsed["ano"] == requested_year
    ]


def file_by_kind(files: list[str], kind: str) -> str | None:
    kind_aliases = {
        "votos_mesorregiao": "territorio/stage01a_municipios.parquet",
        "votos_municipio": "territorio/stage01a_municipios.parquet",
        "votos_bairro": "territorio/stage01b_bairros.parquet",
        "bh_bairros_estrategicos": "territorio/stage07_bairros_estrategicos.parquet",
        "votos_territoriais": "territorio/stage01a_municipios.parquet",
        "escolaridade": "demografico/stage02_escolaridade.parquet",
        "estado_civil": "demografico/stage02_estado_civil.parquet",
        "genero": "demografico/stage02_genero.parquet",
        "idade": "demografico/stage02_idade.parquet",
        "gastos_territoriais": "gastos/gastos_territoriais.parquet",
        "gastos_territoriais_por_tipo": "gastos/gastos_territoriais_por_tipo.parquet",
        "despesas_campanha": "gastos/despesas_campanha.parquet",
        "emendas_legislativa": (
            "emendas/emendas_municipais.parquet",
            "gastos/emendas_legislativa.parquet",
        ),
        "capital_local": "forca_local/stage07a_capital_local_municipios.parquet",
        "afinidade_eleitos": "forca_local/stage07b_afinidade_eleitos.parquet",
        "icp_geral": "perfil/stage04_icp_geral_geo.parquet",
        "icp_clusters": "perfil/stage04_icp_clusters_geo.parquet",
        "censo_escolaridade": "IBGE/censo/escolaridade_apond.parquet",
        "censo_genero": "IBGE/censo/genero_apond.parquet",
        "censo_idade": "IBGE/censo/idade_apond.parquet",
        "censo_icp_geral": "IBGE/censo/stage04_icp_geral_geo_por_area_ponderada.parquet",
        "censo_icp_clusters": "IBGE/censo/stage04_icp_clusters_geo_por_area_ponderada.parquet",
        "potencial_geral": "potencial_demografico/stage08c_potencial_demografico_icp_geral.parquet",
        "potencial_clusters": "potencial_demografico/stage08c_potencial_demografico_icp_clusters.parquet",
    }
    if kind in kind_aliases:
        targets = kind_aliases[kind]
        if isinstance(targets, str):
            targets = (targets,)
        return next(
            (
                file_name
                for target in targets
                for file_name in files
                if file_name.replace("\\", "/").endswith(target)
            ),
            None,
        )

    suffix = f"_{kind}.parquet"
    return next((file_name for file_name in files if file_name.endswith(suffix)), None)


@st.cache_data(show_spinner=False)
def load_parquet(file_name: str, token: str | None = None) -> pd.DataFrame:
    fs = hf_filesystem(token)
    with fs.open(file_name, "rb") as source:
        return pd.read_parquet(source)


def build_filter_options(df: pd.DataFrame, files: list[str] | None = None) -> dict[str, Any]:
    year_col = first_existing_column(df, ("ano", "ano_eleicao", "nr_ano", "year"))
    office_col = first_existing_column(df, ("cargo", "ds_cargo", "nome_cargo", "office"))
    name_col = first_existing_column(
        df,
        ("nome", "nome_urna", "nm_urna_candidato", "nm_candidato", "deputado", "parlamentar", "name"),
    )
    fallback = path_filter_options(files or [])

    def options(column: str | None) -> list[str]:
        if column is None:
            return []
        values = df[column].dropna().astype(str).str.strip()
        return sorted(value for value in values.unique() if value)

    return {
        "columns": {"ano": year_col, "cargo": office_col, "nome": name_col},
        "anos": options(year_col) or fallback["anos"],
        "cargos": options(office_col) or fallback["cargos"],
        "nomes": options(name_col) or fallback["nomes"],
    }


def filtered_dataframe(df: pd.DataFrame, filters: dict[str, str], columns: dict[str, str | None]) -> pd.DataFrame:
    result = df.copy()
    for key, selected in filters.items():
        column = columns.get(key)
        if not column or selected == "Todos":
            continue
        result = result[result[column].astype(str) == selected]
    return result
