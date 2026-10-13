"""Mapa e paleta originais da seção de emendas de deputados_streamlit."""
from __future__ import annotations
import pandas as pd
from eleitoral.maps.dna_geo_reference import load_geo_reference
from eleitoral.maps.choropleth_maps import categorical_choropleth

ACTION_COLORS = {
    "Reduto Atendido": "#2563EB", "Investimento": "#16A34A",
    "Reduto Desassistido": "#FACC15", "Sem Expressão": "#F97316",
    "Votos sem emendas": "#64748B", "Sem votos nem emendas": "#FFFFFF",
}

ACTION_LEGEND = {
    "Reduto Atendido": "Reduto eleitoral com emendas",
    "Investimento": "Emendas destinadas ao município",
    "Reduto Desassistido": "Reduto com retorno limitado",
    "Sem Expressão": "Baixa expressão eleitoral",
    "Votos sem emendas": "Recebeu votos, sem emendas",
    "Sem votos nem emendas": "Sem votos e sem emendas",
}


def parliamentary_map(action: pd.DataFrame):
    geojson, _, municipalities, _ = load_geo_reference()
    if not geojson or action is None or action.empty:
        return None
    frame = municipalities[["codigo_ibge", "nome"]].drop_duplicates("codigo_ibge").rename(columns={"nome": "nome_malha"})
    frame["codigo_ibge_str"] = frame["codigo_ibge"].astype("string")
    action = action.copy()
    action["codigo_ibge_str"] = action["codigo_ibge_str"].astype("string")
    frame = frame.merge(action, on="codigo_ibge_str", how="left")
    frame["categoria_coerencia"] = frame["categoria_coerencia"].fillna("Sem votos nem emendas")
    frame["municipio_exibicao"] = frame["municipio_exibicao"].fillna(frame["nome_malha"])
    frame["qt_votos"] = pd.to_numeric(frame["qt_votos"], errors="coerce").fillna(0)
    frame["valor_emendas"] = pd.to_numeric(frame["valor_emendas"], errors="coerce").fillna(0)
    fig = categorical_choropleth(
        frame, geojson, location="codigo_ibge_str", category="categoria_coerencia",
        categories=list(ACTION_COLORS), colors=list(ACTION_COLORS.values()),
        hover_name="municipio_exibicao", custom_data=["categoria_coerencia", "qt_votos", "valor_emendas", "codigo_ibge_str"],
    )
    fig.update_traces(hovertemplate=(
        "<b>%{hovertext}</b><br>%{customdata[0]}<br>Votos: %{customdata[1]:,.0f}"
        "<br>Emendas: R$ %{customdata[2]:,.2f}<extra></extra>"
    ))
    fig.update_coloraxes(showscale=False)
    return fig
