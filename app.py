from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from hf_sync import DEFAULT_VISUALIZATION_YEAR, data_files, deputados_index, sync_deputados


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _cargo_label(value: str) -> str:
    labels = {
        "Estaduais": "Deputado Estadual",
        "Federais": "Deputado Federal",
        "Deputados": "Deputado",
        "Vereadores": "Vereador",
    }
    return labels.get(value, value)


st.set_page_config(
    page_title="Raio X do voto",
    layout="wide",
)


pages = [
    st.Page(
        "pages/raio_x_do_voto.py",
        title="Raio X do voto",
        url_path="raio-x-eleitoral",
        default=True,
    ),
    st.Page(
        "pages/dna_eleitor.py",
        title="DNA do Eleitor",
        url_path="dna-eleitoral",
    ),
]


with st.sidebar:
    st.markdown("### Cargo Atual")
    offices = {"Vereadores": "vereadores", "Deputados Estaduais": "dep_estaduais"}
    office = st.selectbox("Cargo Atual", list(offices), key="current_office_selector", label_visibility="collapsed")
    group = offices[office]
    if st.session_state.get("candidate_group") != group:
        for state_key in list(st.session_state):
            if state_key not in {"current_office_selector", "candidate_group"}:
                del st.session_state[state_key]
    st.session_state["candidate_group"] = group
    st.markdown("### Candidato")
    try:
        if st.button("Atualizar candidatos", help="Consulta o HF novamente para incluir novos candidatos."):
            sync_deputados(force=True)
        files = data_files()
    except Exception as exc:
        st.error(f"Falha ao ler HF: {exc}")
        files = []

    deputados = deputados_index(files)
    if deputados:
        folders = [row["Pasta"] for row in deputados]
        candidate_names = {"marcela_tropia": "Marcela Trópia", "lud_falcao": "Lud Falcão"}
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
        st.info("Nenhuma pasta de candidato encontrada no caminho configurado.")
    st.session_state["deputados_files"] = files

current_page = st.navigation(pages, position="hidden")
current_page.run()

