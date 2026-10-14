"""Election modes for the statewide map, using municipal electoral records."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from eleitoral.dna.dna_expansion import CLASS_COLORS, _diagnostic_city_frame
from eleitoral.maps.choropleth_maps import _add_boundary, _normalized_name
from eleitoral.maps.dna_geo_reference import load_geo_reference


HISTORY_COLORS = {"Aumento": "#22c55e", "Estabilidade": "#3b82f6", "Queda": "#ef4444", "Sem comparação": "#94a3b8"}
PROJECTION_LABELS = {"AZUL": "Proteger a base", "VERDE": "Oportunidade alta", "AMARELO": "Potencial a desenvolver", "CINZA": "Sem potencial ou dados incompletos"}


def select_statewide_election(suffix: str) -> str:
    options = ["2018", "2022", "2026", "Projeção 2030"]
    key = f"pagina1_estadual_eleicao_{suffix}"
    if st.session_state.get(key) not in options:
        st.session_state[key] = "2026"
    return st.segmented_control("Eleição exibida no mapa", options, selection_mode="single", key=key) or "2026"


def election_votes(source: pd.DataFrame | None, year: str, *, level: str = "municipio") -> pd.DataFrame | None:
    """Adapt votes for cards/drilldown without turning unknown history into zero."""
    if source is None or source.empty:
        return None
    rows = source.copy()
    if "nivel_territorial" in rows:
        levels = rows["nivel_territorial"].astype(str).str.strip().str.casefold()
        rows = rows.loc[levels.eq(level)].copy()
    column = "qt_votos" if year == "2026" else f"qt_votos_candidato_{'bairro_' if level == 'bairro' else ''}{year}"
    if column not in rows:
        return None
    values = pd.to_numeric(rows[column], errors="coerce")
    rows["qt_votos"] = values.where(np.isfinite(values) & values.ge(0))
    return rows if rows["qt_votos"].notna().any() else None


def _codes(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def _municipal_reference(municipalities: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    reference = municipalities[["codigo_ibge", "nome"]].drop_duplicates("codigo_ibge").copy()
    reference["codigo_ibge"] = _codes(reference["codigo_ibge"])
    region_names = regions[["codigo_ibge", "mesorregiao_nome"]].drop_duplicates("codigo_ibge").copy()
    region_names["codigo_ibge"] = _codes(region_names["codigo_ibge"])
    reference = reference.merge(region_names, on="codigo_ibge", how="left", validate="one_to_one")
    reference["region_id"] = reference["mesorregiao_nome"].map(_normalized_name)
    return reference


def historical_state_frame(source: pd.DataFrame, year: str, kind: str, reference: pd.DataFrame, tse: pd.DataFrame) -> pd.DataFrame:
    rows = election_votes(source, year)
    if rows is None:
        return pd.DataFrame()
    if "cd_ibge_municipio" in rows:
        rows["codigo_ibge"] = _codes(rows["cd_ibge_municipio"])
    elif "cd_municipio" in rows:
        keys = tse[["codigo_tse", "codigo_ibge"]].drop_duplicates().copy()
        keys["codigo_tse"] = _codes(keys["codigo_tse"])
        keys["codigo_ibge"] = _codes(keys["codigo_ibge"])
        rows["codigo_ibge"] = _codes(rows["cd_municipio"]).map(keys.set_index("codigo_tse")["codigo_ibge"])
    else:
        return pd.DataFrame()
    rows = rows.dropna(subset=["codigo_ibge"])
    rows = rows.loc[rows["codigo_ibge"].ne("")].copy()
    if rows.empty:
        return pd.DataFrame()
    rows["past"] = rows["qt_votos"]
    for target, column in (("current", "qt_votos"), ("past_valid", f"qt_votos_validos_{year}"), ("current_valid", "qt_votos_validos_municipio"), ("diff", f"diff_market_share_pp_vs_{year}")):
        values = pd.to_numeric(source.loc[rows.index, column], errors="coerce") if column in source else pd.Series(np.nan, index=rows.index)
        rows[target] = values.where(np.isfinite(values))
    # Municipal records are unique in stage01a. Refuse ambiguous records rather
    # than multiplying municipal denominators or averaging supplied differences.
    if rows["codigo_ibge"].dropna().duplicated().any():
        return pd.DataFrame()
    frame = reference.merge(rows[["codigo_ibge", "past", "current", "past_valid", "current_valid", "diff"]], on="codigo_ibge", how="left", validate="one_to_one")
    frame["diff"] = frame["diff"].where(frame["past"].notna() & frame["current"].notna())
    if kind == "votos_mesorregiao":
        frame = frame.groupby("region_id", as_index=False).agg(
            nome=("mesorregiao_nome", "first"),
            **{column: (column, lambda values: values.sum(min_count=len(values))) for column in ("past", "current", "past_valid", "current_valid")},
        )
        frame["diff"] = (frame["current"] / frame["current_valid"] - frame["past"] / frame["past_valid"]) * 100
        frame["diff"] = frame["diff"].where(frame["past_valid"].gt(0) & frame["current_valid"].gt(0))
        frame["id"] = frame["region_id"]
    else:
        frame["id"] = frame["codigo_ibge"]
    frame["class"] = "Sem comparação"
    frame.loc[frame["diff"].gt(1e-9), "class"] = "Aumento"
    frame.loc[frame["diff"].lt(-1e-9), "class"] = "Queda"
    frame.loc[frame["diff"].abs().le(1e-9), "class"] = "Estabilidade"
    return frame


def projection_state_frame(diagnostic: pd.DataFrame | None, kind: str, reference: pd.DataFrame) -> pd.DataFrame:
    required = {"cd_ibge_municipio_setor", "votos_obtidos_2026", "populacao_estimada_icp", "populacao_total_referencia", "cobertura_dados_completa"}
    if diagnostic is None or not required.issubset(diagnostic.columns):
        return pd.DataFrame()
    scores = _diagnostic_city_frame(diagnostic)
    if scores.empty:
        return pd.DataFrame()
    scores["codigo_ibge"] = _codes(scores["codigo_ibge"])
    if kind == "votos_mesorregiao":
        linked = reference.merge(scores, on="codigo_ibge", how="left", validate="one_to_one")
        linked["complete"] = linked["complete"].fillna(False).astype(bool)
        aggregate = linked.groupby("region_id", as_index=False).agg(
            votos_obtidos_2026=("votos_base", lambda values: values.sum(min_count=len(values))),
            populacao_estimada_icp=("oportunidade_demografica", lambda values: values.sum(min_count=len(values))),
            populacao_total_referencia=("reference", lambda values: values.sum(min_count=len(values))),
            cobertura_dados_completa=("complete", "all"),
        ).rename(columns={"region_id": "cd_ibge_municipio_setor"})
        scores = _diagnostic_city_frame(aggregate)
        units = reference[["region_id", "mesorregiao_nome"]].drop_duplicates("region_id").rename(columns={"region_id": "codigo_ibge", "mesorregiao_nome": "nome"})
    else:
        units = reference[["codigo_ibge", "nome"]]
    frame = units.merge(scores, on="codigo_ibge", how="left", validate="one_to_one")
    frame["id"] = frame["codigo_ibge"]
    frame["class"] = frame["classe_expansao"].fillna("CINZA")
    return frame


def _number(value: object, *, decimals: int = 0) -> str:
    return "Indisponível" if pd.isna(value) or not np.isfinite(value) else f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _figure(frame: pd.DataFrame, geojson: dict, kind: str, colors: dict[str, str], customdata: pd.DataFrame, hovertemplate: str) -> go.Figure | None:
    mesh = geojson.get("mesoregions", {}) if kind == "votos_mesorregiao" else geojson
    features = mesh.get("features", [])
    if not features:
        return None
    mesh = {**mesh, "features": [{**feature, "properties": {**feature["properties"], "id": _normalized_name(feature["properties"]["id"]) if kind == "votos_mesorregiao" else str(feature["properties"]["id"])}} for feature in features]}
    names = list(colors)
    scale = []
    for index, color in enumerate(colors.values()):
        scale.extend([[index / len(names), color], [(index + 1) / len(names), color]])
    fig = go.Figure(go.Choropleth(
        geojson=mesh, locations=frame["id"], featureidkey="properties.id",
        z=frame["class"].map(dict(zip(names, range(len(names))))), zmin=-.5, zmax=len(names)-.5,
        colorscale=scale, showscale=False,
        marker_line_color="rgba(255,255,255,.96)", marker_line_width=1.5 if kind == "votos_mesorregiao" else 1,
        customdata=customdata.to_numpy(), hovertemplate=hovertemplate,
    ))
    _add_boundary(fig, geojson.get("regional_lines", {}).get("state", ([], [])), width=3)
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_layout(margin={"l": 0, "r": 0, "t": 4, "b": 0}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#eaf2ff"})
    return fig


def statewide_election_map(source: pd.DataFrame | None, kind: str, election: str, diagnostic: pd.DataFrame | None = None) -> go.Figure | None:
    geojson, tse, municipalities, regions = load_geo_reference()
    if not geojson or municipalities is None or regions is None:
        return None
    reference = _municipal_reference(municipalities, regions)
    if election == "Projeção 2030":
        frame = projection_state_frame(diagnostic, kind, reference)
        if frame.empty:
            return None
        customdata = pd.DataFrame({"name": frame["nome"].map(html.escape), "class": frame["class"].map(PROJECTION_LABELS), "votes": frame["votos_base"].map(_number), "population": frame["oportunidade_demografica"].map(_number), "share": frame["similaridade"].map(lambda value: _number(value, decimals=1) + "%" if pd.notna(value) else "Indisponível")})
        return _figure(frame, geojson, kind, CLASS_COLORS, customdata,
            "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Votos nos setores associados: %{customdata[2]}<br>População estimada do ICP: %{customdata[3]}<br>Parcela na referência: %{customdata[4]}<extra></extra>")
    if source is None or tse is None or election not in {"2018", "2022"}:
        return None
    frame = historical_state_frame(source, election, kind, reference, tse)
    if frame.empty:
        return None
    customdata = pd.DataFrame({"name": frame["nome"].map(html.escape), "past": frame["past"].map(_number), "current": frame["current"].map(_number), "diff": frame["diff"].map(lambda value: f"{value:+.2f} p.p.".replace(".", ",") if pd.notna(value) else "Sem comparação disponível")})
    return _figure(frame, geojson, kind, HISTORY_COLORS, customdata,
        f"<b>%{{customdata[0]}}</b><br>Votos {election}: %{{customdata[1]}}<br>Votos 2026: %{{customdata[2]}}<br>Diferença de participação: %{{customdata[3]}}<extra></extra>")


def render_statewide_legend(election: str) -> None:
    colors = {label: CLASS_COLORS[key] for key, label in PROJECTION_LABELS.items()} if election == "Projeção 2030" else HISTORY_COLORS
    st.html('<div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0">' + ''.join(
        f'<span style="border:1px solid {color};border-radius:999px;padding:5px 10px;color:{color};font-weight:700">{html.escape(label)}</span>' for label, color in colors.items()
    ) + '</div>')
