from __future__ import annotations

import base64
import html
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st
import streamlit_antd_components as sac

from hf_sync import (
    DEFAULT_VISUALIZATION_YEAR,
    data_files,
    file_by_kind,
    first_existing_column,
    hf_filesystem,
    hf_visualizacao_path,
    load_env,
    load_parquet,
    selected_deputado_files,
)


ASSET_DIR = Path(__file__).resolve().parents[3] / "assets"
BACKGROUND_PATH = ASSET_DIR / "background.png"


def _background_data_url() -> str:
    if not BACKGROUND_PATH.exists():
        return ""
    encoded = base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def background_css() -> str:
    background_url = _background_data_url()
    if not background_url:
        return ""
    return f"""
    [data-testid="stAppViewContainer"] {{
        background-image: url("{background_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    """


def apply_shared_visual_model() -> None:
    background_url = _background_data_url()
    st.html(
        dedent(f"""
        <style>
        {background_css()}
        :root {{
            --raiox-card-bg: linear-gradient(145deg, rgba(11, 31, 77, 0.76) 0%, rgba(7, 24, 54, 0.68) 100%);
            --raiox-card-bg-soft: linear-gradient(145deg, rgba(11, 31, 77, 0.58) 0%, rgba(7, 24, 54, 0.48) 100%);
            --raiox-control-bg: rgba(13, 39, 82, 0.72);
            --raiox-card-border: rgba(59, 130, 246, 0.24);
            --raiox-outline-border: rgba(177, 211, 255, 0.34);
            --raiox-card-shadow: inset 0 1px 0 rgba(191, 219, 254, 0.08), 0 18px 40px rgba(2, 9, 24, 0.30);
        }}
        .stApp {{
            color: #eaf2ff;
        }}
        .stApp h1 {{
            font-size: 2.72rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            color: #eaf2ff;
            margin-top: 0.1rem;
            margin-bottom: 0.15rem;
            line-height: 1.02;
        }}
        .st-key-raiox-hero {{
            position: relative;
            overflow: hidden;
            min-height: 22rem;
            margin: 0.15rem 0 1.25rem 0;
            padding: 2.05rem 2.35rem 2rem 2.35rem;
            border: 1px solid rgba(147, 197, 253, 0.24);
            border-radius: 0;
            background:
                linear-gradient(90deg, rgba(1, 10, 28, 0.96) 0%, rgba(3, 18, 45, 0.86) 46%, rgba(4, 20, 48, 0.60) 100%),
                url("{background_url}");
            background-size: cover;
            background-position: center;
            box-shadow: 0 22px 54px rgba(1, 8, 24, 0.58);
        }}
        .st-key-raiox-hero [data-testid="stHorizontalBlock"] {{
            min-height: 18rem;
            align-items: stretch;
        }}
        .st-key-raiox-hero [data-testid="column"] {{
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .st-key-raiox-page-navigation {{
            display: flex;
            min-height: 18rem;
            height: 100%;
            align-items: center;
            justify-content: center;
            padding: 0.7rem;
            border: 1px solid rgba(147, 197, 253, 0.32);
            border-radius: 22px;
            background: rgba(4, 18, 43, 0.72);
            box-shadow: inset 0 1px 0 rgba(219, 234, 254, 0.10), 0 12px 30px rgba(1, 8, 24, 0.30);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }}
        .st-key-raiox-page-navigation [data-testid="stVerticalBlock"] {{
            width: 100%;
        }}
        .raiox-hero-content {{
            position: relative;
            z-index: 1;
        }}
        .raiox-hero-title {{
            position: relative;
            z-index: 1;
            max-width: 100%;
            color: #f8fbff;
            font-size: 3.2rem;
            font-weight: 850;
            line-height: 1;
            letter-spacing: 0;
            text-shadow: 0 0 18px rgba(147, 197, 253, 0.36);
        }}
        .raiox-hero-subtitle {{
            position: relative;
            z-index: 1;
            margin-top: 1.1rem;
            max-width: 100%;
            color: rgba(203, 213, 225, 0.82);
            font-size: 1.04rem;
            font-weight: 600;
        }}
        .raiox-candidate-row {{
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 10.5rem minmax(0, 1fr);
            gap: 1.35rem;
            align-items: center;
            margin-top: 1.5rem;
            max-width: 58rem;
        }}
        .raiox-candidate-photo {{
            width: 10.5rem;
            aspect-ratio: 1 / 1.35;
            border-radius: 10px;
            object-fit: cover;
            background: rgba(226, 232, 240, 0.92);
            border: 1px solid rgba(255,255,255,0.42);
            box-shadow: 0 16px 34px rgba(0,0,0,0.38);
        }}
        .raiox-candidate-info {{
            display: grid;
            gap: 1.35rem;
        }}
        .raiox-candidate-line {{
            color: #f8fbff;
            font-size: 1.72rem;
            font-weight: 850;
            line-height: 1.1;
            text-transform: uppercase;
            text-shadow: 0 0 16px rgba(147, 197, 253, 0.28);
        }}
        .mapa-major-section,
        .mapa-section-card {{
            border: 1px solid var(--raiox-card-border);
            background: var(--raiox-card-bg);
            box-shadow: var(--raiox-card-shadow);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }}
        .mapa-major-section {{
            position: relative;
            overflow: hidden;
            padding: 1.28rem 1.35rem 1.16rem 1.52rem;
            margin: 1.78rem 0 1rem 0;
            border-radius: 20px;
            background:
                radial-gradient(circle at 14% 0%, rgba(96, 165, 250, 0.18) 0%, rgba(96, 165, 250, 0) 34%),
                linear-gradient(132deg, rgba(13, 36, 78, 0.94) 0%, rgba(9, 22, 43, 0.78) 54%, rgba(8, 20, 40, 0.58) 100%);
        }}
        .mapa-major-section::before {{
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 9px;
            background: linear-gradient(180deg, rgba(248, 251, 255, 1) 0%, rgba(96, 165, 250, 0.98) 42%, rgba(37, 99, 235, 0.94) 100%);
            box-shadow: 0 0 34px rgba(96, 165, 250, 0.52);
        }}
        .mapa-major-section-title {{
            position: relative;
            z-index: 1;
            color: #f8fbff;
            font-size: 2.46rem;
            font-weight: 900;
            line-height: 1.02;
            letter-spacing: 0;
            text-shadow: 0 0 22px rgba(147, 197, 253, 0.34);
        }}
        .mapa-major-section-subtitle {{
            position: relative;
            z-index: 1;
            max-width: 62rem;
            margin-top: 0.36rem;
            color: #d1def7;
            font-size: 0.96rem;
            line-height: 1.45;
        }}
        .mapa-section-card {{
            padding: 0.86rem 1rem 0.78rem 1rem;
            margin: 1.35rem 0 0.62rem 0;
            border-radius: 18px;
            background: var(--raiox-card-bg-soft);
        }}
        .mapa-section-title {{
            color: #eaf2ff;
            font-size: 1.54rem;
            font-weight: 760;
            line-height: 1.08;
            letter-spacing: 0;
        }}
        .mapa-section-subtitle {{
            margin-top: 0.17rem;
            color: #b7c7e6;
            font-size: 0.91rem;
        }}
        .dna-placeholder-card {{
            min-height: 16rem;
            margin: 0.75rem 0 1.6rem 0;
            padding: 1.1rem;
            border: 1px solid var(--raiox-outline-border);
            border-radius: 18px;
            background: rgba(7, 24, 54, 0.26);
            box-shadow: none;
        }}
        .dna-placeholder-label {{
            color: #b7c7e6;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .dna-placeholder-text {{
            margin-top: 0.42rem;
            color: #f8fbff;
            font-size: 1.05rem;
            font-weight: 700;
        }}
        .st-key-dna_potential_map_card [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--raiox-outline-border) !important;
            background: rgba(7, 24, 54, 0.18) !important;
            box-shadow: none;
        }}
        .dna-potential-side-cards {{
            display: grid;
            gap: 1rem;
        }}
        .dna-potential-side-card {{
            min-height: 10.45rem;
            border: 1px solid var(--raiox-outline-border);
            border-radius: 16px;
            background: var(--raiox-card-bg);
            box-shadow: 0 12px 30px rgba(1, 8, 24, 0.22);
        }}
        .dna-icp-card {{
            position: relative;
            overflow: hidden;
            margin: 0.75rem 0 1.6rem 0;
            padding: 1.65rem 1.75rem 1.5rem;
            border: 1px solid var(--raiox-outline-border);
            border-radius: 18px;
            background:
                radial-gradient(circle at 8% 0%, rgba(96, 165, 250, 0.18) 0%, rgba(96, 165, 250, 0) 32%),
                linear-gradient(145deg, rgba(11, 31, 77, 0.78) 0%, rgba(7, 24, 54, 0.64) 100%);
            box-shadow: var(--raiox-card-shadow);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }}
        .dna-icp-header {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
        }}
        .dna-subsection-title {{
            color: #f8fbff;
            font-size: clamp(1.65rem, 2.5vw, 2rem);
            font-weight: 800;
            line-height: 1.2;
            margin: 0 0 0.4rem;
        }}
        .dna-subsection-description, .dna-subsection-note {{
            color: #b7c7e6;
            font-size: .86rem;
            line-height: 1.5;
            margin: 0 0 1.65rem;
        }}
        .dna-subsection-note {{ margin: 18px 0 0; }}
        .dna-icp-title {{
            color: #f8fbff;
            font-size: clamp(1.25rem, 1.8vw, 1.5rem);
            font-weight: 750;
            line-height: 1.4;
        }}
        .dna-icp-summary {{
            margin-top: 0.92rem;
            padding: 0.95rem 1rem;
            border: 1px solid rgba(177, 211, 255, 0.22);
            border-radius: 14px;
            background: rgba(4, 18, 43, 0.30);
            color: #eaf2ff;
            font-size: 1.03rem;
            font-weight: 650;
            line-height: 1.45;
        }}
        .dna-icp-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0;
            margin-top: 1.55rem;
            padding-top: 1.15rem;
            border-top: 1px solid rgba(177, 211, 255, 0.2);
        }}
        .dna-icp-kpi {{
            min-height: 6.4rem;
            padding: 0.3rem 1.15rem;
            border-left: 1px solid rgba(177, 211, 255, 0.18);
        }}
        .dna-icp-kpi:first-child {{
            border-left: 0;
            padding-left: 0;
        }}
        .dna-icp-kpi-label {{
            color: #b7c7e6;
            font-size: 0.76rem;
            font-weight: 650;
            letter-spacing: 0.02em;
        }}
        .dna-icp-kpi-value {{
            margin-top: 0.65rem;
            color: #f8fbff;
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.4;
            overflow-wrap: anywhere;
        }}
        .dna-icp-kpi-pct {{
            margin-top: 0.55rem;
            color: #93c5fd;
            font-size: 1.1rem;
            font-weight: 800;
        }}
        @media (max-width: 900px) {{
            .st-key-raiox-hero {{
                min-height: auto;
                padding: 1.45rem 1.1rem 1.4rem 1.1rem;
            }}
            .st-key-raiox-hero [data-testid="stHorizontalBlock"] {{
                min-height: 0;
            }}
            .st-key-raiox-page-navigation {{
                min-height: 15rem;
            }}
            .raiox-hero-title,
            .raiox-hero-subtitle {{
                max-width: 100%;
            }}
            .dna-icp-kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .dna-icp-kpi:nth-child(odd) {{
                border-left: 0;
                padding-left: 0;
            }}
        }}
        @media (max-width: 760px) {{
            .raiox-hero-title {{
                font-size: 2.15rem;
            }}
            .raiox-candidate-row {{
                grid-template-columns: 7.5rem minmax(0, 1fr);
                gap: 0.95rem;
            }}
            .raiox-candidate-photo {{
                width: 7.5rem;
            }}
            .raiox-candidate-line {{
                font-size: 1.05rem;
            }}
            .st-key-raiox-page-navigation {{
                min-height: 13rem;
                padding: 0.4rem;
            }}
            .mapa-major-section-title {{
                font-size: 1.55rem;
            }}
            .dna-icp-header {{
                display: grid;
            }}
            .dna-icp-kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .dna-icp-kpi {{
                min-height: 0;
                padding: 0.85rem 0;
                border-left: 0;
                border-bottom: 1px solid rgba(177, 211, 255, 0.18);
            }}
            .dna-icp-kpi:last-child {{
                border-bottom: 0;
            }}
        }}
        </style>
        """)
    )


def _current_files() -> list[str]:
    files = st.session_state.get("deputados_files", [])
    if files:
        return files
    try:
        files = data_files()
        st.session_state["deputados_files"] = files
        return files
    except Exception as exc:
        st.error(f"Falha ao ler `{hf_visualizacao_path()}` no HF. Confira HF_TOKEN. Detalhe: {exc}")
        return []


def selected_files() -> list[str]:
    files = _current_files()
    filters = st.session_state.get("deputados_filters", {})
    return selected_deputado_files(files, filters)


def selected_deputado_label() -> dict[str, str]:
    filters = st.session_state.get("deputados_filters", {})
    cargo = str(filters.get("cargo") or "Deputado").replace("_", " ").title()
    cargo_labels = {
        "Estaduais": "Deputado Estadual",
        "Federais": "Deputado Federal",
        "Vereadores": "Vereador",
    }
    return {
        "nome": str(filters.get("nome") or "Todos").upper(),
        "cargo": cargo_labels.get(cargo, cargo).upper(),
        "ano": str(filters.get("ano") or DEFAULT_VISUALIZATION_YEAR),
    }


def selected_deputado_party() -> str:
    file_name = file_by_kind(selected_files(), "votos_municipio")
    if not file_name:
        return "NÃO INFORMADO"

    try:
        frame = load_parquet(file_name, load_env().get("HF_TOKEN"))
    except Exception:
        return "NÃO INFORMADO"

    party_column = first_existing_column(
        frame,
        ("sg_partido", "partido", "nm_partido", "nome_partido"),
    )
    if not party_column:
        return "NÃO INFORMADO"

    parties = frame[party_column].dropna().astype(str).str.strip()
    parties = parties[~parties.str.lower().isin({"", "nan", "none", "<na>"})]
    if parties.empty:
        return "NÃO INFORMADO"
    return parties.iloc[0].upper()


def selected_deputado_total_votes() -> str | None:
    file_name = file_by_kind(selected_files(), "votos_municipio")
    if not file_name:
        return None

    try:
        frame = load_parquet(file_name, load_env().get("HF_TOKEN"))
    except Exception:
        return None

    if frame.empty or "qt_votos" not in frame.columns:
        return None
    if "nivel_territorial" in frame.columns:
        municipal = frame[
            frame["nivel_territorial"].astype("string").str.strip().str.lower().eq("municipio")
        ]
        if not municipal.empty:
            frame = municipal

    total = pd.to_numeric(frame["qt_votos"], errors="coerce").fillna(0).sum()
    return f"{float(total):,.0f}".replace(",", ".")


@st.cache_data(show_spinner=False)
def _remote_image_data_url(file_name: str, token: str | None = None) -> str:
    suffix = Path(file_name).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    fs = hf_filesystem(token)
    with fs.open(file_name, "rb") as source:
        encoded = base64.b64encode(source.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def candidate_photo_data_url() -> str:
    image_file = next(
        (
            file_name
            for file_name in selected_files()
            if Path(file_name).suffix.lower() in {".jpg", ".jpeg", ".png"}
        ),
        "",
    )
    if not image_file:
        return ""
    try:
        return _remote_image_data_url(image_file, load_env().get("HF_TOKEN"))
    except Exception:
        return ""


_HEADER_PAGES = (
    ("raio_x", "RAIO X ELEITORAL", "pages/raio_x_do_voto.py"),
    ("dna", "DNA ELEITORAL", "pages/dna_eleitor.py"),
    ("expansao_2030", "EXPANSÃO 2030", "pages/expansao_2030.py"),
)


def _navigate_header_page(active_page: str) -> None:
    selected_index = st.session_state.get("raiox_header_page_navigation")
    if not isinstance(selected_index, int) or not 0 <= selected_index < len(_HEADER_PAGES):
        return

    target_page, _, target_path = _HEADER_PAGES[selected_index]
    if target_page != active_page:
        st.switch_page(target_path)


def _render_page_switch(active_page: str) -> None:
    active_index = next(
        (index for index, (page, _, _) in enumerate(_HEADER_PAGES) if page == active_page),
        0,
    )
    with st.container(key="raiox-page-navigation"):
        sac.buttons(
            items=[label for _, label, _ in _HEADER_PAGES],
            index=active_index,
            size=15,
            radius="lg",
            variant="outline",
            color="#2563eb",
            direction="vertical",
            gap=30,
            use_container_width=True,
            return_index=True,
            on_change=_navigate_header_page,
            args=(active_page,),
            key="raiox_header_page_navigation",
        )


def render_page_header(active_page: str, total_votes: str | None = None) -> None:
    if total_votes is None:
        total_votes = selected_deputado_total_votes()
    deputado = selected_deputado_label()
    partido = selected_deputado_party()
    page_titles = {
        "raio_x": f"RAIO X da votação {deputado['ano']}",
        "dna": "DNA do Eleitor",
        "expansao_2030": "Expansão de votos para 2030",
    }
    page_subtitles = {
        "raio_x": "Análises descritivas geográficas e do perfil do eleitor na última eleição.",
        "dna": "Quem é, onde está e como se comporta o eleitor determinante da candidatura.",
        "expansao_2030": "Oportunidades territoriais para ampliar a votação em 2030.",
    }
    title = page_titles.get(active_page, page_titles["raio_x"])
    subtitle = page_subtitles.get(active_page, page_subtitles["raio_x"])
    photo_url = candidate_photo_data_url()
    photo_html = (
        f'<img class="raiox-candidate-photo" src="{photo_url}" alt="Foto do candidato">'
        if photo_url
        else '<div class="raiox-candidate-photo"></div>'
    )
    votes_html = (
        f'<div class="raiox-candidate-line">TOTAL DE VOTOS: {html.escape(total_votes)}</div>'
        if total_votes is not None else ""
    )
    with st.container(key="raiox-hero"):
        content_col, navigation_col = st.columns([3.5, 1], gap="large")
        with content_col:
            st.html(
                dedent(f"""
                <div class="raiox-hero-content">
                    <div class="raiox-hero-title">{html.escape(title)}</div>
                    <div class="raiox-hero-subtitle">{html.escape(subtitle)}</div>
                    <div class="raiox-candidate-row">
                        {photo_html}
                        <div class="raiox-candidate-info">
                            <div class="raiox-candidate-line">NOME: {html.escape(deputado["nome"])}</div>
                            <div class="raiox-candidate-line">CARGO: {html.escape(deputado["cargo"])}</div>
                            <div class="raiox-candidate-line">PARTIDO: {html.escape(partido)}</div>
                            {votes_html}
                        </div>
                    </div>
                </div>
                """)
            )
        with navigation_col:
            _render_page_switch(active_page)


def major_section_header(title: str, subtitle: str) -> None:
    st.html(
        dedent(f"""
        <div class="mapa-major-section">
            <div class="mapa-major-section-title">{html.escape(title)}</div>
            <div class="mapa-major-section-subtitle">{html.escape(subtitle)}</div>
        </div>
        """)
    )


def section_header(title: str, subtitle: str = "") -> None:
    subtitle_html = (
        f'<div class="mapa-section-subtitle">{html.escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.html(
        dedent(f"""
        <div class="mapa-section-card">
            <div class="mapa-section-title">{html.escape(title)}</div>
            {subtitle_html}
        </div>
        """)
    )


def visualization_placeholder(label: str = "Área reservada para visualização") -> None:
    st.html(
        dedent(f"""
        <div class="dna-placeholder-card">
            <div class="dna-placeholder-label">{html.escape(label)}</div>
            <div class="dna-placeholder-text">As visualizações desta seção serão inseridas aqui.</div>
        </div>
        """)
    )

