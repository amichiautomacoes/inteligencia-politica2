from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
import streamlit as st
from huggingface_hub import HfFileSystem


DATA_DIR = Path(__file__).resolve().parent / "data" / "vereadores"
SUPPORTED_SUFFIXES = {".csv", ".parquet", ".json", ".jsonl", ".xlsx", ".xls", ".jpg", ".jpeg", ".png"}
DEFAULT_VISUALIZATION_YEAR = "2022"
DEFAULT_VISUALIZACAO_PREFIX = "vereadores"


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
        values.setdefault(key, value)
    return values


def _visualizacao_prefix(config: dict[str, str]) -> str:
    return (
        config.get("HF_VISUALIZACAO_PREFIX")
        or config.get("HF_DEPUTADOS_PREFIX")
        or DEFAULT_VISUALIZACAO_PREFIX
    ).strip("/")


def hf_visualizacao_path(env: dict[str, str] | None = None) -> str:
    config = env or load_env()
    bucket_url = config.get("HF_BUCKET_URL", "").rstrip("/")
    prefix = _visualizacao_prefix(config)
    if not bucket_url:
        raise RuntimeError("HF_BUCKET_URL nao foi configurado no .env.")
    return f"{bucket_url}/{prefix.strip('/')}"


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

    # Keep compatibility with paths from older listings that contain the
    # visualization directory but omit the bucket root or local config.
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] in {"vereadores", "deputados"}:
            return parts[index + 1 :]
    return parts


@st.cache_resource(show_spinner=False)
def hf_filesystem(token: str | None) -> HfFileSystem:
    return HfFileSystem(token=token)


@st.cache_data(show_spinner=False, ttl=600)
def remote_data_files(remote_base: str, token: str | None) -> list[str]:
    fs = hf_filesystem(token)
    return sorted(
        file_path
        for file_path in fs.find(remote_base)
        if Path(file_path).suffix.lower() in SUPPORTED_SUFFIXES
    )


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


def deputado_parts(file_name: str) -> dict[str, str] | None:
    parts = _visualizacao_relative_parts(file_name)
    if len(parts) < 3:
        return None

    if len(parts) >= 3 and parts[0] in {"estaduais", "federais"} and parts[1].isdigit():
        cargo, ano, nome_slug = parts[0], parts[1], parts[2]
    elif len(parts) >= 3 and parts[1].isdigit():
        nome_slug, ano = parts[0], parts[1]
        cargo = PurePosixPath(_visualizacao_prefix(load_env())).name
    elif len(parts) >= 4 and parts[2].isdigit():
        cargo, nome_slug, ano = parts[0], parts[1], parts[2]
    else:
        ano, cargo, nome_slug = parts[0], parts[1], parts[2]

    slug_parts = nome_slug.split("_")
    nome_tokens = slug_parts[1:] if slug_parts and slug_parts[0].isdigit() else slug_parts
    return {
        "ano": ano,
        "cargo": cargo.replace("_", " ").title(),
        "cargo_slug": cargo,
        "nome": " ".join(nome_tokens).title(),
        "nome_slug": nome_slug,
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
        if not parsed:
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
    seen: set[tuple[str, str, str]] = set()
    rows: list[dict[str, str]] = []

    for file_name in files:
        parsed = deputado_parts(file_name)
        if not parsed:
            continue

        key = (parsed["ano"], parsed["cargo"], parsed["nome"])
        if key in seen:
            continue

        seen.add(key)
        rows.append({"Ano": parsed["ano"], "Cargo": parsed["cargo"], "Nome": parsed["nome"]})

    return sorted(rows, key=lambda row: (row["Ano"], row["Cargo"], row["Nome"]))


def selected_deputado_files(files: list[str], filters: dict[str, str]) -> list[str]:
    selected: list[str] = []
    selected_year = filters.get("ano") or DEFAULT_VISUALIZATION_YEAR
    for file_name in files:
        parsed = deputado_parts(file_name)
        if not parsed:
            continue
        if selected_year not in (None, "Todos", parsed["ano"]):
            continue
        if filters.get("cargo") not in (None, "Todos", parsed["cargo"]):
            continue
        if filters.get("nome") not in (None, "Todos", parsed["nome"]):
            continue
        selected.append(file_name)
    return selected


def file_by_kind(files: list[str], kind: str) -> str | None:
    kind_aliases = {
        "votos_mesorregiao": "territorio/stage01a_municipios.parquet",
        "votos_municipio": "territorio/stage01a_municipios.parquet",
        "votos_bairro": "territorio/stage01b_bairros.parquet",
        "votos_territoriais": "territorio/stage01a_municipios.parquet",
        "escolaridade": "demografico/stage02_escolaridade.parquet",
        "estado_civil": "demografico/stage02_estado_civil.parquet",
        "genero": "demografico/stage02_genero.parquet",
        "idade": "demografico/stage02_idade.parquet",
        "gastos_territoriais": "gastos/gastos_territoriais.parquet",
        "gastos_territoriais_por_tipo": "gastos/gastos_territoriais_por_tipo.parquet",
        "despesas_campanha": "gastos/despesas_campanha.parquet",
        "emendas_legislativa": "gastos/emendas_legislativa.parquet",
        "capital_local": "forca_local/stage07a_capital_local_municipios.parquet",
        "afinidade_eleitos": "forca_local/stage07b_afinidade_eleitos.parquet",
        "icp_geral": "perfil/stage04_icp_geral_geo.parquet",
        "icp_clusters": "perfil/stage04_icp_clusters_geo.parquet",
        "censo_escolaridade": "IBGE/censo/escolaridade_apond.parquet",
        "censo_genero": "IBGE/censo/genero_apond.parquet",
        "censo_idade": "IBGE/censo/idade_apond.parquet",
        "potencial_geral": "potencial_demografico/stage08c_potencial_demografico_icp_geral.parquet",
        "potencial_clusters": "potencial_demografico/stage08c_potencial_demografico_icp_clusters.parquet",
    }
    if kind in kind_aliases:
        return next(
            (
                file_name
                for file_name in files
                if file_name.replace("\\", "/").endswith(kind_aliases[kind])
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
