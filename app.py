from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from hf_sync import data_files, deputados_index


SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _cargo_label(value: str) -> str:
    labels = {
        "Estaduais": "Deputado Estadual",
        "Federais": "Deputado Federal",
        "Deputados": "Deputado",
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
        title="DNA Eleitor",
        url_path="dna-eleitoral",
    ),
    st.Page(
        "pages/expansao_2030.py",
        title="Expansão 2030",
        url_path="expansao-2030",
    ),
]


with st.sidebar:
    try:
        files = data_files()
    except Exception as exc:
        st.error(f"Falha ao ler HF: {exc}")
        files = []

    deputados = deputados_index(files)
    st.markdown("### Deputado")
    if deputados:
        labels = [row["Nome"] for row in deputados]
        current_name = st.session_state.get("deputados_filters", {}).get("nome")
        current_index = labels.index(current_name) if current_name in labels else 0
        selected_index = st.selectbox(
            "Selecione o deputado",
            range(len(deputados)),
            index=current_index,
            format_func=lambda index: labels[index],
            key="deputado_selector",
        )
        selected_deputado = deputados[selected_index]
        selected_key = (
            selected_deputado["Ano"],
            selected_deputado["Cargo"],
            selected_deputado["Nome"],
        )
        if st.session_state.get("selected_deputado_key") != selected_key:
            st.session_state["selected_deputado_key"] = selected_key
            st.session_state.pop("territorial_context", None)
        st.session_state["deputados_filters"] = {
            "ano": selected_deputado["Ano"],
            "cargo": selected_deputado["Cargo"],
            "nome": selected_deputado["Nome"],
        }
        st.caption(f"{_cargo_label(selected_deputado['Cargo'])} - {selected_deputado['Ano']}")
    else:
        st.session_state["deputados_filters"] = {"ano": "2022", "cargo": "Todos", "nome": "Todos"}
        st.info("Nenhum deputado encontrado no caminho configurado.")
    st.session_state["deputados_files"] = files

current_page = st.navigation(pages, position="sidebar")
current_page.run()

