"""Histórico 2018/2022 e diagnóstico 2030 exclusivos de deputados."""
from __future__ import annotations

import html
import numpy as np
import pandas as pd
import streamlit as st
from shapely.geometry import mapping
from hf_sync import load_env, hf_filesystem

from eleitoral.common.bh_neighborhood_voting import load_bh_neighborhood_mesh, bh_neighborhood_frame, bh_neighborhood_voting_map
from eleitoral.maps.territorial_mesh import municipality_mesh, municipality_mesh_map, _attach_coordinate_matches, _numeric_code_strings, dominant_tse_rows
from eleitoral.maps.choropleth_maps import categorical_choropleth
from eleitoral.maps.dna_geo_reference import load_municipality_sectors, load_sector_ibge_crosswalk, load_sector_neighborhood_lookup, geography_reference_path, attach_crosswalk_units
from eleitoral.dna.sector_expansion import sector_scores, sector_neighborhoods
from eleitoral.dna.dna_expansion import _read, _diagnostic_city_frame, CLASS_COLORS


def select_election(suffix: str) -> str:
    options = ["2018", "2022", "2026", "Projeção 2030"]
    key = f"deputados_bairros_eleicao_{suffix}"
    if st.session_state.get(key) not in options:
        st.session_state[key] = "2026"
    return st.segmented_control("Eleição exibida no mapa", options, selection_mode="single", key=key) or "2026"


@st.cache_data(show_spinner=False)
def _bh_sector_keys() -> pd.DataFrame:
    """Official exact keys; no spatial inference or names from geography."""
    env = load_env()
    path = geography_reference_path(env, 'MG_setores_CD2022.parquet')
    with hf_filesystem(env.get('HF_TOKEN')).open(path, 'rb') as source:
        frame = pd.read_parquet(source, columns=['code_tract','code_neighborhood'], filters=[('code_muni','==','3106200')])
    frame = frame.rename(columns={'code_tract':'setor','code_neighborhood':'codigo_bairro_ibge'})
    for field in ('setor','codigo_bairro_ibge'):
        frame[field] = _numeric_code_strings(frame[field])
    frame = frame.dropna().drop_duplicates()
    return frame.loc[~frame['setor'].duplicated(keep=False)]


def history_rows(source: pd.DataFrame | None, code: str, year: str) -> pd.DataFrame | None:
    column = f"qt_votos_candidato_bairro_{year}"
    if source is None or column not in source or "cd_ibge_municipio" not in source:
        return None
    rows = source.loc[_numeric_code_strings(source["cd_ibge_municipio"]).eq(code)].copy()
    values = pd.to_numeric(rows[column], errors="coerce")
    if not values.notna().any():
        return None
    rows["qt_votos"] = values
    return rows


def _history_map(source: pd.DataFrame, code: str, year: str, historical: pd.DataFrame):
    if code == "3106200":
        fig, _ = bh_neighborhood_voting_map(historical)
        rows = source.loc[_numeric_code_strings(source["cd_ibge_municipio"]).eq(code)].copy()
        rows["_code"] = _numeric_code_strings(rows["cd_ibge_bairro"])
    else:
        fig, _ = municipality_mesh_map(code, historical, allow_neighborhoods=False, candidate_neighborhood_details=True)
        kind, mesh, column, _ = municipality_mesh(code, allow_neighborhoods=False)
        mesh = mesh.copy()
        mesh["id"] = _numeric_code_strings(mesh[column])
        rows = source.loc[_numeric_code_strings(source["cd_ibge_municipio"]).eq(code)].copy()
        rows = attach_crosswalk_units(rows, kind, code)
    if fig is None:
        return None
    historic_col = f"qt_votos_candidato_bairro_{year}"
    diff_col = f"diff_market_share_bairro_pp_vs_{year}"
    rows["_past"] = pd.to_numeric(rows[historic_col], errors="coerce")
    rows["_current"] = pd.to_numeric(rows["qt_votos"], errors="coerce")
    rows["_diff"] = pd.to_numeric(rows.get(diff_col, pd.Series(index=rows.index, dtype=float)), errors="coerce")
    rows["_weight"] = pd.to_numeric(rows.get(f"qt_votos_validos_bairro_{year}", pd.Series(index=rows.index, dtype=float)), errors="coerce")
    # A source difference is not recomputed from unmatched voting places.
    rows["_weight"] = rows["_weight"].where(rows["_weight"].gt(0) & rows["_diff"].notna())
    rows["_weighted_diff"] = rows["_diff"] * rows["_weight"]
    grouped = rows.groupby("_code").agg(
        past=("_past", lambda x: x.sum(min_count=len(x))),
        current=("_current", lambda x: x.sum(min_count=len(x))),
        weighted=("_weighted_diff", lambda x: x.sum(min_count=1)),
        weight=("_weight", lambda x: x.sum(min_count=1)),
    )
    grouped["diff"] = grouped["weighted"] / grouped["weight"]
    details = {}
    detail_rows = dominant_tse_rows(rows, '_past') if code != '3106200' and kind == 'setor' else rows
    for key, records in detail_rows.groupby("_code"):
        tse = records.groupby(["cd_bairro", "nm_bairro"], dropna=False).agg(past=("_past", lambda x: x.sum(min_count=len(x))), current=("_current", lambda x: x.sum(min_count=len(x))))
        details[key] = "<br>".join(
            html.escape(str(name)) + ("" if code != '3106200' and kind == 'area_ponderada' else f" ({html.escape(str(tse_code))})")
            + f": {year}: {_number(record.past)} votos · 2026: {_number(record.current)} votos"
            for (tse_code, name), record in tse.iterrows()
        )
    for trace in fig.data:
        if trace.type != "choropleth":
            continue
        payload, colors = [], []
        for location in trace.locations:
            record = grouped.loc[str(location)] if str(location) in grouped.index else None
            diff = record["diff"] if record is not None else np.nan
            colors.append(0 if pd.isna(diff) else 1 if diff < -1e-9 else 3 if diff > 1e-9 else 2)
            payload.append([details.get(str(location), "Sem dados do candidato"), "Sem comparação disponível" if pd.isna(diff) else f"{diff:+.2f} p.p.".replace('.', ','), _number(record['past']) if record is not None else 'Indisponível', _number(record['current']) if record is not None else 'Indisponível'])
        trace.update(z=colors, zmin=0, zmax=3, colorscale=[[0,'#94a3b8'],[.2499,'#94a3b8'],[.25,'#ef4444'],[.4999,'#ef4444'],[.5,'#3b82f6'],[.7499,'#3b82f6'],[.75,'#22c55e'],[1,'#22c55e']], customdata=payload,
                     hovertemplate=f"%{{customdata[0]}}<br>Soma dos votos {year}: %{{customdata[2]}}<br>Soma dos votos 2026: %{{customdata[3]}}<br>Diferença média ponderada: %{{customdata[1]}}<extra></extra>")
    return fig


def _number(value) -> str:
    return "Indisponível" if pd.isna(value) else f"{value:,.0f}".replace(',', '.')


def _legend(items):
    st.html('<div style="display:flex;flex-wrap:wrap;gap:8px;margin:8px 0">' + ''.join(
        f'<span style="border:1px solid {color};border-radius:999px;padding:5px 10px;color:{color};font-weight:700">{html.escape(label)}</span>'
        for label, color in items) + '</div>')


def _projection_map(source: pd.DataFrame, code: str):
    scores = sector_scores(_read("diagnostico_geral_setor"), "ELEITOR IDEAL")
    if scores.empty:
        return None
    rows = source.loc[_numeric_code_strings(source["cd_ibge_municipio"]).eq(code)].copy()
    if code == "3106200":
        try:
            lookup = load_sector_neighborhood_lookup()
        except FileNotFoundError:
            lookup = pd.DataFrame(columns=["cd_setor_censitario", "codigo_bairro_ibge", "nome_bairro_ibge"])
        neighborhoods = sector_neighborhoods(load_sector_ibge_crosswalk(), lookup)
        official = _bh_sector_keys()
        # The compact lookup is optional; the full official sector table
        # supplies exact neighborhood codes when the compact index is absent.
        neighborhoods = pd.concat([official, neighborhoods[['setor','codigo_bairro_ibge']]], ignore_index=True).drop_duplicates()
        neighborhoods = neighborhoods.loc[~neighborhoods['setor'].duplicated(keep=False)]
        linked = scores.merge(neighborhoods, on="setor", how="inner", validate="one_to_one")
        linked = linked.loc[linked["codigo_bairro_ibge"].str.fullmatch(r"\d+", na=False) & linked["codigo_bairro_ibge"].str.startswith(code, na=False)]
        if linked.empty:
            return None
        grouped = linked.groupby("codigo_bairro_ibge", as_index=False).agg(
            votos_obtidos_2026=("votos_base", lambda x: x.sum(min_count=len(x))),
            populacao_estimada_icp=("oportunidade_demografica", lambda x: x.sum(min_count=len(x))),
            populacao_total_referencia=("reference", lambda x: x.sum(min_count=len(x))),
            cobertura_dados_completa=("complete", "all"),
        ).rename(columns={"codigo_bairro_ibge": "cd_ibge_municipio_setor"})
        scores = _diagnostic_city_frame(grouped).rename(columns={"codigo_ibge": "setor"})
        mesh = load_bh_neighborhood_mesh().rename(columns={"id": "setor"})
        names = bh_neighborhood_frame(load_bh_neighborhood_mesh(), source).set_index('id')['name']
        source_codes = "cd_ibge_bairro"
    else:
        mesh = load_municipality_sectors(code).rename(columns={"code_tract": "setor"})
        source_codes = "cd_setor_censitario"
        rows = attach_crosswalk_units(rows, "setor", code)
        winner_rows = dominant_tse_rows(rows)
        names = winner_rows.groupby('_code').apply(lambda group: ' / '.join(dict.fromkeys(str(row.nm_bairro) + ' (' + str(row.cd_bairro) + ')' for row in group.itertuples())), include_groups=False) if not winner_rows.empty else pd.Series(dtype=str)
    if mesh.empty:
        return None
    mesh['setor'] = _numeric_code_strings(mesh['setor'])
    frame = mesh[['setor']].drop_duplicates().merge(scores, on='setor', how='left', validate='one_to_one')
    if not frame['classe_expansao'].notna().any():
        return None
    frame['classe_expansao'] = frame['classe_expansao'].fillna('CINZA')
    frame['name'] = frame['setor'].map(names).fillna('Sem bairro TSE vinculado no arquivo do candidato')
    if code == "3106200":
        rows['_code'] = _numeric_code_strings(rows[source_codes])
    votes = rows.groupby('_code')['qt_votos'].agg(lambda x: pd.to_numeric(x, errors='coerce').sum(min_count=1))
    frame['votes'] = frame['setor'].map(votes).map(_number)
    for field in ('oportunidade_demografica', 'similaridade'):
        frame[field+'_label'] = frame[field].map(lambda x: 'Indisponível' if pd.isna(x) else f'{x:,.1f}'.replace(',', '_').replace('.', ',').replace('_', '.'))
    labels = {'AZUL':'Proteger a base', 'VERDE':'Oportunidade alta', 'AMARELO':'Potencial a desenvolver', 'CINZA':'Sem potencial ou dados incompletos'}
    frame['class_label'] = frame['classe_expansao'].map(labels)
    geojson = {'type':'FeatureCollection','features':[
        {'type':'Feature','properties':{'id':str(row.setor)},'geometry':mapping(row.geometry)} for row in mesh.itertuples() if row.geometry is not None and not row.geometry.is_empty]}
    fig = categorical_choropleth(frame, geojson, location='setor', category='classe_expansao', categories=list(CLASS_COLORS), colors=list(CLASS_COLORS.values()), hover_name='name', custom_data=['class_label','votes','oportunidade_demografica_label','similaridade_label'])
    fig.update_coloraxes(showscale=False)
    fig.update_traces(hovertemplate='<b>%{hovertext}</b><br>%{customdata[0]}<br>Votos 2026 (TSE): %{customdata[1]}<br>População estimada do ICP: %{customdata[2]}<br>Parcela na referência: %{customdata[3]}%<extra></extra>')
    return fig


def render_election_mode(source: pd.DataFrame | None, code: str, election: str) -> pd.DataFrame | None:
    if election in {'2018','2022'}:
        historical = history_rows(source, code, election)
        if historical is None:
            st.info(f'Votação de {election} indisponível para este candidato neste município; não é possível afirmar ausência de votos ou candidatura.')
            return None
        _legend([('Aumento','#22c55e'),('Estabilidade','#3b82f6'),('Queda','#ef4444'),('Sem comparação','#94a3b8')])
        fig = _history_map(source, code, election, historical)
        if historical['qt_votos'].isna().any():
            st.caption('Cobertura histórica parcial: os cards consideram somente registros com votos conhecidos.')
        st.caption(f'Comparação com 2026. A cor mostra a média das diferenças de participação fornecidas pelo candidato, ponderada pelos votos válidos de {election}; não presume locais correspondidos. Os cards mostram votos de {election}.')
        cards = historical.loc[historical['qt_votos'].notna()].copy()
    else:
        _legend([('Proteger a base',CLASS_COLORS['AZUL']),('Oportunidade alta',CLASS_COLORS['VERDE']),('Potencial a desenvolver',CLASS_COLORS['AMARELO']),('Sem potencial ou dados incompletos',CLASS_COLORS['CINZA'])])
        fig = _projection_map(source, code) if source is not None else None
        cards = source
        st.caption('Diagnóstico stage09b do eleitor ideal, com os mesmos critérios relativos do DNA. Em BH, bairros oficiais com vínculos exatos; nos demais municípios, setores censitários. Nomes e votos TSE vêm do stage01b; estimativas demográficas vêm do diagnóstico. Os cards mantêm 2026. Potencial não é previsão de votos para 2030.')
    if fig is None:
        st.info(f'Mapa de {election} indisponível para este município.')
    else:
        st.plotly_chart(fig, width='stretch', height=560, key=f'deputados_bairros_mapa_{election}_{code}')
    return cards
