from __future__ import annotations

import base64
import html
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from hf_sync import DEFAULT_VISUALIZATION_YEAR, data_files, file_by_kind, hf_filesystem, hf_visualizacao_path, load_env, load_parquet, selected_deputado_files
from eleitoral.maps.dna_geo_reference import load_geo_reference
from eleitoral.maps.choropleth_maps import (
    ACTION_COLORS,
    LOCAL_STRENGTH_COLORS,
    LOCAL_STRENGTH_ICONS,
    LOCAL_STRENGTH_LABELS,
    LOCAL_STRENGTH_LEGEND,
    local_political_strength_map,
    local_political_strength_municipality_map,
    parliamentary_map,
    territorial_map,
)
from eleitoral.maps.territorial_mesh import (
    municipality_mesh_map,
)
from eleitoral.common.shared_header import render_page_header

try:
    import streamlit_shadcn_ui as ui
except Exception:
    ui = None


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
BACKGROUND_PATH = ASSET_DIR / "background.png"
DEMOGRAPHIC_CONTEXT_KEY = "pagina1_demographic_territorial_context"
EXPENSE_TREEMAP_KEY = "pagina1_treemap_despesas"
EXPENSE_SELECTION_KEY = "pagina1_tipo_despesa_selecionado"
EXPENSE_TREEMAP_REVISION_KEY = "pagina1_treemap_despesas_revisao"
LOCAL_STRENGTH_SELECTION_KEY = "pagina1_forca_local_classe_selecionada"
LOCAL_STRENGTH_MAP_REVISION_KEY = "pagina1_forca_local_mapa_revisao"
USE_CUSTOM_KPI_CARDS = True


def _background_css() -> str:
    if not BACKGROUND_PATH.exists():
        return ""
    encoded = base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("ascii")
    return f"""
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    """


def _apply_visual_model() -> None:
    st.markdown(
        f"""
        <style>
        {_background_css()}
        :root {{
            --raiox-card-bg: linear-gradient(145deg, rgba(11, 31, 77, 0.76) 0%, rgba(7, 24, 54, 0.68) 100%);
            --raiox-card-bg-soft: linear-gradient(145deg, rgba(11, 31, 77, 0.58) 0%, rgba(7, 24, 54, 0.48) 100%);
            --raiox-glass-bg: linear-gradient(145deg, rgba(15, 42, 88, 0.46) 0%, rgba(8, 28, 64, 0.32) 100%);
            --raiox-glass-bg-strong: linear-gradient(145deg, rgba(15, 42, 88, 0.58) 0%, rgba(8, 28, 64, 0.42) 100%);
            --raiox-control-bg: rgba(13, 39, 82, 0.72);
            --raiox-card-border: rgba(59, 130, 246, 0.24);
            --raiox-card-border-soft: rgba(177, 211, 255, 0.36);
            --raiox-outline-border: rgba(177, 211, 255, 0.34);
            --raiox-outline-border-strong: rgba(219, 234, 254, 0.48);
            --raiox-card-shadow: inset 0 1px 0 rgba(191, 219, 254, 0.08), 0 18px 40px rgba(2, 9, 24, 0.30);
            --raiox-glass-shadow: none;
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
        .stApp [data-testid="stCaptionContainer"] p {{
            color: #b7c7e6 !important;
            font-size: 0.95rem !important;
            margin-bottom: 1.1rem !important;
            line-height: 1.35 !important;
        }}
        .raiox-hero {{
            position: relative;
            overflow: hidden;
            min-height: 22rem;
            margin: 0.15rem 0 1.25rem 0;
            padding: 2.05rem 2.35rem 2rem 2.35rem;
            border: 1px solid rgba(147, 197, 253, 0.24);
            border-radius: 0;
            background:
                linear-gradient(90deg, rgba(1, 10, 28, 0.96) 0%, rgba(3, 18, 45, 0.86) 46%, rgba(4, 20, 48, 0.60) 100%),
                url("data:image/png;base64,{base64.b64encode(BACKGROUND_PATH.read_bytes()).decode("ascii") if BACKGROUND_PATH.exists() else ""}");
            background-size: cover;
            background-position: center;
            box-shadow: 0 22px 54px rgba(1, 8, 24, 0.58);
        }}
        .raiox-hero-title {{
            position: relative;
            z-index: 1;
            max-width: calc(100% - 25rem);
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
            max-width: calc(100% - 25rem);
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
        .raiox-page-switch {{
            position: absolute;
            z-index: 2;
            top: 2.05rem;
            right: 2.35rem;
            display: inline-grid;
            grid-template-columns: repeat(3, minmax(8.9rem, 1fr));
            gap: 0.25rem;
            padding: 0.28rem;
            border: 1px solid rgba(147, 197, 253, 0.32);
            border-radius: 999px;
            background: rgba(4, 18, 43, 0.72);
            box-shadow: inset 0 1px 0 rgba(219, 234, 254, 0.10), 0 12px 30px rgba(1, 8, 24, 0.30);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }}
        .raiox-page-switch a {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 2.35rem;
            padding: 0 0.9rem;
            border-radius: 999px;
            color: #b7c7e6;
            font-size: 0.83rem;
            font-weight: 850;
            text-decoration: none;
            text-transform: uppercase;
            letter-spacing: 0;
            white-space: nowrap;
        }}
        .raiox-page-switch a.active {{
            color: #f8fbff;
            background: linear-gradient(145deg, rgba(96, 165, 250, 0.42), rgba(37, 99, 235, 0.30));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.20), 0 8px 18px rgba(37, 99, 235, 0.24);
        }}
        .raiox-page-switch a:not(.active):hover {{
            color: #f8fbff;
            background: rgba(96, 165, 250, 0.16);
        }}
        @media (max-width: 900px) {{
            .raiox-page-switch {{
                position: relative;
                inset: auto;
                margin-bottom: 1.1rem;
                width: 100%;
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }}
            .raiox-hero-title,
            .raiox-hero-subtitle {{
                max-width: 100%;
            }}
        }}
        @media (max-width: 760px) {{
            .raiox-hero {{
                padding: 1.45rem 1.1rem 1.4rem 1.1rem;
                min-height: auto;
            }}
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
            .raiox-page-switch {{
                grid-template-columns: 1fr;
                border-radius: 18px;
            }}
        }}
        .mapa-major-section,
        .mapa-section-card {{
            border: 1px solid var(--raiox-card-border);
            background: var(--raiox-card-bg);
            box-shadow: var(--raiox-card-shadow);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }}
        .mapa-kpi-card,
        .mapa-kpi-wide-card,
        .raiox-kpi-card,
        .raiox-demografia-card,
        .raiox-heatmap-card,
        .raiox-concentration-pill {{
            border: 1px solid var(--raiox-outline-border);
            background: transparent;
            box-shadow: none;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
        }}
        .stApp [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: var(--raiox-outline-border) !important;
            background: transparent !important;
            box-shadow: none;
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
        }}
        .st-key-parliamentary-map-container [data-testid="stVerticalBlockBorderWrapper"] {{
            padding-left: 0 !important;
            padding-right: 0 !important;
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
        .mapa-kpi-grid,
        .raiox-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 0.45rem;
            margin-bottom: 0.9rem;
        }}
        .raiox-kpi-grid {{
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-top: 0.95rem;
            margin-bottom: 1.1rem;
        }}
        .mapa-kpi-card,
        .mapa-kpi-wide-card,
        .raiox-kpi-card {{
            border-radius: 16px;
            padding: 0.82rem 0.9rem 0.72rem 0.9rem;
            min-height: 7.8rem;
        }}
        .mapa-kpi-label {{
            color: #b7c7e6;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .mapa-kpi-value {{
            color: #f8fbff;
            font-size: 2.08rem;
            line-height: 1.04;
            font-weight: 800;
            margin-top: 0.2rem;
        }}
        .mapa-kpi-caption {{
            color: #b7c7e6;
            font-size: 0.8rem;
            margin-top: 0.34rem;
            line-height: 1.25;
        }}
        .raiox-map-side-cards {{
            display: grid;
            gap: 1rem;
        }}
        .raiox-map-side-card {{
            min-height: 9.25rem;
            padding: 0.9rem 1rem;
            border: 1px solid var(--raiox-outline-border);
            border-radius: 16px;
            background: var(--raiox-card-bg);
            box-shadow: 0 12px 30px rgba(1, 8, 24, 0.22);
        }}
        .raiox-map-side-label {{
            color: #93c5fd;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }}
        .raiox-map-side-value {{
            color: #f8fbff;
            font-size: clamp(1.3rem, 2vw, 1.9rem);
            font-weight: 850;
            line-height: 1.13;
            margin-top: 0.55rem;
        }}
        .raiox-map-side-caption {{
            color: #b7c7e6;
            font-size: 0.8rem;
            line-height: 1.3;
            margin-top: 0.42rem;
        }}
        .raiox-map-side-badge {{
            display: inline-block;
            margin-top: 0.55rem;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            font-size: 0.73rem;
            font-weight: 750;
            background: rgba(37, 99, 235, 0.23);
            color: #bfdbfe;
        }}
        .raiox-map-side-badge.good {{ background: rgba(22, 163, 74, 0.2); color: #86efac; }}
        .raiox-map-side-badge.warn {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; }}
        .mapa-kpi-wide-card {{
            position: relative;
            overflow: hidden;
            margin-top: -0.2rem;
            margin-bottom: 1.1rem;
            min-height: 9.4rem;
            padding: 1.18rem 1.35rem 1.05rem 1.35rem;
            background: transparent;
        }}
        .mapa-kpi-wide-tag {{
            position: absolute;
            top: 1rem;
            right: 1.2rem;
            color: #f0fdf4;
            background: linear-gradient(145deg, rgba(22, 163, 74, 0.92), rgba(21, 128, 61, 0.86));
            border: 1px solid rgba(134, 239, 172, 0.62);
            border-radius: 999px;
            padding: 0.38rem 0.78rem;
            font-size: 0.76rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            box-shadow: 0 8px 20px rgba(22, 163, 74, 0.22);
        }}
        .mapa-kpi-wide-value {{
            max-width: 44rem;
            margin-top: 0.28rem;
            color: #ffffff;
            font-size: 2.35rem;
            font-weight: 900;
            line-height: 1.02;
        }}
        .mapa-kpi-wide-caption {{
            margin-top: 0.72rem;
            color: #dbeafe;
            font-size: 1.15rem;
            font-weight: 800;
            line-height: 1.25;
        }}
        .raiox-kpi-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: rgba(239, 246, 255, 0.95);
        }}
        .raiox-kpi-dominant-label {{
            display: block;
            margin-top: 0.62rem;
            font-size: 1.58rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .raiox-kpi-dominant-share {{
            display: block;
            margin-top: 0.28rem;
            font-size: 0.98rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.92);
        }}
        .raiox-demografia-card,
        .raiox-heatmap-card {{
            border-radius: 18px;
            padding: 1rem 1.1rem 0.9rem 1.1rem;
            margin: 0.75rem 0 0.65rem 0;
        }}
        .raiox-demografia-header,
        .raiox-heatmap-title {{
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.1;
            color: #f8fafc;
            letter-spacing: 0.01em;
        }}
        .raiox-demografia-subtitle,
        .raiox-heatmap-subtitle {{
            margin-top: 0.2rem;
            font-size: 1rem;
            color: rgba(226, 232, 240, 0.95);
        }}
        [data-testid="stPlotlyChart"] {{
            background: transparent;
            border: 0;
            border-radius: 0;
            padding: 0;
            box-shadow: none;
        }}
        .raiox-bar-title {{
            color: #eaf2ff;
            font-size: 1.34rem;
            font-weight: 800;
            line-height: 1.12;
            margin: 0.12rem 0 0.35rem 0;
            text-align: center;
        }}
        .raiox-chart-card-title {{
            color: #eaf2ff;
            font-size: 1.34rem;
            font-weight: 800;
            line-height: 1.12;
            margin: 0.12rem 0 0.78rem 0;
            text-align: center;
        }}
        .raiox-cost-chart-heading {{
            display: flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin: 0.12rem 0 0.78rem 0;
            text-align: center;
        }}
        .raiox-cost-chart-heading .raiox-chart-card-title {{
            margin: 0;
        }}
        .raiox-cost-filter-tag {{
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            min-height: 1.8rem;
            padding: 0.28rem 0.7rem;
            border: 1px solid rgba(96, 165, 250, 0.45);
            border-radius: 999px;
            background: linear-gradient(145deg, rgba(96, 165, 250, 0.26), rgba(37, 99, 235, 0.18));
            color: #f8fbff;
            font-size: 0.78rem;
            font-weight: 850;
            line-height: 1.15;
            text-transform: uppercase;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.13);
        }}
        .raiox-neighborhood-kpis {{
            display: grid;
            gap: 0.45rem;
            max-width: 11rem;
            margin-left: auto;
        }}
        .raiox-neighborhood-kpi {{
            padding: 0.45rem 0.7rem;
            border: 1px solid rgba(96, 165, 250, 0.28);
            border-radius: 10px;
            background: rgba(11, 31, 77, 0.76);
            text-align: right;
        }}
        .raiox-neighborhood-kpi-label {{
            color: #b7c7e6;
            font-size: 0.72rem;
            line-height: 1.2;
        }}
        .raiox-neighborhood-kpi-value {{
            color: #f8fbff;
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.15;
        }}
        .raiox-concentration-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin: 0;
            border-radius: 12px 12px 0 0;
            background: rgba(7, 24, 54, 0.54);
            overflow: hidden;
        }}
        .raiox-concentration-pill {{
            padding: 1rem 1.15rem;
            border: 0 !important;
            border-right: 1px solid rgba(147, 197, 253, 0.16) !important;
            background: transparent;
            min-width: 0;
            display: flex;
            flex-direction: column;
        }}
        .raiox-concentration-pill:last-child {{
            border-right: 0 !important;
        }}
        .raiox-concentration-pill:first-child {{
            background: linear-gradient(145deg, rgba(96, 165, 250, 0.14), rgba(96, 165, 250, 0.03));
            box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.3), inset 0 0 24px rgba(96, 165, 250, 0.08);
        }}
        .raiox-concentration-leader-badge {{
            align-self: flex-start;
            color: #dbeafe;
            background: rgba(96, 165, 250, 0.18);
            border: 1px solid rgba(96, 165, 250, 0.3);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            font-size: 0.68rem;
            font-weight: 750;
            margin-top: 0.6rem;
        }}
        .raiox-concentration-pill-label {{
            color: #86efac;
            font-size: 0.82rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.075em;
        }}
        .raiox-concentration-pill-value,
        .raiox-concentration-pill-metric {{
            color: #ffffff;
            font-size: clamp(2rem, 3.2vw, 3rem);
            font-weight: 950;
            line-height: 1.1;
            margin: 0.56rem 0 0.08rem;
            font-variant-numeric: tabular-nums;
        }}
        .raiox-concentration-pill-unit {{
            margin-left: 0.34rem;
            color: #b7c7e6;
            font-size: clamp(0.86rem, 1vw, 1rem);
            font-weight: 750;
            letter-spacing: 0;
        }}
        [class*="st-key-pagina1_concentration_donut_"] .js-line {{
            stroke-linecap: round !important;
            stroke-linejoin: round !important;
        }}
        .raiox-concentration-pill-city {{
            color: #ffffff;
            font-size: 1.3rem;
            font-weight: 800;
            line-height: 1.2;
            margin-top: 0.35rem;
        }}
        .raiox-concentration-pill-city span {{
            color: #b7c7e6;
            font-size: 0.82rem;
            font-weight: 500;
        }}
        .raiox-concentration-leader {{
            color: #f8fbff;
            font-size: 0.84rem;
            font-weight: 700;
            margin-top: 0.45rem;
        }}
        .raiox-concentration-breakdown {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.55rem;
            margin: 1rem 0;
        }}
        .raiox-concentration-breakdown-step {{
            border: 1px solid rgba(147, 197, 253, 0.25);
            border-radius: 14px;
            background: rgba(11, 31, 77, 0.72);
            padding: 0.8rem 1rem;
            min-width: 9.5rem;
        }}
        .raiox-concentration-breakdown-title {{ color: #cbd5e1; font-size: 0.78rem; }}
        .raiox-concentration-breakdown-value {{ color: #ffffff; font-size: 1.15rem; font-weight: 800; }}
        .raiox-concentration-breakdown-votes {{ color: #b7c7e6; font-size: 0.78rem; }}
        .raiox-concentration-breakdown-arrow {{ color: #93c5fd; font-size: 1.5rem; }}
        .raiox-concentration-track {{
            display: flex;
            height: 12px;
            width: 100%;
            background: rgba(147, 197, 253, 0.12);
            overflow: hidden;
        }}
        .raiox-concentration-segment {{
            height: 100%;
            flex-shrink: 0;
        }}
        .raiox-concentration-bar-caption {{
            color: #9fb2d4;
            font-size: 0.7rem;
            line-height: 1.3;
            margin: 0 0 0.9rem;
            padding: 0.4rem 0.65rem 0;
        }}
        .raiox-concentration-gain {{
            align-self: flex-start;
            color: #a5f3fc;
            background: rgba(34, 211, 238, 0.1);
            border: 1px solid rgba(103, 232, 249, 0.2);
            border-radius: 999px;
            padding: 0.22rem 0.55rem;
            font-size: 0.72rem;
            font-weight: 700;
            margin-top: 0.65rem;
        }}
        .raiox-concentration-reading {{
            color: #d6e4f9;
            font-size: 0.95rem;
            line-height: 1.5;
            margin: 0.25rem 0 0.7rem;
        }}
        .raiox-concentration-reading strong {{
            color: #f8fbff;
            font-weight: 750;
        }}
        .raiox-concentration-city-list {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.55rem 0.8rem;
            padding: 0.25rem 0 0.5rem;
            color: #eaf2ff;
            font-size: 0.83rem;
        }}
        .raiox-concentration-city-item {{
            display: grid;
            grid-template-columns: auto minmax(0, 1fr) auto;
            align-items: center;
            gap: 0.4rem;
            min-width: 0;
            padding: 0.5rem 0.65rem;
            border: 1px solid rgba(147, 197, 253, 0.15);
            border-radius: 8px;
            background: rgba(10, 30, 65, 0.45);
        }}
        .raiox-concentration-city-rank {{
            color: #93c5fd;
            font-weight: 750;
            font-variant-numeric: tabular-nums;
        }}
        .raiox-concentration-city-name {{
            min-width: 0;
            overflow-wrap: anywhere;
        }}
        .raiox-concentration-city-votes {{
            color: #dbeafe;
            font-weight: 750;
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
            padding-left: 0.5rem;
            border-left: 1px solid rgba(147, 197, 253, 0.2);
        }}
        .raiox-bar-filter [data-testid="stSelectbox"] {{
            max-width: 16rem;
            margin-left: auto;
        }}
        .stApp [data-testid="stSelectbox"] label,
        .stApp [data-testid="stMultiSelect"] label {{
            color: #dbeafe !important;
            font-weight: 700;
        }}
        .stApp [data-baseweb="select"] > div,
        .stApp [data-baseweb="select"] [role="combobox"],
        .stApp [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        .stApp [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
            background: var(--raiox-control-bg) !important;
            border: 1px solid rgba(125, 184, 255, 0.34) !important;
            border-radius: 12px !important;
            color: #f8fbff !important;
            box-shadow: inset 0 1px 0 rgba(219, 234, 254, 0.12), 0 10px 24px rgba(2, 9, 24, 0.20) !important;
            backdrop-filter: blur(12px) saturate(120%);
            -webkit-backdrop-filter: blur(12px) saturate(120%);
        }}
        .stApp [data-baseweb="select"] svg {{
            fill: #bfdbfe !important;
        }}
        .stApp [data-baseweb="select"] span,
        .stApp [data-baseweb="select"] div {{
            color: #f8fbff !important;
        }}
        div[data-baseweb="popover"] {{
            background: transparent !important;
        }}
        div[data-baseweb="popover"] ul,
        div[role="listbox"] {{
            background: linear-gradient(145deg, rgba(11, 31, 77, 0.96) 0%, rgba(7, 24, 54, 0.94) 100%) !important;
            border: 1px solid rgba(125, 184, 255, 0.34) !important;
            border-radius: 12px !important;
            box-shadow: 0 18px 42px rgba(2, 9, 24, 0.48) !important;
            color: #f8fbff !important;
        }}
        div[role="option"] {{
            background: transparent !important;
            color: #f8fbff !important;
        }}
        div[role="option"]:hover,
        div[role="option"][aria-selected="true"] {{
            background: rgba(59, 130, 246, 0.28) !important;
            color: #ffffff !important;
        }}
        @media (max-width: 900px) {{
            .mapa-kpi-grid,
            .raiox-kpi-grid {{
                grid-template-columns: 1fr;
            }}
            .raiox-concentration-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .raiox-concentration-pill:nth-child(2) {{
                border-right: 0 !important;
            }}
            .raiox-concentration-pill:nth-child(-n+2) {{
                border-bottom: 1px solid rgba(147, 197, 253, 0.16) !important;
            }}
            .raiox-concentration-city-list {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .mapa-major-section-title {{
                font-size: 1.55rem;
            }}
        }}
        @media (max-width: 600px) {{
            .raiox-concentration-city-list {{
                grid-template-columns: 1fr;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _major_section_header(title: str, subtitle: str) -> None:
    subtitle_html = (
        f'<div class="mapa-major-section-subtitle">{subtitle}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="mapa-major-section">
            <div class="mapa-major-section-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div class="mapa-section-card">
            <div class="mapa-section-title">{title}</div>
            <div class="mapa-section-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def _load_geo_reference() -> tuple[dict | None, pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None]:
    return load_geo_reference()



def _normalize_municipio_name(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())




def _iter_geojson_rings(geometry: dict) -> list[list[list[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    if geometry_type == "Polygon":
        return coordinates
    if geometry_type == "MultiPolygon":
        return [ring for polygon in coordinates for ring in polygon]
    return []




def _format_number(value: float | int) -> str:
    return f"{float(value):,.0f}".replace(",", ".")


def _format_percent(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "--"
    return f"{float(value) * 100:.1f}%".replace(".", ",")


def _format_currency(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "R$ 0,00"
    formatted = f"{float(value):,.2f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_currency_whole(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "R$ 0"
    return f"R$ {_format_number(round(float(value)))}"


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


def _selected_files(scope: str | None = None) -> list[str]:
    files = _current_files()
    filters = st.session_state.get("deputados_filters", {})
    return selected_deputado_files(files, filters, scope=scope)


def _selected_deputado_label() -> dict[str, str]:
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


@st.cache_data(show_spinner=False)
def _remote_image_data_url(file_name: str, token: str | None = None) -> str:
    suffix = Path(file_name).suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    fs = hf_filesystem(token)
    with fs.open(file_name, "rb") as source:
        encoded = base64.b64encode(source.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _candidate_photo_data_url() -> str:
    image_file = next(
        (
            file_name
            for file_name in _selected_files()
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


def _render_page_header(total_votes: str) -> None:
    render_page_header("raio_x", total_votes=total_votes)


def _read_selected_parquet(kind: str, scope: str | None = None) -> pd.DataFrame | None:
    file_name = file_by_kind(_selected_files(scope), kind)
    if not file_name:
        return None
    try:
        return load_parquet(file_name, load_env().get("HF_TOKEN"))
    except Exception as exc:
        st.warning(f"Nao consegui ler `{kind}.parquet`: {exc}")
        return None


def _territorial_kind_select() -> str:
    options = {
        "Mesorregião": "votos_mesorregiao",
        "Município": "votos_municipio",
    }
    selected = st.selectbox(
        "Filtro territorial",
        list(options.keys()),
        key="pagina1_territorial_kind",
    )
    return options[selected]


def _territorial_map_view(df: pd.DataFrame | None, kind: str) -> pd.DataFrame | None:
    if df is None or df.empty or "qt_votos" not in df.columns:
        return df
    if kind != "votos_mesorregiao" or "nm_mesorregiao" not in df.columns:
        return df

    group_cols = ["nm_mesorregiao"]
    optional_cols = [col for col in ("cd_mesorregiao", "nr_mesorregiao") if col in df.columns]
    result = (
        df.assign(qt_votos=pd.to_numeric(df["qt_votos"], errors="coerce").fillna(0))
        .groupby(group_cols, as_index=False)
        .agg({"qt_votos": "sum", **{col: "first" for col in optional_cols}})
    )
    result["nivel_territorial"] = "mesorregiao"
    return result


def _territorial_concentration_chart(
    df: pd.DataFrame | None, kind: str, *, label_col: str | None = None,
    title: str | None = None, limit: int | None = 10,
) -> go.Figure:
    label_col = label_col or ("nm_mesorregiao" if kind == "votos_mesorregiao" else "nm_municipio")
    title = title or ("Top 10 mesorregiões" if kind == "votos_mesorregiao" else "Top 10 municípios")

    if df is None or df.empty or "qt_votos" not in df.columns or label_col not in df.columns:
        ranking = pd.DataFrame({"territorio": ["Sem dados"], "qt_votos": [0.0], "pct": [0.0]})
    else:
        ranking = df.copy()
        ranking["qt_votos"] = pd.to_numeric(ranking["qt_votos"], errors="coerce").fillna(0)
        ranking[label_col] = ranking[label_col].fillna("Nao informado").astype(str).str.strip()
        ranking.loc[ranking[label_col].eq(""), label_col] = "Nao informado"
        ranking = (
            ranking.groupby(label_col, as_index=False)["qt_votos"]
            .sum()
            .sort_values("qt_votos", ascending=False)
        )
        if limit is not None:
            ranking = ranking.head(limit)
        total_votes = float(pd.to_numeric(df["qt_votos"], errors="coerce").fillna(0).sum())
        ranking["pct"] = np.where(total_votes > 0, ranking["qt_votos"] / total_votes, 0.0)
        ranking = ranking.sort_values("qt_votos", ascending=True)
        ranking = ranking.rename(columns={label_col: "territorio"})

    ranking["qt_votos"] = pd.to_numeric(ranking["qt_votos"], errors="coerce").fillna(0)
    ranking["pct"] = pd.to_numeric(ranking["pct"], errors="coerce").fillna(0)
    max_votes = float(ranking["qt_votos"].max()) if not ranking.empty else 0.0
    if not np.isfinite(max_votes):
        max_votes = 0.0

    customdata = np.stack([ranking["qt_votos"], ranking["pct"]], axis=-1)
    trace_text = [
        f"{_format_number(votes)}<br><b>{_format_percent(pct)} dos votos</b>"
        for votes, pct in customdata
    ]
    fig = go.Figure(
        go.Bar(
            x=ranking["qt_votos"],
            y=ranking["territorio"],
            orientation="h",
            marker={
                "color": ranking["qt_votos"],
                "colorscale": [
                    [0.0, "rgba(96, 165, 250, 0.72)"],
                    [0.45, "rgba(37, 99, 235, 0.92)"],
                    [1.0, "rgba(147, 197, 253, 1.0)"],
                ],
                "line": {"color": "rgba(239,246,255,0.86)", "width": 1.5},
            },
            customdata=customdata,
            text=trace_text,
            textposition="auto",
            textfont={"color": "#f8fbff", "size": 16, "family": "Segoe UI, Inter, sans-serif"},
            insidetextfont={"color": "#ffffff", "size": 16, "family": "Segoe UI, Inter, sans-serif"},
            outsidetextfont={"color": "#f8fbff", "size": 16, "family": "Segoe UI, Inter, sans-serif"},
            cliponaxis=False,
            opacity=0.98,
            hovertemplate="<b>%{y}</b><br>Votos: %{customdata[0]:,.0f}<br>Participacao: %{customdata[1]:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(560, 150 + len(ranking) * 58),
        margin={"l": 270, "r": 46, "t": 72, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f8fbff", "size": 15, "family": "Segoe UI, Inter, sans-serif"},
        title={
            "text": title,
            "x": 0.0,
            "xanchor": "left",
            "font": {"size": 23, "color": "#f8fbff", "family": "Segoe UI, Inter, sans-serif"},
        },
        xaxis={
            "title": "",
            "showticklabels": False,
            "showgrid": False,
            "range": [0, max_votes * 1.12] if max_votes > 0 else None,
            "zeroline": False,
        },
        yaxis={
            "title": "",
            "tickfont": {"size": 16, "color": "#f8fbff"},
            "automargin": True,
            "ticks": "",
            "showgrid": False,
            "zeroline": False,
        },
        coloraxis_showscale=False,
        bargap=0.12,
    )
    return fig


def _selected_territory(event: object, kind: str) -> str:
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection", {})
    points = selection.get("points", []) if isinstance(selection, dict) else getattr(selection, "points", [])
    if not points:
        return ""
    point = points[0]
    customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    if kind == "votos_mesorregiao" and customdata and isinstance(customdata[0], str):
        return customdata[0]
    location = point.get("location") if isinstance(point, dict) else getattr(point, "location", None)
    if not location:
        return ""
    if kind == "votos_mesorregiao":
        return str(location)
    _, _, municipalities, _ = load_geo_reference()
    match = municipalities[municipalities["codigo_ibge"].astype("string").eq(str(location))]
    return str(match.iloc[0]["nome"]) if not match.empty else ""


@st.dialog("Detalhamento territorial", width="large")
def _territorial_drilldown(territory: str, kind: str, municipal_votes: pd.DataFrame | None,
                            neighborhood_votes: pd.DataFrame | None) -> None:
    st.subheader(territory)
    if kind == "votos_mesorregiao":
        source = municipal_votes
        region_col, label_col = "nm_mesorregiao", "nm_municipio"
        title = "Votos por município"
    else:
        source = neighborhood_votes
        region_col, label_col = "nm_municipio", "nm_bairro"
        title = "Votos por bairro"
    if source is None or source.empty or not {region_col, label_col, "qt_votos"}.issubset(source.columns):
        st.info("Dados do detalhamento indisponíveis para este território.")
        return
    selected = source[source[region_col].map(_normalized_text).eq(_normalized_text(territory))].copy()
    if selected.empty:
        st.info("Nenhum voto detalhado disponível para este território.")
        return
    selected[label_col] = selected[label_col].fillna("Não informado").astype(str).str.strip().replace("", "Não informado")
    st.plotly_chart(_territorial_concentration_chart(
        selected, kind, label_col=label_col, title=title, limit=None,
    ), width="stretch", key="pagina1_drilldown_chart")


def _normalized_text(value: object) -> str:
    return " ".join("".join(
        char for char in unicodedata.normalize("NFKD", str(value or "").strip().upper())
        if not unicodedata.combining(char)
    ).split())


def _map_side_card(title: str, value: str, caption: str, badge: str = "", tone: str = "") -> str:
    badge_html = (
        f'<div class="raiox-map-side-badge {tone}">{html.escape(badge)}</div>'
        if badge else ""
    )
    return (
        '<div class="raiox-map-side-card">'
        f'<div class="raiox-map-side-label">{html.escape(title)}</div>'
        f'<div class="raiox-map-side-value">{html.escape(value)}</div>'
        f'<div class="raiox-map-side-caption">{html.escape(caption)}</div>'
        f'{badge_html}</div>'
    )


def _render_map_side_cards(df: pd.DataFrame | None) -> None:
    card = _map_side_card

    cards = []
    municipal = pd.DataFrame()
    if df is not None and not df.empty and {"nm_municipio", "qt_votos"}.issubset(df.columns):
        municipal = df.copy()
        if "nivel_territorial" in municipal.columns:
            city_rows = municipal[municipal["nivel_territorial"].astype(str).str.lower().eq("municipio")]
            if not city_rows.empty:
                municipal = city_rows
        municipal["qt_votos"] = pd.to_numeric(municipal["qt_votos"], errors="coerce").fillna(0)
        municipal["nm_municipio"] = municipal["nm_municipio"].fillna("").astype(str).str.strip()
        municipal = municipal[municipal["nm_municipio"].ne("")]

    _, _, municipalities_ref, _ = load_geo_reference()
    state_cities = (
        int(municipalities_ref["codigo_ibge"].nunique())
        if municipalities_ref is not None and not municipalities_ref.empty else 853
    )
    if municipal.empty:
        cards.extend([
            card("Município principal (Top 1)", "—", "Votos municipais indisponíveis"),
            card("Dependência do reduto principal", "—", "Votos municipais indisponíveis"),
            card("Penetração territorial", "—", "Votos municipais indisponíveis"),
            card("Densidade média por município", "—", "Votos municipais indisponíveis"),
        ])
    else:
        by_city = municipal.groupby(municipal["nm_municipio"].map(_normalized_text))["qt_votos"].sum()
        by_city = by_city[by_city.index != ""]
        total = float(by_city.sum())
        with_votes = int(by_city.gt(0).sum())
        leader_share = float(by_city.max() / total) if total > 0 and not by_city.empty else 0.0
        leader_key = str(by_city.idxmax()) if not by_city.empty else ""
        leader_rows = municipal[municipal["nm_municipio"].map(_normalized_text).eq(leader_key)]
        leader_name = str(leader_rows.iloc[0]["nm_municipio"]).title() if not leader_rows.empty else "—"
        leader_votes = float(by_city.max()) if not by_city.empty else 0.0
        cards.append(card(
            "Município principal (Top 1)",
            f"{leader_name} ({_format_percent(leader_share)})" if total > 0 else "—",
            f"{_format_number(leader_votes)} votos na cidade líder" if total > 0 else "Sem votos municipais",
            "Alta concentração" if leader_share > 0.30 else "Município líder",
            "warn" if leader_share > 0.30 else "good",
        ))
        cards.append(card(
            "Dependência do reduto principal", _format_percent(leader_share) if total > 0 else "—",
            "Dos votos no município líder" if total > 0 else "Sem votos municipais",
            "Alerta de concentração" if leader_share > 0.30 else "Concentração moderada",
            "warn" if leader_share > 0.30 else "good",
        ))
        reach = with_votes / state_cities if state_cities else 0.0
        cards.append(card(
            "Penetração territorial", f"{_format_number(with_votes)} / {_format_number(state_cities)}",
            f"{_format_percent(reach)} dos municípios do estado",
            "Presença em mais da metade do estado" if reach >= 0.5 else "Presença em menos da metade do estado",
            "good" if reach >= 0.5 else "warn",
        ))
        cards.append(card(
            "Densidade média por município",
            f"{_format_number(round(total / with_votes))} votos / município" if with_votes else "—",
            f"Considerando apenas os {_format_number(with_votes)} municípios com voto",
        ))
    st.markdown('<div class="raiox-map-side-cards">' + "".join(cards) + '</div>', unsafe_allow_html=True)


def _render_local_politics_cards(
    summaries: list[dict[str, object]],
    selected_class: str | None,
) -> None:
    card_copy = {
        "Máquina eficiente": (
            "Apoio local forte e votação acima da média estadual.",
            "Manter e fortalecer",
        ),
        "Traição ou máquina inoperante": (
            "Há aliados locais, mas a votação ficou abaixo da média estadual.",
            "Revisar articulação",
        ),
        "Voto orgânico / opinião": (
            "Boa votação mesmo sem uma estrutura política local forte.",
            "Construir novas alianças",
        ),
        "Sem penetração": (
            "Pouco apoio local e votação abaixo da média estadual.",
            "Priorizar com critério",
        ),
    }
    if not summaries:
        st.info("Indicadores de força política local indisponíveis.")
        return

    style_rules = []
    for index, summary in enumerate(summaries):
        classification = str(summary["classification"])
        color = LOCAL_STRENGTH_COLORS[classification]
        is_selected = classification == selected_class
        selected_shadow = (
            f"0 0 0 2px {color}, 0 14px 32px rgba(1,8,24,.34)"
            if is_selected else "0 12px 30px rgba(1,8,24,.22)"
        )
        card_background = (
            f"radial-gradient(circle at 0% 0%, {color}52 0%, {color}26 42%, transparent 72%), "
            f"linear-gradient(145deg, {color}30 0%, rgba(7,24,54,.76) 58%, {color}12 100%)"
            if is_selected
            else (
                f"radial-gradient(circle at 0% 0%, {color}38 0%, {color}18 42%, transparent 72%), "
                f"linear-gradient(145deg, {color}24 0%, rgba(7,24,54,.72) 58%, {color}0d 100%)"
            )
        )
        wrapper_margin = "0" if index == len(summaries) - 1 else "0 0 .55rem 0"
        style_rules.append(f"""
        .st-key-pagina1_forca_local_card_{index} {{
            margin: {wrapper_margin};
        }}
        .st-key-pagina1_forca_local_card_{index} button {{
            min-height: 10.65rem;
            height: auto;
            align-items: flex-start;
            justify-content: flex-start;
            padding: .82rem .95rem .86rem;
            border: 1px solid {color}66;
            border-radius: 16px;
            background: {card_background};
            box-shadow: {selected_shadow};
            color: #eaf2ff;
            text-align: left;
            backdrop-filter: blur(7px);
            -webkit-backdrop-filter: blur(7px);
        }}
        .st-key-pagina1_forca_local_card_{index} button:hover {{
            border-color: {color};
            background:
                radial-gradient(circle at 0% 0%, {color}52 0%, {color}28 44%, transparent 74%),
                linear-gradient(145deg, {color}30 0%, rgba(7,24,54,.78) 58%, {color}14 100%);
            color: #ffffff;
        }}
        .st-key-pagina1_forca_local_card_{index} button p {{
            white-space: pre-line;
            width: 100%;
            margin: 0;
            text-align: left;
            line-height: 1.28;
        }}
        .st-key-pagina1_forca_local_card_{index} button p br {{
            display: block;
            content: "";
            margin-top: 0.42rem;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:first-of-type {{
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            padding: 0.28rem 0.52rem;
            border: 1px solid {color}99;
            border-radius: 999px;
            background: {color}2b;
            color: #f8fbff;
            font-size: 0.72rem;
            font-weight: 900;
            line-height: 1.2;
            letter-spacing: 0.035em;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(2),
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(3) {{
            color: #ffffff;
            font-size: 1.12rem;
            font-weight: 900;
            line-height: 1.08;
        }}
        .st-key-pagina1_forca_local_card_{index} button p strong:nth-of-type(4) {{
            color: #b7c7e6;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }}
        .st-key-pagina1_forca_local_card_{index} button p em {{
            color: #dbeafe;
            font-style: normal;
            font-weight: 750;
        }}
        .st-key-pagina1_forca_local_card_{index} button p code {{
            display: inline-block;
            max-width: 100%;
            padding: 0.34rem 0.56rem;
            border: 1px solid {color}73;
            border-radius: 999px;
            background: {color}24;
            color: #f8fbff;
            font-family: inherit;
            font-size: 0.72rem;
            font-weight: 800;
            line-height: 1.25;
            white-space: normal;
        }}
        """)
    st.html("<style>" + "".join(style_rules) + "</style>")

    for index, summary in enumerate(summaries):
        classification = str(summary["classification"])
        title = LOCAL_STRENGTH_LABELS[classification]
        icon = LOCAL_STRENGTH_ICONS[classification]
        description, action = card_copy[classification]
        municipalities = int(summary["municipalities"])
        vote_share = float(summary["vote_share"])
        leader = str(summary["leader"])
        leader_votes = float(summary["leader_votes"])
        selected_suffix = " · EXIBINDO" if classification == selected_class else ""
        cities_label = "Cidade" if municipalities == 1 else "Cidades"
        label = (
            f"**{icon} {title.upper()}{selected_suffix}**  \n"
            f"**{_format_number(municipalities)} {cities_label}** | "
            f"**{_format_percent(vote_share)} da sua votação**  \n"
            f"**Cidade-chave:** {leader} *({_format_number(leader_votes)} votos)*  \n"
            f"`Estratégia · {action}`"
        )
        if st.button(
            label,
            key=f"pagina1_forca_local_card_{index}",
            use_container_width=True,
            help=description,
        ):
            st.session_state[LOCAL_STRENGTH_SELECTION_KEY] = (
                None if classification == selected_class else classification
            )
            st.rerun()


def _render_local_strength_map_legend(statewide_market_share: float | None) -> None:
    reference = (
        f"{statewide_market_share:.2f}%"
        if statewide_market_share is not None
        else "a participação estadual"
    )
    legend_items = [
        (
            "Máquina eficiente",
            "🟢 Prefeito/vereadores entregaram votos",
        ),
        (
            "Traição ou máquina inoperante",
            "🔴 Prefeito/vereadores não entregaram votos",
        ),
        (
            "Voto orgânico / opinião",
            "🔵 Votação própria sem prefeito/vereadores",
        ),
        (
            "Sem penetração",
            "⚪ Sem prefeito/vereadores e sem votos",
        ),
    ]
    items_html = "".join(
        f"""
        <div class="raiox-local-map-legend-item" style="--local-color: {html.escape(LOCAL_STRENGTH_COLORS[classification])};">
            <span>{html.escape(copy)}</span>
        </div>
        """
        for classification, copy in legend_items
    )
    st.html(
        f"""
        <style>
        .st-key-pagina1_forca_local_map_card [data-testid="stVerticalBlockBorderWrapper"] {{
            min-height: 50rem;
            padding: 0.92rem 1rem 1rem !important;
        }}
        .raiox-local-map-legend {{
            margin: 0 0 0.6rem;
            padding: 0.12rem 0 0.78rem;
            border-bottom: 1px solid rgba(177, 211, 255, 0.16);
        }}
        .raiox-local-map-legend-title {{
            display: none;
        }}
        .raiox-local-map-legend-note {{
            max-width: 60rem;
            margin: 0 auto;
            color: #f8fbff;
            font-size: 0.86rem;
            font-weight: 850;
            line-height: 1.42;
            text-align: center;
        }}
        .raiox-local-map-legend-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.5rem;
            margin-top: 0.64rem;
        }}
        .raiox-local-map-legend-item {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 2.55rem;
            padding: 0.4rem 0.66rem;
            border: 1px solid color-mix(in srgb, var(--local-color), transparent 36%);
            border-radius: 999px;
            background: color-mix(in srgb, var(--local-color), transparent 84%);
            color: #eaf2ff;
            font-size: 0.7rem;
            font-weight: 800;
            line-height: 1.18;
            letter-spacing: 0;
            text-align: center;
        }}
        @media (max-width: 900px) {{
            .st-key-pagina1_forca_local_map_card [data-testid="stVerticalBlockBorderWrapper"] {{
                min-height: 0;
            }}
            .raiox-local-map-legend-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
        }}
        @media (max-width: 560px) {{
            .raiox-local-map-legend-grid {{
                grid-template-columns: 1fr;
            }}
            .raiox-local-map-legend-item {{
                border-radius: 14px;
            }}
        }}
        </style>
        <div class="raiox-local-map-legend">
            <div class="raiox-local-map-legend-note">
                Avalia a eficácia de prefeitos e vereadores aliados na transferência de votos.
                Considera-se votação alta quando o seu percentual na cidade supera a sua média no estado ({html.escape(reference)}).
            </div>
            <div class="raiox-local-map-legend-grid">
                {items_html}
            </div>
        </div>
        """
    )


def _local_politics_map_selection(event: object | None) -> dict[str, str]:
    if event is None:
        return {}
    if hasattr(event, "selection"):
        selection = getattr(event, "selection")
    elif isinstance(event, dict):
        selection = event.get("selection", {})
    else:
        selection = {}
    points = (
        selection.get("points", [])
        if isinstance(selection, dict)
        else getattr(selection, "points", [])
    )
    if not points:
        return {}

    point = points[0]
    customdata = (
        point.get("customdata")
        if isinstance(point, dict)
        else getattr(point, "customdata", None)
    )
    customdata = list(customdata) if customdata is not None else []
    location = (
        point.get("location")
        if isinstance(point, dict)
        else getattr(point, "location", None)
    )
    code = str(location or (customdata[5] if len(customdata) > 5 else "")).strip()
    municipality = str(customdata[6] if len(customdata) > 6 else "").strip()
    if not municipality:
        hovertext = (
            point.get("hovertext")
            if isinstance(point, dict)
            else getattr(point, "hovertext", None)
        )
        municipality = str(hovertext or "").strip()
    if not municipality and code:
        _, _, municipalities, _ = load_geo_reference()
        if municipalities is not None and not municipalities.empty:
            match = municipalities[
                municipalities["codigo_ibge"].astype("string").eq(code)
            ]
            if not match.empty:
                municipality = str(match.iloc[0]["nome"])
    classification = str(customdata[0] if customdata else "").strip()
    if not code or not municipality or classification not in LOCAL_STRENGTH_COLORS:
        return {}
    return {
        "codigo_ibge": code,
        "municipio": municipality,
        "classificacao": classification,
    }


def _format_percentage_points(value: object, digits: int = 1) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "—"
    return f"{float(numeric):.{digits}f}%".replace(".", ",")


def _format_score(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "—"
    return f"{float(numeric):.1f}/100".replace(".", ",")


def _local_political_link_label(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    labels = {
        "mesmo_partido": "Mesmo partido",
        "federacao": "Federação partidária",
        "partido_aliado": "Partido aliado",
        "aliado": "Aliado",
        "sem_vinculo": "Sem vínculo partidário",
    }
    return labels.get(normalized, normalized.replace("_", " ").title() or "Não informado")


@st.dialog("Força política local", width="large")
def _local_politics_municipality_dialog(
    selection: dict[str, str],
    capital_local_df: pd.DataFrame | None,
    votes_df: pd.DataFrame | None,
    elected_df: pd.DataFrame | None,
    statewide_market_share: float | None,
) -> None:
    municipality = selection["municipio"]
    municipality_key = _normalized_text(municipality)
    classification = selection["classificacao"]
    code = selection["codigo_ibge"]
    color = LOCAL_STRENGTH_COLORS[classification]
    icon = LOCAL_STRENGTH_ICONS[classification]
    reading, criteria = LOCAL_STRENGTH_LEGEND[classification]

    capital_rows = pd.DataFrame()
    if (
        capital_local_df is not None
        and not capital_local_df.empty
        and "nm_municipio" in capital_local_df.columns
    ):
        capital_rows = capital_local_df[
            capital_local_df["nm_municipio"]
            .map(_normalized_text)
            .eq(municipality_key)
        ].copy()
    if capital_rows.empty:
        st.subheader(municipality.title())
        st.info("Os detalhes de força local deste município não estão disponíveis.")
        return
    capital = capital_rows.iloc[0]

    municipal_votes = pd.DataFrame()
    if votes_df is not None and not votes_df.empty and "nm_municipio" in votes_df.columns:
        municipal_votes = votes_df.copy()
        if "nivel_territorial" in municipal_votes.columns:
            level = municipal_votes["nivel_territorial"].astype(str).str.casefold()
            if level.eq("municipio").any():
                municipal_votes = municipal_votes[level.eq("municipio")].copy()
        municipal_votes = municipal_votes[
            municipal_votes["nm_municipio"]
            .map(_normalized_text)
            .eq(municipality_key)
        ]

    votes = pd.to_numeric(
        municipal_votes.get("qt_votos", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0).sum()
    if votes <= 0:
        selected_year = str(
            st.session_state.get("deputados_filters", {}).get("ano")
            or DEFAULT_VISUALIZATION_YEAR
        )
        votes = pd.to_numeric(
            pd.Series([capital.get(f"qt_votos_candidato_{selected_year}")]),
            errors="coerce",
        ).fillna(0).iloc[0]
    market_share_values = pd.to_numeric(
        municipal_votes.get("pct_market_share", pd.Series(dtype=float)),
        errors="coerce",
    ).dropna()
    market_share = (
        float(market_share_values.iloc[0])
        if not market_share_values.empty
        else None
    )

    strategic_reading = {
        "Máquina eficiente": (
            "A estrutura política local é forte e o desempenho eleitoral ficou "
            "acima da referência estadual. Aqui, o apoio se converteu em voto."
        ),
        "Traição ou máquina inoperante": (
            "Existe estrutura política local, mas o desempenho ficou abaixo da "
            "referência estadual. Vale revisar a entrega e o engajamento dos aliados."
        ),
        "Voto orgânico / opinião": (
            "O município entregou votação acima da referência mesmo sem uma "
            "estrutura local forte. Há espaço para transformar apoio popular em alianças."
        ),
        "Sem penetração": (
            "A estrutura local e o desempenho eleitoral estão abaixo dos cortes. "
            "É um território para priorizar somente com objetivo e estratégia claros."
        ),
    }

    st.markdown(f"## {html.escape(municipality.title())}")
    st.markdown(
        f"""
        <div style="
            display:inline-flex;align-items:center;gap:.55rem;padding:.45rem .75rem;
            margin:.05rem 0 .8rem;border:1px solid {color};border-radius:999px;
            background:rgba(8,28,64,.72);color:#f8fbff;font-weight:800;">
            <span style="width:.72rem;height:.72rem;border-radius:50%;background:{color};"></span>
            {icon} {html.escape(reading)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_columns = st.columns(4, gap="small")
    metric_columns[0].metric("Votos no município", _format_number(votes))
    metric_columns[1].metric(
        "Market share local",
        _format_percentage_points(market_share, 2),
    )
    metric_columns[2].metric(
        "Referência estadual",
        _format_percentage_points(statewide_market_share, 2),
    )
    metric_columns[3].metric(
        "Capital político local",
        _format_score(capital.get("capital_local_0a100")),
    )
    st.info(strategic_reading[classification])
    st.caption(f"Critério da cor: {criteria}.")

    map_column, composition_column = st.columns([0.43, 0.57], gap="large")
    with map_column:
        st.markdown("#### Mapa do município")
        municipality_fig = local_political_strength_municipality_map(
            code,
            municipality,
            classification,
        )
        if municipality_fig is not None:
            st.plotly_chart(
                municipality_fig,
                width="stretch",
                height=330,
                key=f"pagina1_forca_local_detalhe_mapa_{code}",
                config={"displayModeBar": False},
            )
        else:
            st.info("Malha municipal indisponível.")

        mayor_party = str(capital.get("sg_partido_prefeito_2024") or "Não informado")
        mayor_link = _local_political_link_label(capital.get("vinculo_prefeito"))
        council_total = int(
            pd.to_numeric(
                pd.Series([capital.get("qt_vereadores_camara")]),
                errors="coerce",
            ).fillna(0).iloc[0]
        )
        council_allies = int(
            pd.to_numeric(
                pd.Series([capital.get("qt_vereadores_aliados")]),
                errors="coerce",
            ).fillna(0).iloc[0]
        )
        allied_parties = str(capital.get("partidos_aliados") or "Não informado")
        base_year = str(capital.get("ano_base_eleitos") or "Não informado")
        data_status = str(capital.get("situacao_dados") or "Não informado")
        detail_cards = [
            (
                "Prefeitura",
                f"{mayor_party} · {mayor_link}",
                f"Contribuição para a nota: {_format_score(capital.get('pontos_prefeito'))}",
            ),
            (
                "Câmara municipal",
                f"{council_allies} aliados em {council_total} vereadores",
                (
                    f"{_format_percentage_points(capital.get('pct_vereadores_aliados_camara'))} "
                    f"da Câmara · contribuição: {_format_score(capital.get('pontos_camara'))}"
                ),
            ),
            (
                "Partidos considerados aliados",
                allied_parties,
                (
                    "Capital apenas do mesmo partido: "
                    f"{_format_score(capital.get('capital_local_mesmo_partido_0a100'))}"
                ),
            ),
            (
                "Base dos dados",
                f"Eleitos em {base_year}",
                (
                    f"Faixa {str(capital.get('faixa_capital_local') or 'não informada').title()} "
                    f"· situação {data_status.replace('_', ' ')}"
                ),
            ),
        ]
        cards_html = "".join(
            (
                '<div style="padding:.75rem .85rem;border:1px solid rgba(177,211,255,.24);'
                'border-radius:12px;background:rgba(8,28,64,.5);margin:.55rem 0;">'
                f'<div style="color:#93c5fd;font-size:.72rem;font-weight:850;'
                f'text-transform:uppercase;">{html.escape(label)}</div>'
                f'<div style="color:#f8fbff;font-weight:800;margin-top:.2rem;">'
                f'{html.escape(value)}</div>'
                f'<div style="color:#b7c7e6;font-size:.78rem;margin-top:.15rem;">'
                f'{html.escape(caption)}</div></div>'
            )
            for label, value, caption in detail_cards
        )
        st.markdown(cards_html, unsafe_allow_html=True)

    with composition_column:
        st.markdown("#### Prefeito e vereadores")
        local_elected = pd.DataFrame()
        if elected_df is not None and not elected_df.empty:
            municipality_code = str(capital.get("cd_municipio") or "").strip()
            if municipality_code and "cd_municipio" in elected_df.columns:
                local_elected = elected_df[
                    elected_df["cd_municipio"].astype("string").str.strip().eq(
                        municipality_code
                    )
                ].copy()
            if local_elected.empty and "nm_municipio" in elected_df.columns:
                local_elected = elected_df[
                    elected_df["nm_municipio"]
                    .map(_normalized_text)
                    .eq(municipality_key)
                ].copy()

        if local_elected.empty:
            st.info("A composição nominal deste município não está disponível.")
        else:
            for column in (
                "cargo_eleito",
                "nm_eleito",
                "sg_partido_eleito",
                "vinculo_politico",
                "afinidade_eleito_0a100",
            ):
                if column not in local_elected.columns:
                    local_elected[column] = None
            local_elected["_cargo_ordem"] = (
                local_elected["cargo_eleito"]
                .astype(str)
                .str.casefold()
                .map(lambda value: 0 if "prefeit" in value else 1)
            )
            local_elected["afinidade_eleito_0a100"] = pd.to_numeric(
                local_elected["afinidade_eleito_0a100"],
                errors="coerce",
            )
            local_elected = local_elected.sort_values(
                ["_cargo_ordem", "afinidade_eleito_0a100", "nm_eleito"],
                ascending=[True, False, True],
            )
            composition = pd.DataFrame(
                {
                    "Cargo": local_elected["cargo_eleito"].map(
                        lambda value: (
                            "Prefeito"
                            if "prefeit" in str(value).casefold()
                            else "Vereador"
                        )
                    ),
                    "Nome": local_elected["nm_eleito"].fillna("Não informado").map(
                        lambda value: str(value).title()
                    ),
                    "Partido": local_elected["sg_partido_eleito"].fillna("—"),
                    "Vínculo": local_elected["vinculo_politico"].map(
                        _local_political_link_label
                    ),
                    "Afinidade": local_elected["afinidade_eleito_0a100"],
                }
            )
            mayor_count = int(composition["Cargo"].eq("Prefeito").sum())
            council_count = int(composition["Cargo"].eq("Vereador").sum())
            st.caption(
                f"{mayor_count} prefeito · {council_count} vereadores · "
                f"base eleitoral municipal de {base_year}"
            )
            st.dataframe(
                composition,
                hide_index=True,
                width="stretch",
                height=590,
                column_config={
                    "Cargo": st.column_config.TextColumn(width="small"),
                    "Nome": st.column_config.TextColumn(width="medium"),
                    "Partido": st.column_config.TextColumn(width="small"),
                    "Vínculo": st.column_config.TextColumn(width="medium"),
                    "Afinidade": st.column_config.NumberColumn(
                        "Afinidade",
                        help="Afinidade política e eleitoral do eleito com o candidato, de 0 a 100.",
                        format="%.1f",
                    ),
                },
            )


def _render_neighborhood_side_cards(df: pd.DataFrame | None, municipality_code: str | None) -> None:
    card = _map_side_card
    required = {"cd_ibge_municipio", "nm_bairro", "qt_votos"}
    municipality_rows = pd.DataFrame()
    rows = pd.DataFrame()
    if df is not None and municipality_code is not None and required.issubset(df.columns):
        codes = df["cd_ibge_municipio"].astype("string")
        municipality_rows = df.loc[codes.eq(str(municipality_code))].copy()
        rows = municipality_rows[["nm_bairro", "qt_votos"]].copy()
        rows["nm_bairro"] = rows["nm_bairro"].fillna("").astype(str).str.strip()
        rows["qt_votos"] = pd.to_numeric(rows["qt_votos"], errors="coerce").fillna(0)
        rows = rows.loc[rows["nm_bairro"].ne("")]

    municipality_total = pd.to_numeric(
        municipality_rows.get("qt_votos", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0).sum()
    cards = [
        card(
            "Votos em Belo Horizonte (2026)",
            _format_number(municipality_total) if not municipality_rows.empty else "—",
            "Total municipal",
        )
    ]
    if rows.empty:
        cards.extend([
            card("Bairro principal (Top 1)", "—", "Dados de bairros indisponíveis"),
            card("Dependência do bairro principal", "—", "Dados de bairros indisponíveis"),
            card("Penetração por bairros", "—", "Dados de bairros indisponíveis"),
            card("Densidade média por bairro", "—", "Dados de bairros indisponíveis"),
        ])
    else:
        rows["_bairro"] = rows["nm_bairro"].map(_normalized_text)
        by_name = rows.groupby("_bairro")["qt_votos"].sum()
        by_name = by_name.loc[by_name.index != ""]
        total = float(by_name.sum())
        with_votes = int(by_name.gt(0).sum())
        leader_key = str(by_name.idxmax()) if total > 0 else ""
        leader_name = (
            str(rows.loc[rows["_bairro"].eq(leader_key), "nm_bairro"].iloc[0]).title()
            if leader_key else "—"
        )
        leader_votes = float(by_name.max()) if total > 0 else 0.0
        share = leader_votes / total if total > 0 else 0.0
        cards.extend([
            card(
                "Bairro principal (Top 1)",
                f"{leader_name} ({_format_percent(share)})" if total > 0 else "—",
                f"{_format_number(leader_votes)} votos no bairro líder" if total > 0 else "Sem votos por bairro",
                "Alta concentração" if share > 0.30 else "Bairro líder",
                "warn" if share > 0.30 else "good",
            ),
            card(
                "Dependência do bairro principal",
                _format_percent(share) if total > 0 else "—",
                "Dos votos nos bairros do município" if total > 0 else "Sem votos por bairro",
                "Alerta de concentração" if share > 0.30 else "Concentração moderada",
                "warn" if share > 0.30 else "good",
            ),
            card(
                "Penetração por bairros",
                f"{_format_number(with_votes)} bairros com voto",
                "Total de bairros do município indisponível",
            ),
            card(
                "Densidade média por bairro",
                f"{_format_number(round(total / with_votes))} votos / bairro" if with_votes else "—",
                f"Considerando apenas os {_format_number(with_votes)} bairros com voto" if with_votes else "Sem votos por bairro",
            ),
        ])
    st.markdown('<div class="raiox-map-side-cards">' + "".join(cards) + '</div>', unsafe_allow_html=True)


def _render_bh_comparison_legend() -> None:
    st.markdown(
        '''<div style="display:flex;flex-wrap:wrap;gap:12px;margin:0 0 8px;color:#dbeafe;font-size:.76rem">
            <span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#22c55e;margin-right:5px"></i>Ganhou participação</span>
            <span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#3b82f6;margin-right:5px"></i>Sem variação</span>
            <span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#ef4444;margin-right:5px"></i>Perdeu participação</span>
            <span><i style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#94a3b8;margin-right:5px"></i>Sem comparação</span>
        </div>''',
        unsafe_allow_html=True,
    )


def _municipal_concentration_frame(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty or not {"nm_municipio", "qt_votos"}.issubset(df.columns):
        return pd.DataFrame()

    result = df.copy()
    if "nivel_territorial" in result.columns:
        municipal = result[
            result["nivel_territorial"].astype(str).str.strip().str.lower().eq("municipio")
        ].copy()
        if not municipal.empty:
            result = municipal

    result["nm_municipio"] = result["nm_municipio"].fillna("").astype(str).str.strip()
    result["qt_votos"] = pd.to_numeric(result["qt_votos"], errors="coerce").fillna(0)
    result = result[result["nm_municipio"].ne("") & result["qt_votos"].gt(0)]
    if result.empty:
        return pd.DataFrame()

    agg_map = {"qt_votos": "sum"}
    if "qt_secoes_com_voto" in result.columns:
        result["qt_secoes_com_voto"] = pd.to_numeric(
            result["qt_secoes_com_voto"], errors="coerce"
        ).fillna(0)
        agg_map["qt_secoes_com_voto"] = "sum"

    result = (
        result.groupby("nm_municipio", as_index=False)
        .agg(agg_map)
        .sort_values("qt_votos", ascending=False)
        .reset_index(drop=True)
    )
    votos_total = float(result["qt_votos"].sum())
    if votos_total <= 0:
        return pd.DataFrame()

    result["rank_municipio"] = np.arange(1, len(result) + 1)
    result["pct_votos"] = result["qt_votos"] / votos_total
    result["votos_acumulados"] = result["qt_votos"].cumsum()
    result["pct_acumulado"] = result["votos_acumulados"] / votos_total
    return result


def _concentration_reference_rows(concentration_df: pd.DataFrame) -> pd.DataFrame:
    if concentration_df.empty:
        return pd.DataFrame()
    total_rows = len(concentration_df)
    points = [point for point in (1, 5, 15, 20) if point <= total_rows]
    if total_rows not in points:
        points.append(total_rows)
    rows = concentration_df.iloc[[point - 1 for point in points]].copy()
    rows["referencia"] = [f"Top {point}" if point < total_rows else "Todos" for point in points]
    rows["referencia_rank"] = points
    return rows


def _accumulated_concentration_chart(concentration_df: pd.DataFrame, max_rank: int | None = None) -> go.Figure:
    if concentration_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados municipais indisponiveis.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": "#eaf2ff", "size": 16},
        )
        fig.update_layout(height=390, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    chart_df = concentration_df.copy()
    if max_rank is not None and max_rank > 0:
        chart_df = chart_df[chart_df["rank_municipio"].le(max_rank)].copy()
    if chart_df.empty:
        chart_df = concentration_df.head(1).copy()

    ref_df = _concentration_reference_rows(concentration_df)
    max_rank_value = int(chart_df["rank_municipio"].max())
    x_axis_max = max(1.0, np.log10(max_rank_value) * 1.03)
    y_axis_max = 100
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_df["rank_municipio"],
            y=chart_df["pct_acumulado"] * 100,
            mode="lines",
            fill="tozeroy",
            line={"color": "#7DD3FC", "width": 3.4},
            fillcolor="rgba(59, 130, 246, 0.16)",
            customdata=np.stack(
                [
                    chart_df["votos_acumulados"],
                    chart_df["pct_acumulado"],
                    chart_df["nm_municipio"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "<b>Top %{x:.0f} municípios</b><br>"
                "%{customdata[0]:,.0f} votos acumulados<br>"
                "%{customdata[1]:.1%} da votação total<br>"
                "Município na posição: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    if not ref_df.empty:
        marker_positions = []
        for rank, label in zip(ref_df["rank_municipio"], ref_df["referencia"]):
            if int(rank) == 1:
                marker_positions.append("middle right")
            elif int(rank) == 5:
                marker_positions.append("bottom center")
            elif int(rank) in (15, 20):
                marker_positions.append("top center")
            elif int(rank) == max_rank_value:
                marker_positions.append("middle left")
            elif str(label) == "Todos":
                marker_positions.append("middle left")
            else:
                marker_positions.append("top center")
        fig.add_trace(
            go.Scatter(
                x=ref_df["rank_municipio"],
                y=ref_df["pct_acumulado"] * 100,
                mode="markers+text",
                marker={
                    "size": 15,
                    "color": "#FFFFFF",
                    "line": {"color": "#38BDF8", "width": 3.5},
                    "symbol": "circle",
                },
                text=ref_df["referencia"],
                textposition=marker_positions,
                textfont={"color": "#FFFFFF", "size": 13, "family": "Segoe UI, Inter, sans-serif"},
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "%{customdata[0]:,.0f} votos acumulados<br>"
                    "%{customdata[1]:.1%} da votação total<extra></extra>"
                ),
                customdata=np.stack(
                    [ref_df["votos_acumulados"], ref_df["pct_acumulado"], ref_df["referencia_rank"]],
                    axis=-1,
                ),
                showlegend=False,
            )
        )
    tick_values = []
    for value in (1, 5, 15, 20, 50, 100, 250, 500, max_rank_value):
        if value <= max_rank_value and value not in tick_values:
            tick_values.append(value)
    fig.update_layout(
        height=430,
        margin={"l": 46, "r": 78, "t": 20, "b": 48},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        xaxis={
            "title": "Municípios acumulados",
            "type": "log",
            "range": [0, x_axis_max],
            "tickmode": "array",
            "tickvals": tick_values,
            "ticktext": [
                "Todos" if value == max_rank_value else str(value)
                for value in tick_values
            ],
            "gridcolor": "rgba(255,255,255,0.08)",
            "zeroline": False,
        },
        yaxis={
            "title": "% da Votação Total",
            "range": [0, y_axis_max],
            "ticksuffix": "%",
            "gridcolor": "rgba(255,255,255,0.12)",
            "zeroline": False,
        },
        shapes=[
            {
                "type": "rect",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": 0,
                "y1": 100,
                "fillcolor": "rgba(56, 189, 248, 0.055)",
                "line": {"width": 0},
                "layer": "below",
            },
        ]
        + [
            {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": level,
                "y1": level,
                "line": {
                    "color": "rgba(125, 211, 252, 0.72)" if level == 100 else "rgba(226, 232, 240, 0.16)",
                    "width": 2.4 if level == 100 else 1,
                    "dash": "solid" if level == 100 else "dot",
                },
            }
            for level in (25, 50, 75, 100)
        ],
        annotations=[
            {
                "xref": "paper",
                "x": 1.0,
                "xanchor": "right",
                "yref": "y",
                "y": level,
                "text": f"{level}%",
                "showarrow": False,
                "font": {
                    "color": "#E0F2FE" if level == 100 else "rgba(226, 232, 240, 0.72)",
                    "size": 12 if level == 100 else 10,
                },
                "bgcolor": "rgba(8, 47, 73, 0.82)" if level == 100 else "rgba(5, 12, 28, 0.62)",
                "borderpad": 3 if level == 100 else 2,
            }
            for level in (25, 50, 75, 100)
        ],
        hoverlabel={
            "bgcolor": "rgba(5,12,28,0.95)",
            "font_color": "#EAF2FF",
            "bordercolor": "rgba(147,197,253,0.55)",
        },
    )
    return fig


CONCENTRATION_STEPS = (
    (1, "Top 1", "#2563eb"),
    (5, "Top 2–5", "#3b82f6"),
    (15, "Top 6–15", "#38bdf8"),
    (20, "Top 16–20", "#60a5fa"),
)


def _concentration_donut(share: float, color: str) -> go.Figure:
    progress = max(0.0, min(1.0, float(share)))
    stroke_width = 28
    background_theta = np.linspace(0, 360, 241)
    # Start at 12 o'clock and move clockwise.
    progress_theta = np.linspace(90, 90 - (360 * progress), max(2, int(180 * progress) + 2))
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=np.ones(len(background_theta)),
        theta=background_theta,
        mode="lines",
        line={"color": "rgba(20, 48, 88, 0.92)", "width": stroke_width},
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_trace(go.Scatterpolar(
        r=np.ones(len(progress_theta)),
        theta=progress_theta,
        mode="lines",
        line={"color": color, "width": stroke_width, "shape": "spline", "smoothing": 1.2},
        hovertemplate=f"Votos acumulados: {_format_percent(progress)}<extra></extra>",
        showlegend=False,
    ))
    fig.update_layout(
        height=170, margin={"l": 4, "r": 4, "t": 4, "b": 4},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "radialaxis": {"visible": False, "range": [0, 1.28]},
            "angularaxis": {"visible": False, "rotation": 90, "direction": "clockwise"},
        },
        annotations=[{"text": _format_percent(share), "x": 0.5, "y": 0.5,
                      "showarrow": False, "font": {"size": 18, "color": "#ffffff"}}],
        hoverlabel={
            "bgcolor": "rgba(5,12,28,0.95)",
            "font_color": "#EAF2FF",
            "bordercolor": "rgba(147,197,253,0.55)",
        },
    )
    return fig


@st.dialog("Composição dos votos", width="large")
def _concentration_breakdown_dialog(concentration_df: pd.DataFrame, selected_rank: int) -> None:
    st.markdown(f"### Até o Top {selected_rank}")
    total_rows = len(concentration_df)
    pieces = []
    previous_share = 0.0
    previous_votes = 0.0
    for rank, label, color in CONCENTRATION_STEPS:
        effective = min(rank, total_rows)
        if effective <= 0:
            break
        row = concentration_df.iloc[effective - 1]
        share = float(row["pct_acumulado"])
        votes = float(row["votos_acumulados"])
        if share > previous_share:
            pieces.append(
                '<div class="raiox-concentration-breakdown-step">'
                f'<div class="raiox-concentration-breakdown-title"><span style="color:{color}">●</span> {html.escape(label)}</div>'
                f'<div class="raiox-concentration-breakdown-value">{_format_percent(share - previous_share)}</div>'
                f'<div class="raiox-concentration-breakdown-votes">{_format_number(votes - previous_votes)} votos</div>'
                '</div>'
            )
        previous_share, previous_votes = share, votes
        if rank >= selected_rank:
            break
    st.markdown(
        '<div class="raiox-concentration-breakdown">'
        + '<span class="raiox-concentration-breakdown-arrow">→</span>'.join(pieces)
        + '</div>', unsafe_allow_html=True,
    )
    selected = concentration_df.iloc[min(selected_rank, total_rows) - 1]
    st.caption(
        f"Acumulado: {_format_percent(float(selected['pct_acumulado']))} "
        f"({_format_number(float(selected['votos_acumulados']))} votos) em "
        f"{min(selected_rank, total_rows)} municípios."
    )


def _concentration_chart_selection(event: object | None) -> int | None:
    def customdata_item(customdata: object, position: int) -> object | None:
        if customdata is None:
            return None
        if isinstance(customdata, dict):
            for key in (position, str(position)):
                if key in customdata:
                    return customdata[key]
            return None
        try:
            return list(customdata)[position]
        except (TypeError, IndexError, KeyError):
            return None

    if event is None:
        return None
    if hasattr(event, "selection"):
        selection = getattr(event, "selection")
    elif isinstance(event, dict):
        selection = event.get("selection", {})
    else:
        selection = {}
    points = (
        selection.get("points", [])
        if isinstance(selection, dict)
        else getattr(selection, "points", [])
    )
    if not points:
        return None
    point = points[0]
    customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    rank_value = customdata_item(customdata, 2)
    try:
        rank = int(float(rank_value))
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


@st.dialog("Municípios da concentração", width="large")
def _concentration_municipalities_dialog(concentration_df: pd.DataFrame, selected_rank: int) -> None:
    if concentration_df.empty:
        st.info("Dados municipais indisponíveis.")
        return

    total_rows = len(concentration_df)
    effective_rank = min(max(1, int(selected_rank)), total_rows)
    selected = concentration_df.head(effective_rank).copy()
    reference = selected.iloc[-1]
    is_all = effective_rank >= total_rows
    title = "Todos os municípios" if is_all else f"Top {effective_rank} municípios"
    st.subheader(title)
    st.caption(
        f"{_format_number(float(reference['votos_acumulados']))} votos acumulados · "
        f"{_format_percent(float(reference['pct_acumulado']))} da votação total"
    )

    if is_all:
        display = selected[[
            "rank_municipio",
            "nm_municipio",
            "qt_votos",
            "pct_votos",
            "pct_acumulado",
        ]].rename(columns={
            "rank_municipio": "Posição",
            "nm_municipio": "Município",
            "qt_votos": "Votos",
            "pct_votos": "% individual",
            "pct_acumulado": "% acumulado",
        })
        display["% individual"] = pd.to_numeric(display["% individual"], errors="coerce").fillna(0) * 100
        display["% acumulado"] = pd.to_numeric(display["% acumulado"], errors="coerce").fillna(0) * 100
        st.dataframe(
            display,
            hide_index=True,
            height=650,
            width="stretch",
            column_config={
                "Posição": st.column_config.NumberColumn(format="%d"),
                "Votos": st.column_config.NumberColumn(format="%d"),
                "% individual": st.column_config.NumberColumn(format="%.2f%%"),
                "% acumulado": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        return

    st.plotly_chart(
        _territorial_concentration_chart(
            concentration_df,
            "votos_municipio",
            label_col="nm_municipio",
            title=title,
            limit=effective_rank,
        ),
        width="stretch",
        key=f"pagina1_concentration_dialog_chart_{effective_rank}",
    )


def _render_accumulated_concentration_section(df: pd.DataFrame | None) -> None:
    concentration_df = _municipal_concentration_frame(df)
    _major_section_header(
        "Concentração territorial dos votos",
        "Quanto da votação total está concentrada nos municípios onde o candidato mais recebeu votos.",
    )
    with st.container(border=True):
        if concentration_df.empty:
            st.warning("Nao encontrei dados municipais validos para calcular a concentracao territorial.")
            return

        def row_at(rank: int) -> pd.Series:
            idx = min(rank, len(concentration_df)) - 1
            return concentration_df.iloc[idx]

        top1 = row_at(1)
        top15 = row_at(15)
        donut_cols = st.columns(4, gap="small")
        for column, (rank, _, color) in zip(donut_cols, CONCENTRATION_STEPS):
            row = row_at(rank)
            share = float(row["pct_acumulado"])
            with column:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="raiox-concentration-pill-label">Top {rank}</div>'
                        f'<div class="raiox-concentration-pill-metric">'
                        f'<span class="raiox-concentration-pill-number">{_format_number(float(row["votos_acumulados"]))}</span>'
                        f'<span class="raiox-concentration-pill-unit">votos</span>'
                        '</div>', unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        _concentration_donut(share, color), width="stretch",
                        key=f"pagina1_concentration_donut_{rank}",
                        on_select=lambda selected_rank=rank: st.session_state.update(
                            pagina1_concentration_selected_rank=selected_rank
                        ),
                        selection_mode="points",
                        config={"displayModeBar": False},
                    )
        selected_rank = st.session_state.pop("pagina1_concentration_selected_rank", None)
        if selected_rank in (1, 5, 15, 20):
            _concentration_breakdown_dialog(concentration_df, selected_rank)
        st.caption(
            f"Curva acumulada até 100% da votação em {_format_number(len(concentration_df))} municípios."
        )
        curve_revision = st.session_state.get("pagina1_concentration_curve_revision", 0)
        st.plotly_chart(
            _accumulated_concentration_chart(concentration_df),
            width="stretch",
            key=f"pagina1_concentration_curve_{curve_revision}",
            config={"displayModeBar": False},
        )
        st.markdown(
            '<p class="raiox-concentration-reading">'
            f'<strong>{html.escape(str(top1["nm_municipio"]).title())}</strong> lidera com '
            f'<strong>{_format_percent(float(top1["pct_acumulado"]))}</strong>; '
            f'os 15 principais municípios concentram <strong>{_format_percent(float(top15["pct_acumulado"]))}</strong> dos votos.'
            '</p>',
            unsafe_allow_html=True,
        )
        for rank in (5, 15, 20):
            with st.expander(f"Ver municípios do Top {rank}"):
                city_items = "".join(
                    '<div class="raiox-concentration-city-item">'
                    f'<span class="raiox-concentration-city-rank">{int(city_row["rank_municipio"]):02d}</span>'
                    f'<span class="raiox-concentration-city-name">{html.escape(str(city_row["nm_municipio"]).title())}</span>'
                    f'<span class="raiox-concentration-city-votes">{_format_number(float(city_row["qt_votos"]))} votos</span>'
                    '</div>'
                    for _, city_row in concentration_df.head(rank).iterrows()
                )
                st.markdown(
                    f'<div class="raiox-concentration-city-list">{city_items}</div>',
                    unsafe_allow_html=True,
                )


def _municipal_votes_frame(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if "nivel_territorial" in df.columns:
        municipal = df[
            df["nivel_territorial"].astype(str).str.strip().str.lower() == "municipio"
        ].copy()
        if not municipal.empty:
            return municipal
    return df


def _total_votes_label(df: pd.DataFrame | None) -> str:
    municipal = _municipal_votes_frame(df)
    if municipal is None or "qt_votos" not in municipal.columns:
        return "--"
    total = pd.to_numeric(municipal["qt_votos"], errors="coerce").fillna(0).sum()
    return _format_number(total)


def _candidate_widget_suffix() -> str:
    filters = st.session_state.get("deputados_filters", {})
    parts = [filters.get("ano"), filters.get("cargo"), filters.get("nome")]
    normalized = "_".join(_normalized_text(part).replace(" ", "_") for part in parts if part)
    return normalized.casefold() or "padrao"


def _render_territory_leader(df: pd.DataFrame | None) -> None:
    name = "--"
    votes = "--"
    municipal = _municipal_votes_frame(df)
    if municipal is not None and {"nm_mesorregiao", "qt_votos"}.issubset(municipal.columns):
        by_meso = (
            municipal.assign(qt_votos=pd.to_numeric(municipal["qt_votos"], errors="coerce").fillna(0))
            .groupby("nm_mesorregiao", as_index=False)["qt_votos"]
            .sum()
            .sort_values("qt_votos", ascending=False)
        )
        if not by_meso.empty:
            name = str(by_meso.iloc[0]["nm_mesorregiao"]).title()
            votes = _format_number(by_meso.iloc[0]["qt_votos"])

    if ui is not None and not USE_CUSTOM_KPI_CARDS:
        ui.metric_card(
            label="Principal reduto eleitoral",
            value=name,
            description=f"{votes} votos recebidos",
            delta="Maior base eleitoral",
            variant="dashboard",
            key="kpi_territorio_lider",
        )
        return

    st.markdown(
        f"""
        <div class="mapa-kpi-wide-card">
            <div class="mapa-kpi-wide-tag">Maior base eleitoral</div>
            <div class="mapa-kpi-label">Principal reduto eleitoral</div>
            <div class="mapa-kpi-wide-value">{html.escape(name)}</div>
            <div class="mapa-kpi-wide-caption">{votes} votos recebidos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _demographic_label(column: str, prefix: str) -> str:
    label = column.removeprefix(prefix).replace("_", " ").strip()
    return label.title() if label else column




def _neighborhood_vote_cards(
    municipal_votes: pd.DataFrame | None,
    neighborhood_votes: pd.DataFrame | None,
    municipio: str,
    context: dict[str, str],
) -> str:
    if municipio == "Todos" or neighborhood_votes is None or neighborhood_votes.empty:
        return ""

    municipal_rows = pd.DataFrame()
    if municipal_votes is not None and not municipal_votes.empty and "nm_municipio" in municipal_votes.columns:
        municipal_rows = municipal_votes[
            municipal_votes["nm_municipio"].astype(str).str.strip().eq(municipio)
        ]
    vote_source = municipal_rows if not municipal_rows.empty else neighborhood_votes
    city_votes = pd.to_numeric(vote_source["qt_votos"], errors="coerce").fillna(0).sum()
    cards = [
        f'<div class="raiox-neighborhood-kpi">'
        f'<div class="raiox-neighborhood-kpi-label">Votos no município</div>'
        f'<div class="raiox-neighborhood-kpi-value">{_format_number(city_votes)}</div>'
        f'</div>'
    ]
    if context.get("cd_area_ponderada") or context.get("cd_setor_censitario") or context.get("nm_bairro"):
        selected_rows = _apply_territorial_context(neighborhood_votes, context, "Todas", municipio)
        neighborhood_total = pd.to_numeric(selected_rows["qt_votos"], errors="coerce").fillna(0).sum()
        selected_label = context.get("nome_bairro") or "território selecionado"
        cards.append(
            f'<div class="raiox-neighborhood-kpi">'
            f'<div class="raiox-neighborhood-kpi-label">Votos em {html.escape(selected_label)}</div>'
            f'<div class="raiox-neighborhood-kpi-value">{_format_number(neighborhood_total)}</div>'
            f'</div>'
        )
    return '<div class="raiox-neighborhood-kpis">' + "".join(cards) + "</div>"


def _apply_territorial_context(
    df: pd.DataFrame, context: dict[str, str], mesorregiao: str, municipio: str = "Todos"
) -> pd.DataFrame:
    result = df.copy()
    if mesorregiao != "Todas" and "nm_mesorregiao" in result.columns:
        result = result[result["nm_mesorregiao"].astype(str).str.strip() == mesorregiao]
    if municipio != "Todos" and "nm_municipio" in result.columns:
        result = result[result["nm_municipio"].astype(str).str.strip() == municipio]
    for column in ("cd_municipio", "cd_bairro", "nm_municipio", "nm_bairro", "cd_area_ponderada", "cd_setor_censitario"):
        value = context.get(column)
        if column in result.columns and value:
            if column.startswith("cd_"):
                result = result[result[column].map(_territorial_code).eq(_territorial_code(value))]
            else:
                result = result[result[column].astype(str).str.strip().eq(value)]
    return result


def _territorial_code(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _section_context(key: str) -> dict[str, str]:
    context = st.session_state.setdefault(key, {})
    if not isinstance(context, dict):
        context = {}
        st.session_state[key] = context
    return {
        str(key): str(value)
        for key, value in context.items()
        if value not in (None, "")
    }


def _set_section_context(key: str, context: dict[str, str]) -> bool:
    normalized = {
        str(key): str(value)
        for key, value in context.items()
        if value not in (None, "")
    }
    if normalized == _section_context(key):
        return False
    st.session_state[key] = normalized
    return True


def _clear_section_context(key: str) -> None:
    st.session_state[key] = {}


def _context_label(context: dict[str, str]) -> str:
    return (
        (context.get("nome_bairro") or "território selecionado")
        if context.get("cd_area_ponderada") or context.get("cd_setor_censitario") or context.get("nm_bairro")
        else context.get("nm_municipio") or "recorte selecionado"
    )


def _demographic_bar(kind: str, context: dict[str, str], mesorregiao: str, municipio: str = "Todos") -> go.Figure:
    df = _read_selected_parquet(kind)
    prefix_by_kind = {
        "genero": "pct_genero_",
        "idade": "pct_idade_",
        "escolaridade": "pct_escolaridade_",
        "estado_civil": "pct_estado_civil_",
    }
    prefix = prefix_by_kind[kind]

    if df is None or df.empty:
        bar_df = pd.DataFrame({"categoria": ["Parquet pendente"], "percentual": [0.0]})
    else:
        df = _apply_territorial_context(df, context, mesorregiao, municipio)
        if (context.get("cd_area_ponderada") or context.get("cd_setor_censitario")) and "cd_bairro" in df.columns:
            area_votes = _read_selected_parquet("votos_bairro")
            if area_votes is not None and "cd_bairro" in area_votes.columns:
                area_rows = _apply_territorial_context(area_votes, context, mesorregiao, municipio)
                area_codes = {code for code in area_rows["cd_bairro"].map(_territorial_code) if code}
                df = df[df["cd_bairro"].map(_territorial_code).isin(area_codes)]
            else:
                df = df.iloc[0:0]
        value_cols = [col for col in df.columns if col.startswith(prefix)]
        if value_cols:
            weight_col = "QT_VOTOS_TOTAL" if "QT_VOTOS_TOTAL" in df.columns else "qt_votos"
            weights = pd.to_numeric(df.get(weight_col, 0), errors="coerce").fillna(0)
            total_weight = float(weights.sum())
            if total_weight > 0:
                percentages = [
                    (pd.to_numeric(df[col], errors="coerce").fillna(0) * weights).sum() / total_weight
                    for col in value_cols
                ]
            else:
                percentages = [
                    pd.to_numeric(df[col], errors="coerce").fillna(0).mean()
                    for col in value_cols
                ]
            bar_df = pd.DataFrame(
                {
                    "categoria": [_demographic_label(col, prefix) for col in value_cols],
                    "percentual": percentages,
                }
            ).sort_values("percentual", ascending=False)
        else:
            bar_df = pd.DataFrame({"categoria": ["Colunas nao encontradas"], "percentual": [0.0]})

    bar_df["percentual"] = pd.to_numeric(bar_df["percentual"], errors="coerce").fillna(0)
    bar_df["rotulo"] = bar_df["percentual"].map(lambda value: f"{value:.1f}%".replace(".", ","))

    fig = px.bar(
        bar_df,
        x="percentual",
        y="categoria",
        text="rotulo",
        color="percentual",
        color_continuous_scale="Blues",
        orientation="h",
    )
    max_percent = float(bar_df["percentual"].max() or 0)
    x_range = [0, min(110, max_percent * 1.18)] if max_percent > 0 else [0, 100]
    fig.update_layout(
        height=430,
        margin={"l": 180, "r": 88, "t": 8, "b": 42},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        xaxis={
            "title": "% do perfil",
            "gridcolor": "rgba(255,255,255,0.12)",
            "range": x_range,
            "ticksuffix": "%",
        },
        yaxis={"title": "", "categoryorder": "total ascending"},
        coloraxis_showscale=False,
    )
    fig.update_traces(
        texttemplate="%{text}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Participacao: %{x:.1f}%<extra></extra>",
    )
    return fig


def _campaign_total_votes(votos_df: pd.DataFrame | None) -> float:
    if votos_df is None or votos_df.empty or "qt_votos" not in votos_df.columns:
        return 0.0
    votes = pd.to_numeric(votos_df["qt_votos"], errors="coerce").fillna(0)
    if "nm_municipio" in votos_df.columns:
        frame = votos_df[["nm_municipio"]].copy()
        frame["qt_votos"] = votes
        return float(frame.groupby("nm_municipio")["qt_votos"].sum().sum())
    return float(votes.sum())


EXPENSE_TYPE_ALIASES = {
    "Atividades de militância e mobilização de rua": "Militância",
    "Cessão ou locação de veículos": "Locação de Veículos",
    "Combustíveis e lubrificantes": "Combustíveis",
    "Correspondências e despesas postais": "Correios",
    "Criação e inclusão de páginas na internet": "Criação de Sites",
    "Despesa com Impulsionamento de Conteúdos": "Anúncios Online",
    "Encargos financeiros, taxas bancárias e/ou op. cartão de crédito": "Taxas Bancárias",
    "Locação/cessão de bens imóveis": "Locação de Imóveis",
    "Locação/cessão de bens móveis (exceto veículos)": "Locação de Bens Móveis",
    "Materiais de expediente": "Material de Expediente",
    "Produção de jingles, vinhetas e slogans": "Produção de Jingles e Áudio",
    "Publicidade por adesivos": "Publicidade: Adesivos",
    "Publicidade por jornais e revistas": "Publicidade: Impressa (Mídia)",
    "Publicidade por materiais impressos": "Materiais Impressos",
    "Serviços advocatícios": "Serviços Jurídicos",
    "Serviços contábeis": "Serviços Contábeis",
    "Serviços próprios prestados por terceiros": "Serviços de Terceiros (Próprios)",
    "Serviços prestados por terceiros": "Serviços de Terceiros",
    "Taxa de Administração de Financiamento Coletivo": "Taxa de Vaquinha",
    "Comícios": "Comícios",
    "Diversas a especificar": "Outras Despesas",
    "Despesas com pessoal": "Equipe e Pessoal",
}

EXPENSE_TREEMAP_SHORT_LABELS = {
    "Publicidade por jornais e revistas": "Publicidade Impressa",
    "Produção de jingles, vinhetas e slogans": "Jingles e Áudio",
    "Serviços próprios prestados por terceiros": "Terceiros Próprios",
}

EXPENSE_TREEMAP_COLORS = {
    "Atividades de militância e mobilização de rua": "#15803D",
    "Cessão ou locação de veículos": "#6D28D9",
    "Combustíveis e lubrificantes": "#C2410C",
    "Correspondências e despesas postais": "#0369A1",
    "Criação e inclusão de páginas na internet": "#A16207",
    "Despesa com Impulsionamento de Conteúdos": "#A21CAF",
    "Encargos financeiros, taxas bancárias e/ou op. cartão de crédito": "#475569",
    "Locação/cessão de bens imóveis": "#0F766E",
    "Locação/cessão de bens móveis (exceto veículos)": "#B45309",
    "Materiais de expediente": "#4338CA",
    "Produção de jingles, vinhetas e slogans": "#BE123C",
    "Publicidade por adesivos": "#047857",
    "Publicidade por jornais e revistas": "#9D174D",
    "Publicidade por materiais impressos": "#1D4ED8",
    "Serviços advocatícios": "#9A3412",
    "Serviços contábeis": "#5B21B6",
    "Serviços próprios prestados por terceiros": "#4D7C0F",
    "Serviços prestados por terceiros": "#0E7490",
    "Taxa de Administração de Financiamento Coletivo": "#1E40AF",
    "OUTRAS DESPESAS": "#334155",
}


def _short_expense_type_label(expense_type: str) -> str:
    label = EXPENSE_TYPE_ALIASES.get(expense_type)
    if label:
        return label
    if len(expense_type) <= 28:
        return expense_type
    return f"{expense_type[:25].rstrip()}..."


def _expense_treemap_label(expense_type: str) -> str:
    label = EXPENSE_TREEMAP_SHORT_LABELS.get(expense_type) or EXPENSE_TYPE_ALIASES.get(expense_type)
    if label:
        return label.upper()
    normalized = " ".join(str(expense_type or "Não informado").strip().split())
    if len(normalized) <= 30:
        return normalized.upper()
    return f"{normalized[:27].rstrip()}...".upper()


def _expense_treemap_display_frame(chart_df: pd.DataFrame) -> pd.DataFrame:
    if chart_df.empty:
        return chart_df

    display_df = chart_df.sort_values("valor_total_despesa", ascending=False).copy()
    display_df["_rank"] = np.arange(1, len(display_df) + 1)
    small_share = pd.to_numeric(display_df["pct_gasto"], errors="coerce").fillna(0).lt(0.015)
    tail_mask = small_share & display_df["_rank"].gt(4)
    if not tail_mask.any():
        return display_df.drop(columns=["_rank"])

    visible = display_df.loc[~tail_mask].copy()
    tail = display_df.loc[tail_mask].copy()
    total_spend = float(pd.to_numeric(chart_df["valor_total_despesa"], errors="coerce").fillna(0).sum())
    total_votes = float(pd.to_numeric(chart_df["qt_votos"], errors="coerce").fillna(0).max())
    tail_spend = float(pd.to_numeric(tail["valor_total_despesa"], errors="coerce").fillna(0).sum())
    tail_row = {
        "tipo_despesa": "OUTRAS DESPESAS",
        "valor_total_despesa": tail_spend,
        "qt_votos": total_votes,
        "custo_por_voto": tail_spend / total_votes if total_votes > 0 else 0.0,
        "pct_gasto": tail_spend / total_spend if total_spend > 0 else 0.0,
        "pct_gasto_acumulado": np.nan,
        "rotulo_custo": _format_currency(tail_spend / total_votes if total_votes > 0 else 0.0),
        "tipo_despesa_curto": "Outras Despesas",
        "tipo_despesa_treemap": "OUTRAS DESPESAS",
        "rotulo_acumulado": "",
        "rotulo_pct_gasto": _format_percent(tail_spend / total_spend if total_spend > 0 else 0.0),
        "is_grouped_tail": True,
        "tail_count": f"{int(len(tail))} tipos agrupados:",
        "tail_members": ", ".join(
            tail["tipo_despesa"].astype(str).head(6).map(_short_expense_type_label).tolist()
        ),
        "tail_hover": (
            f"<br>{int(len(tail))} tipos agrupados: "
            f"{', '.join(tail['tipo_despesa'].astype(str).head(6).map(_short_expense_type_label).tolist())}"
        ),
    }
    visible["is_grouped_tail"] = False
    visible["tail_count"] = ""
    visible["tail_members"] = ""
    visible["tail_hover"] = ""
    result = pd.concat([visible, pd.DataFrame([tail_row])], ignore_index=True)
    return result.sort_values("valor_total_despesa", ascending=False)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _interpolate_hex_color(start: str, end: str, amount: float) -> str:
    amount = max(0.0, min(1.0, float(amount)))
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    return _rgb_to_hex(tuple(
        round(start_channel + (end_channel - start_channel) * amount)
        for start_channel, end_channel in zip(start_rgb, end_rgb)
    ))


def _text_color_for_background(color: str) -> str:
    red, green, blue = _hex_to_rgb(color)
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255
    return "#0b1f4d" if luminance > 0.52 else "#f8fbff"


def _expense_cost_by_type_frame(
    despesas_df: pd.DataFrame | None,
    total_votes: float,
) -> pd.DataFrame:
    if (
        despesas_df is None
        or despesas_df.empty
        or "tipo_despesa" not in despesas_df.columns
        or "valor_despesa" not in despesas_df.columns
        or total_votes <= 0
    ):
        return pd.DataFrame()

    result = despesas_df[["tipo_despesa", "valor_despesa"]].copy()
    result["tipo_despesa"] = result["tipo_despesa"].fillna("Nao informado").astype(str).str.strip()
    result.loc[result["tipo_despesa"].eq(""), "tipo_despesa"] = "Nao informado"
    result["valor_total_despesa"] = pd.to_numeric(result["valor_despesa"], errors="coerce").fillna(0)
    result = (
        result.groupby("tipo_despesa", as_index=False)["valor_total_despesa"]
        .sum()
        .sort_values("valor_total_despesa", ascending=False)
    )
    result = result[result["valor_total_despesa"].gt(0)].copy()
    if result.empty:
        return result

    total_spend = float(result["valor_total_despesa"].sum())
    result["qt_votos"] = float(total_votes)
    result["custo_por_voto"] = result["valor_total_despesa"] / float(total_votes)
    result["pct_gasto"] = result["valor_total_despesa"] / total_spend if total_spend > 0 else 0.0
    result["pct_gasto_acumulado"] = result["pct_gasto"].cumsum()
    result["rotulo_custo"] = result["custo_por_voto"].map(_format_currency)
    result["tipo_despesa_curto"] = result["tipo_despesa"].map(_short_expense_type_label)
    result["tipo_despesa_treemap"] = result["tipo_despesa"].map(_expense_treemap_label)
    result["rotulo_acumulado"] = result["pct_gasto_acumulado"].map(lambda value: f"{value:.0%}")
    result["rotulo_pct_gasto"] = result["pct_gasto"].map(lambda value: f"{value:.0%}")
    return result


def _cost_efficiency_kpis(
    chart_df: pd.DataFrame,
    selected_expense: str | None = None,
) -> dict[str, str]:
    if chart_df.empty:
        return {
            "custo_label": "Custo por Voto Total",
            "custo_por_voto": _format_currency(0),
            "gasto_label": "Total Gasto",
            "total_gasto": _format_currency(0),
            "despesa_label": "Despesa Líder",
            "despesa_lider": "Sem dados",
            "despesa_lider_caption": "Sem tipo de despesa",
            "custo_caption": "Custo total dividido pelos votos da campanha.",
            "gasto_caption": "Soma das despesas da campanha.",
        }
    filtered_df = chart_df
    if selected_expense:
        filtered_df = chart_df.loc[chart_df["tipo_despesa"].eq(selected_expense)]
    filtered_spend = float(
        pd.to_numeric(filtered_df["valor_total_despesa"], errors="coerce").fillna(0).sum()
    )
    campaign_spend = float(
        pd.to_numeric(chart_df["valor_total_despesa"], errors="coerce").fillna(0).sum()
    )
    total_votes = float(pd.to_numeric(chart_df["qt_votos"], errors="coerce").fillna(0).max())
    cost_per_vote = filtered_spend / total_votes if total_votes > 0 else 0.0
    leader = filtered_df.sort_values("valor_total_despesa", ascending=False).head(1).iloc[0]
    is_filtered = bool(selected_expense)
    leader_spend = float(leader["valor_total_despesa"])
    leader_pct = leader_spend / campaign_spend if campaign_spend > 0 else 0.0
    return {
        "custo_label": "Custo por Voto da Despesa" if is_filtered else "Custo por Voto Total",
        "custo_por_voto": _format_currency(cost_per_vote),
        "gasto_label": "Gasto no Tipo Selecionado" if is_filtered else "Total Gasto",
        "total_gasto": _format_currency(filtered_spend),
        "despesa_label": "Despesa Selecionada" if is_filtered else "Despesa Líder",
        "despesa_lider": _short_expense_type_label(str(leader["tipo_despesa"])),
        "despesa_lider_caption": (
            f"{_format_currency(leader_spend)} | {_format_percent(leader_pct)} do gasto total"
        ),
        "custo_caption": (
            "Custo da despesa selecionada dividido pelos votos da campanha."
            if is_filtered else "Custo total dividido pelos votos da campanha."
        ),
        "gasto_caption": (
            "Valor da despesa selecionada na campanha."
            if is_filtered else "Soma das despesas da campanha."
        ),
    }


def _render_cost_efficiency_kpis(
    chart_df: pd.DataFrame,
    selected_expense: str | None = None,
) -> None:
    kpis = _cost_efficiency_kpis(chart_df, selected_expense)
    metric_columns = st.columns(3, gap="small")
    metric_data = (
        (kpis["custo_label"], kpis["custo_por_voto"], kpis["custo_caption"]),
        (kpis["gasto_label"], kpis["total_gasto"], kpis["gasto_caption"]),
        (kpis["despesa_label"], kpis["despesa_lider"], kpis["despesa_lider_caption"]),
    )
    for column, (label, value, caption) in zip(metric_columns, metric_data):
        with column:
            with st.container(border=True):
                st.metric(label, value)
                st.caption(caption)


def _expense_cost_by_type_chart(chart_df: pd.DataFrame, selected_expense: str | None = None) -> go.Figure:
    if chart_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Dados de despesas de campanha indisponíveis.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": "#eaf2ff", "size": 16},
        )
        fig.update_layout(height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    display_df = _expense_treemap_display_frame(chart_df)
    display_df["treemap_color"] = display_df["tipo_despesa"].map(EXPENSE_TREEMAP_COLORS).fillna("#475569")
    if selected_expense:
        selected_mask = display_df["tipo_despesa"].eq(selected_expense)
        display_df.loc[selected_mask, "treemap_color"] = display_df.loc[
            selected_mask, "treemap_color"
        ].map(lambda color: _interpolate_hex_color(color, "#ffffff", 0.22))
    display_df["treemap_text_color"] = display_df["treemap_color"].map(_text_color_for_background)
    display_df["rotulo_pct_orcamento"] = display_df["pct_gasto"].map(_format_percent)
    display_df["rotulo_valor_despesa"] = display_df["valor_total_despesa"].map(_format_currency_whole)
    border_colors = [
        "#f8fbff" if selected_expense and expense_type == selected_expense else "rgba(191,219,254,0.55)"
        for expense_type in display_df["tipo_despesa"]
    ]
    custom_data = np.stack(
        [
            display_df["tipo_despesa"],
            display_df["rotulo_pct_orcamento"],
            display_df["rotulo_valor_despesa"],
            display_df["pct_gasto"],
            display_df["custo_por_voto"],
            display_df.get("is_grouped_tail", pd.Series(False, index=display_df.index)),
            display_df.get("tail_hover", pd.Series("", index=display_df.index)),
            display_df["tipo_despesa_curto"],
        ],
        axis=-1,
    )
    fig = go.Figure(go.Treemap(
        labels=display_df["tipo_despesa_treemap"],
        parents=[""] * len(display_df),
        values=display_df["valor_total_despesa"],
        customdata=custom_data,
        texttemplate=(
            "<b>%{label}</b><br>"
            "%{customdata[1]} do orçamento • %{customdata[2]}"
        ),
        textfont={
            "color": display_df["treemap_text_color"].tolist(),
            "size": 16,
            "family": "Segoe UI, Inter, sans-serif",
        },
        marker={
            "colors": display_df["treemap_color"].tolist(),
            "line": {"color": border_colors, "width": 1.3},
        },
        hovertemplate=(
            "<b>%{customdata[7]}</b><br>"
            "Total gasto: %{customdata[2]}<br>"
            "Participação no orçamento: %{customdata[3]:.1%}<br>"
            "Custo por voto: R$ %{customdata[4]:,.2f}"
            "%{customdata[6]}<extra></extra>"
        ),
        branchvalues="total",
        tiling={"pad": 2},
    ))
    fig.update_traces(
        textposition="middle center",
        pathbar={"visible": False},
    )
    fig.update_layout(
        height=440,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff", "family": "Segoe UI, Inter, sans-serif"},
        hoverlabel={
            "bgcolor": "rgba(5,12,28,0.95)",
            "font_color": "#EAF2FF",
            "bordercolor": "rgba(147,197,253,0.55)",
        },
        uniformtext={"minsize": 12, "mode": "hide"},
    )
    return fig


def _selected_expense_from_treemap(event: object | None, chart_df: pd.DataFrame) -> str | None:
    if not event:
        return None
    valid_expenses = set(chart_df["tipo_despesa"].astype(str))
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection", {})
    points = getattr(selection, "points", None)
    if points is None and isinstance(selection, dict):
        points = selection.get("points", [])
    for point in points or []:
        customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
        if customdata is not None and len(customdata) > 5 and str(customdata[5]).lower() == "true":
            continue
        expense_type = str(customdata[0]) if customdata is not None and len(customdata) else ""
        if expense_type in valid_expenses:
            return expense_type
        label = point.get("label") if isinstance(point, dict) else getattr(point, "label", "")
        label = str(label or "").strip()
        if label:
            matching = chart_df.loc[chart_df["tipo_despesa_treemap"].astype(str).eq(label), "tipo_despesa"]
            if not matching.empty:
                return str(matching.iloc[0])
    return None


def _territorial_expense_cost_frame(
    gastos_df: pd.DataFrame | None,
    expense_share: float,
    territory: str,
) -> pd.DataFrame:
    required = {"qt_votos", "valor_despesas_rateado", "nm_municipio", "nm_mesorregiao"}
    if gastos_df is None or gastos_df.empty or not required.issubset(gastos_df.columns):
        return pd.DataFrame()
    frame = gastos_df.copy()
    if "nivel_territorial" in frame.columns:
        levels = frame["nivel_territorial"].astype(str).str.strip().str.lower()
        if levels.eq("municipio").any():
            frame = frame[levels.eq("municipio")].copy()
        elif levels.eq("bairro").any():
            frame = frame[levels.eq("bairro")].copy()
        else:
            return pd.DataFrame()
    frame["qt_votos"] = pd.to_numeric(frame["qt_votos"], errors="coerce").fillna(0)
    frame["valor_despesas_rateado"] = pd.to_numeric(
        frame["valor_despesas_rateado"], errors="coerce"
    ).fillna(0)
    group_col = "nm_municipio" if territory == "Municípios" else "nm_mesorregiao"
    frame[group_col] = frame[group_col].fillna("Não informado").astype(str).str.strip()
    result = frame.groupby(group_col, as_index=False)[["qt_votos", "valor_despesas_rateado"]].sum()
    result = result[result["qt_votos"].gt(0)].copy()
    result["gasto_atribuido"] = result["valor_despesas_rateado"] * expense_share
    result["custo_por_voto"] = result["gasto_atribuido"] / result["qt_votos"]
    return result.sort_values("qt_votos", ascending=False)


def _territorial_expense_cost_by_type_frame(
    gastos_por_tipo_df: pd.DataFrame | None,
    selected_expense: str | None,
    territory: str,
) -> pd.DataFrame:
    required = {
        "cd_municipio", "nm_municipio", "nm_mesorregiao", "tipo_despesa",
        "valor_total_tipo_despesa", "qt_votos_municipio",
    }
    if gastos_por_tipo_df is None or gastos_por_tipo_df.empty or not required.issubset(gastos_por_tipo_df.columns):
        return pd.DataFrame()

    frame = gastos_por_tipo_df.copy()
    frame["qt_votos_municipio"] = pd.to_numeric(frame["qt_votos_municipio"], errors="coerce")
    frame["valor_total_tipo_despesa"] = pd.to_numeric(
        frame["valor_total_tipo_despesa"], errors="coerce"
    )
    frame = frame.dropna(subset=["qt_votos_municipio", "valor_total_tipo_despesa"])
    if frame.empty:
        return pd.DataFrame()

    # Each type's campaign total and each city's votes repeat across the city/type rows.
    type_totals = frame.groupby("tipo_despesa")["valor_total_tipo_despesa"].first()
    if selected_expense:
        if selected_expense not in type_totals.index:
            return pd.DataFrame()
        campaign_spend = float(type_totals.loc[selected_expense])
    else:
        campaign_spend = float(type_totals.sum())

    municipalities = frame.drop_duplicates("cd_municipio").copy()
    group_col = "nm_municipio" if territory == "Municípios" else "nm_mesorregiao"
    municipalities[group_col] = municipalities[group_col].fillna("Não informado").astype(str).str.strip()
    result = municipalities.groupby(group_col, as_index=False)["qt_votos_municipio"].sum()
    result = result[result["qt_votos_municipio"].gt(0)].copy()
    result = result.rename(columns={"qt_votos_municipio": "qt_votos"})
    result["gasto_atribuido"] = campaign_spend
    result["custo_por_voto"] = campaign_spend / result["qt_votos"]
    return result.sort_values("qt_votos", ascending=False)


def _territorial_expense_cost_chart(
    frame: pd.DataFrame, territory: str, campaign_total: bool = False
) -> go.Figure:
    def unavailable_chart() -> go.Figure:
        empty_fig = go.Figure()
        empty_fig.add_annotation(
            text="Sem dados territoriais de gastos para este recorte.",
            x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
            font={"color": "#eaf2ff", "size": 16},
        )
        empty_fig.update_layout(
            height=560,
            margin={"l": 10, "r": 10, "t": 30, "b": 10},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#eaf2ff"},
            xaxis={"visible": False},
            yaxis={"visible": False},
            showlegend=False,
        )
        return empty_fig

    if frame.empty:
        return unavailable_chart()

    label_col = "nm_municipio" if territory == "Municípios" else "nm_mesorregiao"
    display = frame.copy()
    for column in ("qt_votos", "custo_por_voto", "gasto_atribuido"):
        display[column] = pd.to_numeric(display[column], errors="coerce")
    display = display.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["qt_votos", "custo_por_voto", "gasto_atribuido"]
    )
    display = display.loc[display["qt_votos"].gt(0) & display["custo_por_voto"].ge(0)].copy()
    if display.empty:
        return unavailable_chart()

    display = display.nlargest(15, "custo_por_voto").sort_values("custo_por_voto", ascending=True)
    max_votes = float(display["qt_votos"].max())
    max_cost = float(display["custo_por_voto"].max())
    display["rotulo_custo"] = display["custo_por_voto"].map(_format_currency)
    display["territory_label"] = display[label_col].astype(str)
    customdata = display[[
        "territory_label", "gasto_atribuido", "qt_votos", "custo_por_voto", "rotulo_custo",
    ]].to_numpy()

    # Keep the cost bars in a fixed portion of the shared axis so votes retain their own range.
    left_extent = max_votes * 0.36 if max_cost > 0 else 0.0
    if max_cost > 0:
        cost_scale = left_extent / max_cost
        display["custo_espelhado"] = -(display["custo_por_voto"] * cost_scale)
    else:
        display["custo_espelhado"] = 0.0

    fig = go.Figure()
    if max_cost > 0:
        fig.add_trace(go.Bar(
            x=display["custo_espelhado"],
            y=display["territory_label"],
            orientation="h",
            name="R$/voto",
            marker={
                "color": "rgba(251,191,36,0.72)",
                "line": {"color": "rgba(254,243,199,0.78)", "width": 1},
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Custo por voto: %{customdata[4]}<br>"
                f"{'Total da campanha' if campaign_total else 'Gasto atribuído'}: R$ %{{customdata[1]:,.2f}}<br>"
                "Votos: %{customdata[2]:,.0f}<extra></extra>"
            ),
        ))
    fig.add_trace(go.Bar(
        x=display["qt_votos"],
        y=display["territory_label"],
        orientation="h",
        name="Votos",
        marker={
            "color": "#60a5fa",
            "line": {"color": "rgba(248,251,255,0.45)", "width": 1},
        },
        text=display["rotulo_custo"].map(lambda value: f"{value}/voto"),
        textposition="outside",
        textfont={"color": "#eaf2ff", "size": 12},
        cliponaxis=False,
        customdata=customdata,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Votos: %{customdata[2]:,.0f}<br>"
            "Custo por voto: %{customdata[4]}<br>"
            f"{'Total da campanha' if campaign_total else 'Gasto atribuído'}: R$ %{{customdata[1]:,.2f}}<extra></extra>"
        ),
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(226,232,240,0.52)")

    right_extent = max_votes
    tickvals = [0.0]
    ticktext = ["0"]
    if max_cost > 0:
        tickvals = [-left_extent, -(left_extent / 2), 0.0]
        ticktext = [_format_currency(max_cost), _format_currency(max_cost / 2), "0"]
    tickvals.extend([right_extent / 2, right_extent])
    ticktext.extend([_format_number(right_extent / 2), _format_number(right_extent)])
    x_range = [-(left_extent * 1.15), right_extent * 1.48] if max_cost > 0 else [0.0, right_extent * 1.48]
    x_title = "R$/voto (esquerda) · Votos (direita)" if max_cost > 0 else "Votos"

    fig.update_layout(
        height=560,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        xaxis={
            "title": x_title,
            "gridcolor": "rgba(255,255,255,0.10)",
            "zeroline": False,
            "tickmode": "array",
            "tickvals": tickvals,
            "ticktext": ticktext,
            "range": x_range,
            "automargin": True,
        },
        yaxis={"title": "", "automargin": True},
        barmode="overlay",
        bargap=0.34,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"color": "#dbeafe"},
        },
        hoverlabel={
            "bgcolor": "rgba(5,12,28,0.95)",
            "font_color": "#EAF2FF",
            "bordercolor": "rgba(147,197,253,0.55)",
        },
    )
    return fig


def _render_cost_efficiency_section(
    votos_df: pd.DataFrame | None,
    despesas_df: pd.DataFrame | None,
    gastos_df: pd.DataFrame | None,
    gastos_por_tipo_df: pd.DataFrame | None,
) -> None:
    _major_section_header(
        "Eficiência por Custo do Voto",
        "Participação de cada tipo de despesa nos gastos totais da campanha.",
    )
    chart_df = _expense_cost_by_type_frame(despesas_df, _campaign_total_votes(votos_df))
    selected_expense = st.session_state.get(EXPENSE_SELECTION_KEY)
    if chart_df.empty or selected_expense not in chart_df["tipo_despesa"].values:
        selected_expense = None
        st.session_state.pop(EXPENSE_SELECTION_KEY, None)
    selected_expense_label = _short_expense_type_label(selected_expense) if selected_expense else None
    _render_cost_efficiency_kpis(chart_df, selected_expense)
    treemap_col, territorial_col = st.columns(2, gap="large")
    with treemap_col:
        with st.container(border=True):
            treemap_title = (
                f"Gastos por tipo de despesa · filtrando {selected_expense_label}"
                if selected_expense_label else "Gastos por tipo de despesa"
            )
            st.markdown(
                f"<div class='raiox-chart-card-title'>{html.escape(treemap_title)}</div>",
                unsafe_allow_html=True,
            )
            treemap_event = st.plotly_chart(
                _expense_cost_by_type_chart(chart_df, selected_expense),
                width="stretch",
                key=f"{EXPENSE_TREEMAP_KEY}_{st.session_state.get(EXPENSE_TREEMAP_REVISION_KEY, 0)}",
                on_select="rerun",
                selection_mode="points",
            )
            clicked_expense = _selected_expense_from_treemap(treemap_event, chart_df)
            if clicked_expense and clicked_expense != selected_expense:
                st.session_state[EXPENSE_SELECTION_KEY] = clicked_expense
                st.rerun()
    with territorial_col:
        with st.container(border=True):
            title = selected_expense_label or "Gasto total"
            filter_tag = (
                f"<span class='raiox-cost-filter-tag'>{html.escape(selected_expense_label)}</span>"
                if selected_expense_label else ""
            )
            st.markdown(
                "<div class='raiox-cost-chart-heading'>"
                f"<div class='raiox-chart-card-title'>Votos e custo por voto territorial · {html.escape(title)}</div>"
                f"{filter_tag}"
                "</div>",
                unsafe_allow_html=True,
            )
            if selected_expense and st.button("Mostrar gasto total", key="pagina1_reset_tipo_despesa"):
                st.session_state.pop(EXPENSE_SELECTION_KEY, None)
                st.session_state[EXPENSE_TREEMAP_REVISION_KEY] = (
                    st.session_state.get(EXPENSE_TREEMAP_REVISION_KEY, 0) + 1
                )
                st.rerun()
            share = 1.0
            if selected_expense:
                share = float(chart_df.loc[
                    chart_df["tipo_despesa"].eq(selected_expense), "pct_gasto"
                ].iloc[0])
            has_type_data = gastos_por_tipo_df is not None and not gastos_por_tipo_df.empty
            if has_type_data:
                municipality_cost = _territorial_expense_cost_by_type_frame(
                    gastos_por_tipo_df, selected_expense, "Municípios"
                )
            else:
                municipality_cost = _territorial_expense_cost_frame(gastos_df, share, "Municípios")
            municipality_names = (
                sorted(municipality_cost["nm_municipio"].dropna().astype(str).unique().tolist())
                if "nm_municipio" in municipality_cost.columns else []
            )
            top15_option = "Top 15 municípios por custo por voto"
            territory_filter = st.selectbox(
                "Filtrar por município",
                [top15_option, *municipality_names],
                key=f"pagina1_custo_municipio_filtro_{_candidate_widget_suffix()}",
            )
            territory = "Municípios"
            territorial_cost = municipality_cost.copy()
            if territory_filter != top15_option:
                territorial_cost = territorial_cost.loc[
                    territorial_cost["nm_municipio"].astype(str).eq(territory_filter)
                ].copy()
            if not territorial_cost.empty and {
                "qt_votos", "custo_por_voto", "gasto_atribuido",
            }.issubset(territorial_cost.columns):
                territorial_cost = territorial_cost.replace([np.inf, -np.inf], np.nan).dropna(
                    subset=["qt_votos", "custo_por_voto", "gasto_atribuido"]
                )
                territorial_cost = territorial_cost.loc[
                    pd.to_numeric(territorial_cost["qt_votos"], errors="coerce").gt(0)
                    & pd.to_numeric(territorial_cost["custo_por_voto"], errors="coerce").ge(0)
                ]
            if territorial_cost.empty:
                st.info(
                    "Sem dados territoriais de gastos válidos para este recorte. "
                    "Não é possível calcular o custo por voto."
                )
            else:
                st.plotly_chart(
                    _territorial_expense_cost_chart(territorial_cost, territory, has_type_data),
                    width="stretch",
                )
                if has_type_data:
                    st.caption(
                        "Custo de referência: valor total da campanha para o tipo selecionado "
                        "(ou todos os tipos) dividido pelos votos do território. "
                        "O parquet repete o total da campanha em cada município; "
                        "não registra gasto realizado em cada local."
                    )
                else:
                    st.caption(
                        "Gasto atribuído proporcionalmente aos votos em cada território. "
                        "O parquet não identifica o tipo de despesa por local; por isso "
                        "o custo por voto é igual entre territórios neste rateio."
                    )


def _parliamentary_action_frame(
    votos_df: pd.DataFrame | None,
    emendas_df: pd.DataFrame | None,
) -> pd.DataFrame:
    if votos_df is None or votos_df.empty or emendas_df is None or emendas_df.empty:
        return pd.DataFrame()
    if "qt_votos" not in votos_df.columns:
        return pd.DataFrame()

    geojson_mg, df_tse_ref, df_municipios_ref, df_regioes_ref = _load_geo_reference()
    if geojson_mg is None or df_tse_ref is None or df_municipios_ref is None:
        return pd.DataFrame()

    code_col = next(
        (
            col
            for col in (
                "cd_ibge_municipio",
                "codigo_ibge",
                "CD_MUNICIPIO",
                "cd_municipio",
                "codigo_tse",
                "codigo_municipio_tse",
            )
            if col in votos_df.columns
        ),
        None,
    )
    city_col = "nm_municipio" if "nm_municipio" in votos_df.columns else None
    rank_col = next(
        (
            col
            for col in (
                "rank_municipio",
                "ranking_municipio",
                "posicao_municipio",
                "posicao_candidato_municipio",
                "rank_candidato_municipio",
                "ranking_candidato_municipio",
            )
            if col in votos_df.columns
        ),
        None,
    )
    extra_vote_cols = [rank_col] if rank_col else []

    if code_col == "cd_ibge_municipio" or code_col == "codigo_ibge":
        votos_base = votos_df[[code_col, "qt_votos"] + ([city_col] if city_col else []) + extra_vote_cols].copy()
        votos_base = votos_base.rename(columns={code_col: "codigo_ibge", city_col or code_col: "municipio"})
        votos_base["codigo_ibge"] = votos_base["codigo_ibge"].astype("string")
    elif code_col:
        votos_base = votos_df[[code_col, "qt_votos"] + ([city_col] if city_col else []) + extra_vote_cols].copy()
        votos_base = votos_base.rename(columns={code_col: "codigo_tse", city_col or code_col: "municipio"})
        votos_base["codigo_tse"] = votos_base["codigo_tse"].astype("string")
        votos_base = votos_base.merge(
            df_tse_ref[["codigo_tse", "codigo_ibge", "nome_municipio"]],
            on="codigo_tse",
            how="left",
        )
        votos_base["municipio"] = votos_base["municipio"].fillna(votos_base["nome_municipio"])
    elif city_col:
        votos_base = votos_df[[city_col, "qt_votos"] + extra_vote_cols].copy().rename(columns={city_col: "municipio"})
        votos_base["municipio_norm"] = votos_base["municipio"].map(_normalize_municipio_name)
        votos_base = votos_base.merge(
            df_tse_ref[["codigo_ibge", "nome_municipio", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    else:
        return pd.DataFrame()

    votos_base["qt_votos"] = pd.to_numeric(votos_base["qt_votos"], errors="coerce").fillna(0)
    agg_map = {"qt_votos": "sum", "municipio": "first"}
    if rank_col and rank_col in votos_base.columns:
        votos_base[rank_col] = pd.to_numeric(votos_base[rank_col], errors="coerce")
        agg_map[rank_col] = "min"
    votos_base = (
        votos_base.dropna(subset=["codigo_ibge"])
        .groupby("codigo_ibge", as_index=False)
        .agg(agg_map)
    )

    emenda_value_col = next(
        (
            col
            for col in (
                "valor_pago_atualizado",
                "valor_empenhado_ano",
                "valor_indicado",
                "valor_emenda",
            )
            if col in emendas_df.columns
        ),
        None,
    )
    if emenda_value_col is None:
        return pd.DataFrame()

    emendas = emendas_df.copy()
    if "cd_ibge_municipio" in emendas.columns:
        emendas["codigo_ibge"] = emendas["cd_ibge_municipio"].astype("string")
    elif "nm_municipio" in emendas.columns:
        emendas["municipio_norm"] = emendas["nm_municipio"].map(_normalize_municipio_name)
        emendas = emendas.merge(
            df_tse_ref[["codigo_ibge", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    elif "municipio" in emendas.columns:
        emendas["municipio_norm"] = emendas["municipio"].map(_normalize_municipio_name)
        emendas = emendas.merge(
            df_tse_ref[["codigo_ibge", "municipio_norm"]],
            on="municipio_norm",
            how="left",
        )
    else:
        return pd.DataFrame()

    emendas[emenda_value_col] = pd.to_numeric(emendas[emenda_value_col], errors="coerce").fillna(0)
    extra_emenda_cols = [
        col
        for col in (
            "valor_total_emendas_municipio",
            "total_votos_municipio",
            "indice_retorno_parlamentar",
            "classificacao_retorno_parlamentar",
        )
        if col in emendas.columns
    ]
    emendas_agg = {emenda_value_col: "sum", **{col: "first" for col in extra_emenda_cols}}
    emendas_base = (
        emendas.dropna(subset=["codigo_ibge"])
        .groupby("codigo_ibge", as_index=False)
        .agg(emendas_agg)
        .rename(columns={emenda_value_col: "valor_emendas"})
    )

    result = df_municipios_ref.copy()
    result["codigo_ibge"] = result["codigo_ibge"].astype("string")
    result = result.dropna(subset=["codigo_ibge"]).merge(votos_base, on="codigo_ibge", how="left")
    result = result.merge(emendas_base, on="codigo_ibge", how="left")
    result["qt_votos"] = pd.to_numeric(result["qt_votos"], errors="coerce").fillna(0)
    if "total_votos_municipio" in result.columns:
        result["qt_votos"] = (
            pd.to_numeric(result["total_votos_municipio"], errors="coerce")
            .fillna(result["qt_votos"])
            .fillna(0)
        )
    if "valor_total_emendas_municipio" in result.columns:
        result["valor_emendas"] = (
            pd.to_numeric(result["valor_total_emendas_municipio"], errors="coerce")
            .fillna(result["valor_emendas"])
            .fillna(0)
        )
    result["valor_emendas"] = pd.to_numeric(result["valor_emendas"], errors="coerce").fillna(0)
    result["municipio"] = result["municipio"].fillna(result.get("nome"))
    if df_regioes_ref is not None and not df_regioes_ref.empty:
        result = result.merge(
            df_regioes_ref[["codigo_ibge", "mesorregiao_nome", "regiao_imediata_nome"]],
            on="codigo_ibge",
            how="left",
        )
    result["codigo_ibge_str"] = result["codigo_ibge"].astype("string")
    result["municipio_exibicao"] = result["nome"].fillna(result["municipio"]).fillna("Município")
    result["municipio_contexto"] = result["municipio"].fillna(result["municipio_exibicao"]).astype(str)
    result["mesorregiao_exibicao"] = (
        result.get("mesorregiao_nome", pd.Series(index=result.index, dtype="object"))
        .fillna("Mesorregião não informada")
        .astype(str)
    )
    total_votes = float(result["qt_votos"].sum())
    result["pct_votos_total"] = np.where(total_votes > 0, result["qt_votos"] / total_votes, 0.0)
    if "indice_retorno_parlamentar" in result.columns:
        result["indice_retorno"] = pd.to_numeric(result["indice_retorno_parlamentar"], errors="coerce").fillna(0)
    else:
        result["indice_retorno"] = 0.0
    result["indice_retorno"] = pd.to_numeric(result["indice_retorno"], errors="coerce").replace([np.inf, -np.inf], 0).fillna(0)
    if rank_col and rank_col in result.columns:
        result["is_top3_vote"] = pd.to_numeric(result[rank_col], errors="coerce").le(3)
    else:
        top3_codes = set(result.nlargest(3, "qt_votos")["codigo_ibge"].dropna().astype("string"))
        result["is_top3_vote"] = result["codigo_ibge"].astype("string").isin(top3_codes)

    result["categoria_coerencia"] = (
        result.get("classificacao_retorno_parlamentar", pd.Series(index=result.index, dtype="object"))
        .fillna("Sem Expressão")
        .astype(str)
        .str.strip()
    )
    result.loc[result["categoria_coerencia"].eq(""), "categoria_coerencia"] = "Sem Expressão"
    result["categoria_coerencia"] = result["categoria_coerencia"].replace(
        {
            "Sem Expressao": "Sem Expressão",
            "sem expressao": "Sem Expressão",
            "sem expressão": "Sem Expressão",
        }
    )
    no_emendas = result["valor_emendas"].le(0)
    result.loc[no_emendas & result["qt_votos"].gt(0), "categoria_coerencia"] = "Votos sem emendas"
    result.loc[no_emendas & result["qt_votos"].le(0), "categoria_coerencia"] = "Sem votos nem emendas"
    result["motivo_cor"] = result["categoria_coerencia"].map(
        {
            "Reduto Atendido": "Classificação de retorno parlamentar informada no parquet.",
            "Investimento": "Classificação de retorno parlamentar informada no parquet.",
            "Reduto Desassistido": "Classificação de retorno parlamentar informada no parquet.",
            "Sem Expressão": "Classificação de retorno parlamentar informada no parquet.",
            "Votos sem emendas": "O candidato recebeu votos neste município, mas não destinou emendas.",
            "Sem votos nem emendas": "O candidato não recebeu votos nem destinou emendas neste município.",
        }
    ).fillna("Classificação de retorno parlamentar informada no parquet.")
    return result




def _parliamentary_action_kpis(action_df: pd.DataFrame) -> dict[str, str]:
    if action_df.empty:
        return {
            "reciprocidade": "—",
            "reciprocidade_caption": "Sem dados de emendas para calcular",
            "beneficiado": "Sem dados",
            "beneficiado_caption": "Nenhum registro de emenda disponível",
            "media_retorno": "—",
            "media_retorno_caption": "Sem dados de emendas para calcular",
        }

    total_emendas = float(pd.to_numeric(action_df["valor_emendas"], errors="coerce").fillna(0).sum())
    top3_emendas = float(
        pd.to_numeric(action_df.loc[action_df["is_top3_vote"], "valor_emendas"], errors="coerce").fillna(0).sum()
    )
    reciprocidade = top3_emendas / total_emendas if total_emendas > 0 else 0.0

    total_votes = float(pd.to_numeric(action_df["qt_votos"], errors="coerce").fillna(0).sum())
    media_retorno = total_emendas / total_votes if total_votes > 0 else 0.0

    beneficiary = action_df.sort_values("valor_emendas", ascending=False).head(1)
    if beneficiary.empty or float(beneficiary["valor_emendas"].iloc[0]) <= 0:
        beneficiado = "Sem emendas"
        beneficiado_caption = "R$ 0,00 | 0 votos"
    else:
        row = beneficiary.iloc[0]
        beneficiado = str(row.get("municipio_exibicao", "Município"))
        beneficiado_caption = (
            f"{_format_currency(float(row.get('valor_emendas', 0) or 0))} | "
            f"{_format_number(float(row.get('qt_votos', 0) or 0))} votos"
        )

    return {
        "reciprocidade": _format_percent(reciprocidade),
        "reciprocidade_caption": "Das emendas foram para municípios Top 3 do candidato",
        "beneficiado": beneficiado,
        "beneficiado_caption": beneficiado_caption,
        "media_retorno": _format_currency(media_retorno),
        "media_retorno_caption": "Valor médio de emendas por voto no estado",
    }


def _render_parliamentary_action_kpis(action_df: pd.DataFrame) -> None:
    kpis = _parliamentary_action_kpis(action_df)
    st.markdown(
        f"""
        <div class="raiox-kpi-grid">
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Taxa de Reciprocidade</div>
                <div class="mapa-kpi-value">{html.escape(kpis["reciprocidade"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["reciprocidade_caption"])}</div>
            </div>
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Maior Beneficiado (R$)</div>
                <div class="mapa-kpi-value">{html.escape(kpis["beneficiado"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["beneficiado_caption"])}</div>
            </div>
            <div class="raiox-kpi-card">
                <div class="mapa-kpi-label">Média R$/Voto</div>
                <div class="mapa-kpi-value">{html.escape(kpis["media_retorno"])}</div>
                <div class="mapa-kpi-caption">{html.escape(kpis["media_retorno_caption"])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


PARLIAMENTARY_LEGEND_COPY = {
    "Reduto Atendido": {
        "title": "🔵 BASE PRIORIZADA 🎯",
        "description": (
            "Municípios onde houve votação relevante e também emendas. "
            "É a base eleitoral que recebeu retorno parlamentar."
        ),
    },
    "Investimento": {
        "title": "🟢 APOSTA POLÍTICA 🚀",
        "description": (
            "Municípios que receberam emendas mesmo sem serem grandes redutos. "
            "Indicam aposta política ou construção de presença."
        ),
    },
    "Reduto Desassistido": {
        "title": "🟡 BASE EM RISCO ⚠️",
        "description": (
            "Municípios com votos importantes, mas pouca ou nenhuma emenda. "
            "A base pode se sentir pouco atendida."
        ),
    },
    "Sem Expressão": {
        "title": "🟠 PRESENÇA PONTUAL 🔍",
        "description": (
            "Municípios com baixa expressão eleitoral e atuação parlamentar pontual. "
            "Não são prioridade evidente nesse cruzamento."
        ),
    },
    "Votos sem emendas": {
        "title": "🔘 VOTAÇÃO ORGÂNICA 🤝",
        "description": (
            "Municípios onde houve votos para o candidato, mas nenhuma emenda registrada. "
            "A votação apareceu sem retorno parlamentar."
        ),
    },
    "Sem votos nem emendas": {
        "title": "⚪ TERRITÓRIO NEUTRO 🏳️",
        "description": (
            "Municípios sem votos e sem emendas neste recorte. "
            "Não há presença eleitoral nem atuação registrada."
        ),
    },
}


def _render_parliamentary_legend_cards(action_df: pd.DataFrame) -> None:
    if action_df.empty or "categoria_coerencia" not in action_df.columns:
        st.info("Legenda parlamentar indisponível.")
        return

    total_votes = float(pd.to_numeric(action_df.get("qt_votos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    cards = []
    for category, copy in PARLIAMENTARY_LEGEND_COPY.items():
        color = ACTION_COLORS.get(category, "#64748B")
        rows = action_df[action_df["categoria_coerencia"].astype(str).eq(category)].copy()
        cities = int(len(rows))
        votes = float(pd.to_numeric(rows.get("qt_votos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        vote_share = votes / total_votes if total_votes > 0 else 0.0
        cards.append(
            f"""
            <div class="raiox-parliament-card" style="
                --parliament-color: {html.escape(color)};
                background:
                    radial-gradient(circle at 0% 0%, {html.escape(color)}45 0%, {html.escape(color)}1f 42%, transparent 72%),
                    linear-gradient(145deg, {html.escape(color)}28 0%, rgba(7,24,54,.76) 58%, {html.escape(color)}0f 100%);
                border-color: {html.escape(color)}66;
            ">
                <div class="raiox-parliament-card-title">{html.escape(copy["title"])}</div>
                <div class="raiox-parliament-card-metric">
                    {_format_number(cities)} cidades
                    <span>{_format_percent(vote_share)} da votação</span>
                </div>
                <div class="raiox-parliament-card-description">{html.escape(copy["description"])}</div>
            </div>
            """
        )

    st.html(
        """
        <style>
        .raiox-parliament-card-stack {
            display: grid;
            gap: .58rem;
        }
        .raiox-parliament-card {
            min-height: 6rem;
            padding: .68rem .78rem .72rem;
            border: 1px solid;
            border-radius: 16px;
            color: #eaf2ff;
            box-shadow: 0 12px 30px rgba(1, 8, 24, 0.22);
            backdrop-filter: blur(7px);
            -webkit-backdrop-filter: blur(7px);
        }
        .raiox-parliament-card-title {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            padding: .25rem .48rem;
            border: 1px solid color-mix(in srgb, var(--parliament-color), white 25%);
            border-radius: 999px;
            background: color-mix(in srgb, var(--parliament-color), transparent 76%);
            color: #f8fbff;
            font-size: .68rem;
            font-weight: 900;
            line-height: 1.18;
            letter-spacing: .03em;
        }
        .raiox-parliament-card-metric {
            margin-top: .48rem;
            color: #ffffff;
            font-size: 1.06rem;
            font-weight: 900;
            line-height: 1.18;
        }
        .raiox-parliament-card-metric span {
            display: block;
            margin-top: .12rem;
            color: #dbeafe;
            font-size: .82rem;
            font-weight: 750;
        }
        .raiox-parliament-card-description {
            margin-top: .42rem;
            color: #c8d7ef;
            font-size: .74rem;
            line-height: 1.32;
        }
        </style>
        <div class="raiox-parliament-card-stack">
        """ + "".join(cards) + "</div>"
    )


def _parliamentary_map_selection(event: object | None) -> dict[str, str]:
    if event is None:
        return {}
    if hasattr(event, "selection"):
        selection = getattr(event, "selection")
    elif isinstance(event, dict):
        selection = event.get("selection", {})
    else:
        selection = {}
    if isinstance(selection, dict):
        points = selection.get("points", [])
    else:
        points = getattr(selection, "points", [])
    if not points:
        return {}
    point = points[0]
    customdata = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    if customdata is None or len(customdata) < 4:
        return {}
    return {
        "codigo_ibge": str(customdata[3]),
    }


@st.dialog("Emendas destinadas ao município", width="large")
def _parliamentary_emendas_dialog(
    codigo_ibge: str, action_df: pd.DataFrame, emendas_df: pd.DataFrame | None,
) -> None:
    selected = action_df[action_df["codigo_ibge_str"].eq(codigo_ibge)]
    if selected.empty:
        st.info("Município não encontrado no recorte atual.")
        return
    row = selected.iloc[0]
    st.subheader(str(row["municipio_exibicao"]).title())
    st.caption(
        f'{_format_number(float(row["qt_votos"]))} votos · '
        f'{row["categoria_coerencia"]}'
    )
    st.metric("Total de emendas indicado ao município", _format_currency(float(row["valor_emendas"])))
    if emendas_df is None or emendas_df.empty:
        st.info("Detalhamento das emendas indisponível.")
        return
    emendas = emendas_df.copy()
    if "cd_ibge_municipio" in emendas.columns:
        codes = emendas["cd_ibge_municipio"].astype("string")
        emendas = emendas[codes.eq(codigo_ibge)].copy()
    else:
        municipality_col = next(
            (
                col
                for col in ("nm_municipio", "municipio_beneficiario", "municipio")
                if col in emendas.columns
            ),
            None,
        )
        if municipality_col is None:
            st.info("Detalhamento das emendas indisponível.")
            return
        selected_municipality = row.get("municipio")
        if pd.isna(selected_municipality) or not str(selected_municipality).strip():
            selected_municipality = row.get("municipio_exibicao")
        selected_municipality = _normalize_municipio_name(selected_municipality)
        emendas = emendas.loc[
            emendas[municipality_col].map(_normalize_municipio_name).eq(selected_municipality)
        ].copy()
    if emendas.empty:
        st.info("Não há emendas registradas para este município.")
        return
    value_col = next(
        (
            col
            for col in (
                "valor_indicado",
                "valor_empenhado_ano",
                "valor_pago_atualizado",
                "valor_emenda",
            )
            if col in emendas.columns
        ),
        None,
    )
    if value_col is None:
        st.info("Detalhamento das emendas indisponível.")
        return
    finality_col = next(
        (col for col in ("funcao_descricao", "objeto_finalidade") if col in emendas.columns),
        None,
    )
    type_col = next(
        (col for col in ("tipo_indicacao", "tipo_emenda") if col in emendas.columns),
        None,
    )
    emendas["_valor_emenda"] = pd.to_numeric(emendas[value_col], errors="coerce").fillna(0)
    emendas["_finalidade"] = (
        emendas[finality_col] if finality_col else pd.Series("Não informado", index=emendas.index)
    )
    emendas["_tipo_emenda"] = (
        emendas[type_col] if type_col else pd.Series("Não informado", index=emendas.index)
    )
    for col in ("_finalidade", "_tipo_emenda"):
        emendas[col] = emendas[col].fillna("Não informado").astype(str).str.strip()
        emendas.loc[emendas[col].eq(""), col] = "Não informado"
    summary = (
        emendas.groupby(["_finalidade", "_tipo_emenda"], as_index=False)
        .agg(indicacoes=("_valor_emenda", "size"), valor_indicado=("_valor_emenda", "sum"))
        .sort_values("valor_indicado", ascending=False)
        .rename(columns={
            "_finalidade": "Finalidade", "_tipo_emenda": "Tipo de indicação",
            "indicacoes": "Indicações", "valor_indicado": "Valor indicado",
        })
    )
    st.dataframe(
        summary, hide_index=True, width="stretch",
        column_config={
            "Indicações": st.column_config.NumberColumn(format="%d"),
            "Valor indicado": st.column_config.NumberColumn(format="R$ %.2f"),
        },
    )
    st.caption("Valores, finalidade e tipo seguem os dados registrados no parquet de emendas.")


def _bh_parliamentary_emendas_frame(emendas_df: pd.DataFrame | None) -> pd.DataFrame:
    if emendas_df is None or emendas_df.empty:
        return pd.DataFrame()

    municipality_col = next(
        (col for col in ("municipio_beneficiario", "nm_municipio", "municipio") if col in emendas_df.columns),
        None,
    )
    if municipality_col is None:
        return pd.DataFrame()

    emendas = emendas_df.copy()
    city_name = _normalize_municipio_name("Belo Horizonte")
    city_mask = emendas[municipality_col].map(_normalize_municipio_name).eq(city_name)
    return emendas.loc[city_mask].copy()


def _render_bh_parliamentary_summary(
    votos_bairro_df: pd.DataFrame | None,
    emendas_df: pd.DataFrame | None,
) -> pd.DataFrame:
    emendas = _bh_parliamentary_emendas_frame(emendas_df)
    votes = (
        pd.to_numeric(votos_bairro_df.get("qt_votos"), errors="coerce").fillna(0)
        if votos_bairro_df is not None and "qt_votos" in votos_bairro_df.columns
        else pd.Series(dtype=float)
    )
    total_votes = float(votes.sum())
    value_col = next(
        (col for col in ("valor_pago_atualizado", "valor_empenhado_ano", "valor_indicado", "valor_emenda") if col in emendas.columns),
        None,
    )
    values = (
        pd.to_numeric(emendas[value_col], errors="coerce")
        if value_col else pd.Series(dtype=float)
    )
    total_emendas = float(values.fillna(0).sum()) if value_col else None
    years = sorted(
        emendas.get("ano_emenda", pd.Series(dtype=object)).dropna().astype(str).unique().tolist()
    )
    period = f"{years[0]}–{years[-1]}" if years else "Período não informado"
    emenda_count = int(values.notna().sum()) if value_col else 0
    kpis = [
        ("Votos nos bairros de BH", _format_number(total_votes) if total_votes > 0 else "—", "Votação de 2026 no parquet territorial"),
        (
            "Emendas registradas para BH",
            _format_currency(total_emendas) if total_emendas is not None and emenda_count else "Sem dados",
            "Total municipal, sem rateio entre bairros",
        ),
        ("Registros de emenda", _format_number(emenda_count) if emenda_count else "—", period),
    ]
    cards = "".join(
        f'''<div class="raiox-kpi-card" style="margin:.65rem 0">
            <div class="mapa-kpi-label">{html.escape(label)}</div>
            <div class="mapa-kpi-value">{html.escape(value)}</div>
            <div class="mapa-kpi-caption">{html.escape(caption)}</div>
        </div>'''
        for label, value, caption in kpis
    )
    st.markdown(cards, unsafe_allow_html=True)
    return emendas


def _render_bh_emendas_table(emendas: pd.DataFrame) -> None:
    if emendas.empty:
        st.info("Não há registros de emendas para Belo Horizonte nesta pasta.")
        return
    columns = [
        ("ano_emenda", "Ano"),
        ("numero_emenda", "Número"),
        ("tipo_emenda", "Tipo"),
        ("valor_emenda", "Valor indicado"),
        ("objeto_finalidade", "Finalidade / objeto"),
        ("beneficiario_final", "Beneficiário"),
        ("status_emenda", "Status"),
    ]
    selected = [column for column, _ in columns if column in emendas.columns]
    display = emendas[selected].rename(columns=dict(columns)).copy()
    if "Valor indicado" in display.columns:
        display["Valor indicado"] = pd.to_numeric(display["Valor indicado"], errors="coerce")
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={"Valor indicado": st.column_config.NumberColumn(format="R$ %.2f")},
    )


def _render_parliamentary_action_section(
    votos_df: pd.DataFrame | None,
    emendas_df: pd.DataFrame | None,
) -> None:
    _major_section_header(
        "Mapa da atuação parlamentar de acordo com os votos",
        "Compare a atuação municipal em Minas Gerais com a votação por bairro em Belo Horizonte.",
    )
    map_scope = st.radio(
        "Recorte do mapa",
        ["Minas Gerais · municípios", "Belo Horizonte · bairros"],
        horizontal=True,
        key="parliamentary_map_scope",
    )
    if map_scope == "Belo Horizonte · bairros":
        bh_votes = _read_selected_parquet("votos_bairro", scope="bh")
        bh_emendas = _read_selected_parquet("emendas_legislativa", scope="bh")
        map_col, summary_col = st.columns([0.70, 0.30], gap="large")
        with map_col:
            with st.container(border=True, key="parliamentary-bh-map-container"):
                try:
                    fig, _ = municipality_mesh_map("3106200", bh_votes)
                    if fig is None:
                        st.info("Mapa de votação por bairro indisponível para Belo Horizonte.")
                    else:
                        st.plotly_chart(
                            fig,
                            width="stretch",
                            height=680,
                            key=f"pagina1_parliamentary_bh_map_{_candidate_widget_suffix()}",
                            config={"displayModeBar": False},
                        )
                        st.caption(
                            "O mapa mostra os votos de 2026 por bairro. As emendas desta pasta estão registradas "
                            "para Belo Horizonte como um todo e não são distribuídas entre os bairros."
                        )
                except Exception as exc:
                    st.warning(f"Não foi possível carregar o mapa de bairros de Belo Horizonte: {exc}")
        with summary_col:
            bh_emendas_rows = _render_bh_parliamentary_summary(bh_votes, bh_emendas)
        with st.expander("Consultar emendas registradas para Belo Horizonte"):
            _render_bh_emendas_table(bh_emendas_rows)
        return

    action_df = _parliamentary_action_frame(votos_df, emendas_df)
    parliamentary_map_col, parliamentary_cards_col = st.columns([0.70, 0.30], gap="large")
    with parliamentary_map_col:
        _render_parliamentary_action_kpis(action_df)
        with st.container(border=True, key="parliamentary-map-container"):
            fig = parliamentary_map(action_df)
            if fig is not None:
                revision = st.session_state.get("pagina1_parliamentary_map_revision", 0)
                event = st.plotly_chart(
                    fig, width="stretch", height=720,
                    key=f"pagina1_parliamentary_action_map_{revision}",
                    on_select="rerun", selection_mode="points",
                )
                selection = _parliamentary_map_selection(event)
                if selection:
                    st.session_state["pagina1_parliamentary_map_revision"] = revision + 1
                    _parliamentary_emendas_dialog(selection["codigo_ibge"], action_df, emendas_df)
            else:
                st.info("Mapa parlamentar indisponível.")
    with parliamentary_cards_col:
        _render_parliamentary_legend_cards(action_df)


_apply_visual_model()

votos_municipio_df = _read_selected_parquet("votos_municipio")
votos_bairro_df = _read_selected_parquet("votos_bairro")
_render_page_header(_total_votes_label(votos_municipio_df))
_major_section_header("Mapa de Força Eleitoral", "Onde estão concentrados seus votos e a força da sua votação.")
_render_territory_leader(votos_municipio_df)
map_col, cards_col = st.columns([0.70, 0.30], gap="large")
with map_col:
    with st.container(border=True):
        _, filter_col = st.columns([0.70, 0.30], gap="small")
        with filter_col:
            territorial_kind = _territorial_kind_select()
        votos_df = _territorial_map_view(_read_selected_parquet(territorial_kind), territorial_kind)
        fig = territorial_map(votos_df, territorial_kind)
        if fig is not None:
            map_event = st.plotly_chart(
                fig, width="stretch", height=560, key=f"pagina1_territorial_map_{territorial_kind}",
                on_select="rerun", selection_mode="points",
            )
            territory = _selected_territory(map_event, territorial_kind)
            if territory:
                _territorial_drilldown(territory, territorial_kind, votos_municipio_df, votos_bairro_df)
        else:
            st.info("Mapa territorial indisponível.")
with cards_col:
    _render_map_side_cards(votos_municipio_df)
_section_header(
    "Como foi sua votação em Belo Horizonte",
    "Veja sua performance dentro da sua cidade",
)
detail_map_col, detail_cards_col = st.columns([0.70, 0.30], gap="large")
with detail_map_col:
    with st.container(border=True):
        bh_map_year = st.radio(
            "Eleição exibida no mapa",
            ["2020", "2024", "2026"],
            index=2,
            horizontal=True,
            key="bh_neighborhood_map_year",
        )
        try:
            # Belo Horizonte is fixed for this section (IBGE municipality code).
            if bh_map_year in {"2020", "2024"}:
                _render_bh_comparison_legend()
                comparison_df = _read_selected_parquet("votos_bairro", scope="bh")
                mesh_fig, _ = municipality_mesh_map(
                    "3106200", comparison_df, comparison_year=bh_map_year
                )
            else:
                mesh_fig, _ = municipality_mesh_map("3106200", votos_bairro_df)
            if mesh_fig is None:
                if bh_map_year in {"2020", "2024"}:
                    st.info(f"Comparação de votos por bairro para {bh_map_year} indisponível nesta pasta.")
                else:
                    st.info("Mapa de votos por bairro indisponível para Belo Horizonte.")
            else:
                st.plotly_chart(
                    mesh_fig,
                    width="stretch",
                    height=680,
                    key=f"pagina1_malha_belo_horizonte_{bh_map_year}",
                )
                mesh_kind = (mesh_fig.layout.meta or {}).get("mesh_kind")
                scale_type = (mesh_fig.layout.meta or {}).get("scale_type")
                if bh_map_year in {"2020", "2024"}:
                    st.caption(
                        f"O mapa compara a participação do candidato em {bh_map_year} e 2026. "
                        "O tooltip mostra os votos totais de cada eleição e a diferença em pontos percentuais, "
                        "calculada nos locais de votação correspondidos. Os cards laterais permanecem em 2026."
                    )
                elif scale_type == "uniform":
                    st.caption(
                        "Belo Horizonte tem menos de 1.000 votos neste recorte e usa um único tom de azul, "
                        "sem escala de intensidade. Passe o cursor para ver os bairros e seus votos."
                    )
                elif mesh_kind == "setor":
                    scale_label = "logarítmica" if scale_type == "logarithmic" else "linear"
                    st.caption(f"Azul mais escuro indica mais votos. A escala {scale_label} é relativa ao maior valor de Belo Horizonte e, nos setores censitários, ocupa toda a faixa de cores para manter visíveis os setores com votos. O tooltip identifica os bairros do TSE mesmo onde o candidato não recebeu votos; setores sem referência direta usam o bairro territorialmente mais próximo na cidade.")
                else:
                    scale_label = "logarítmica" if scale_type == "logarithmic" else "linear"
                    st.caption(f"Azul mais escuro indica mais votos. A escala {scale_label} considera também a proporção de bairros com votos em Belo Horizonte. Passe o cursor para ver os bairros e seus votos.")
        except Exception as exc:
            st.warning(f"Não foi possível carregar o mapa de bairros de Belo Horizonte: {exc}")
with detail_cards_col:
    _render_neighborhood_side_cards(votos_bairro_df, "3106200")

_major_section_header(
    "Força da política local",
    "Veja se vereadores e prefeitos das cidades foram decisivos na sua votação",
)
capital_local_df = _read_selected_parquet("capital_local")
local_elected_df = _read_selected_parquet("afinidade_eleitos")
selected_local_strength_class = st.session_state.get(LOCAL_STRENGTH_SELECTION_KEY)
local_politics_fig, statewide_market_share, local_politics_summaries = local_political_strength_map(
    capital_local_df,
    votos_municipio_df,
    selected_local_strength_class,
)
local_map_col, local_cards_col = st.columns([0.70, 0.30], gap="large")
with local_map_col:
    with st.container(border=True, key="pagina1_forca_local_map_card"):
        if local_politics_fig is None:
            st.info("Mapa de força política local indisponível.")
        else:
            _render_local_strength_map_legend(statewide_market_share)
            local_map_revision = st.session_state.get(
                LOCAL_STRENGTH_MAP_REVISION_KEY,
                0,
            )
            local_map_event = st.plotly_chart(
                local_politics_fig,
                width="stretch",
                height=682,
                key=f"pagina1_forca_politica_mapa_municipal_{local_map_revision}",
                config={"displayModeBar": False},
                on_select="rerun",
                selection_mode="points",
            )
            local_map_selection = _local_politics_map_selection(local_map_event)
            if local_map_selection:
                st.session_state[LOCAL_STRENGTH_MAP_REVISION_KEY] = (
                    local_map_revision + 1
                )
                _local_politics_municipality_dialog(
                    local_map_selection,
                    capital_local_df,
                    votos_municipio_df,
                    local_elected_df,
                    statewide_market_share,
                )
with local_cards_col:
    _render_local_politics_cards(
        local_politics_summaries,
        selected_local_strength_class,
    )

_render_accumulated_concentration_section(votos_municipio_df)
emendas_legislativa_df = _read_selected_parquet("emendas_legislativa")
_render_parliamentary_action_section(votos_municipio_df, emendas_legislativa_df)
despesas_campanha_df = _read_selected_parquet("despesas_campanha")
gastos_territoriais_df = _read_selected_parquet("gastos_territoriais")
gastos_territoriais_por_tipo_df = _read_selected_parquet("gastos_territoriais_por_tipo")
_render_cost_efficiency_section(
    votos_municipio_df, despesas_campanha_df, gastos_territoriais_df, gastos_territoriais_por_tipo_df
)



