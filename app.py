from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from hf_sync import DEFAULT_VISUALIZATION_YEAR, data_files, deputados_index, hf_visualizacao_path


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from eleitoral.common.shared_header import render_sidebar_navigation


st.set_page_config(
    page_title="RaioX Territorial",
    layout="wide",
)


pages = [
    st.Page(
        "pages/raio_x_do_voto.py",
        title="RaioX Territorial",
        url_path="raio-x-eleitoral",
        default=True,
    ),
    st.Page(
        "pages/dna_eleitor.py",
        title="DNA do Eleitor",
        url_path="dna-eleitoral",
    ),
    st.Page(
        "pages/dre_campanha.py",
        title="DRE Campanha",
        url_path="dre-campanha",
    ),
    st.Page(
        "pages/impacto_politico.py",
        title="Impacto político",
        url_path="impacto-politico",
    ),
]


sidebar_error = None
with st.sidebar:
    try:
        files = data_files()
    except FileNotFoundError:
        sidebar_error = (
            f"Pasta de dados não encontrada no Hugging Face: {hf_visualizacao_path()}. "
            "Confira HF_VISUALIZACAO_PREFIX no .env."
        )
        files = []
    except Exception as exc:
        sidebar_error = f"Falha ao ler HF: {exc}"
        files = []

    deputados = deputados_index(files)
    if deputados:
        folders = [row["Pasta"] for row in deputados]
        candidate_names = {"lud_falcao": "Lud Falcão"}
        labels = {row["Pasta"]: candidate_names.get(row["Pasta"], row["Nome"]) for row in deputados}
        current_filters = st.session_state.get("deputados_filters", {})
        current_folder = current_filters.get("pasta")
        current_index = next(
            (index for index, folder in enumerate(folders) if folder == current_folder),
            None,
        )
        if current_index is None:
            current_name = current_filters.get("nome")
            current_index = next(
                (index for index, row in enumerate(deputados) if row["Nome"] == current_name),
                0,
            )
        selected_folder = st.selectbox(
            "Candidato",
            folders,
            index=current_index,
            format_func=labels.get,
            key="candidate_folder_selector",
        )
        selected_deputado = next(row for row in deputados if row["Pasta"] == selected_folder)
        selected_key = (
            selected_deputado["Ano"],
            selected_deputado["Cargo"],
            selected_deputado["Pasta"],
        )
        if st.session_state.get("selected_deputado_key") != selected_key:
            st.session_state["selected_deputado_key"] = selected_key
            st.session_state.pop("territorial_context", None)
        st.session_state["deputados_filters"] = {
            "ano": selected_deputado["Ano"],
            "cargo": selected_deputado["Cargo"],
            "nome": selected_deputado["Nome"],
            "pasta": selected_deputado["Pasta"],
        }

    else:
        st.session_state["deputados_filters"] = {
            "ano": DEFAULT_VISUALIZATION_YEAR,
            "cargo": "Todos",
            "nome": "Todos",
            "pasta": "Todos",
        }
        st.selectbox(
            "Candidato",
            [],
            placeholder="Nenhum candidato disponível",
            disabled=True,
            key="candidate_folder_selector",
        )
    st.session_state["deputados_files"] = files

if sidebar_error:
    st.error(sidebar_error)
elif not deputados:
    st.info("Nenhuma pasta de candidato encontrada no caminho configurado.")

current_page = st.navigation(pages, position="hidden")
active_page = {
    "dna-eleitoral": "dna",
    "dre-campanha": "dre_campanha",
    "impacto-politico": "impacto_politico",
}.get(current_page.url_path, "raio_x")
with st.sidebar:
    render_sidebar_navigation(active_page)
current_page.run()

