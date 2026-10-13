"""Plotly choropleths built from the IBGE GeoParquets on Hugging Face."""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from eleitoral.maps.dna_geo_reference import load_geo_reference


LOCAL_STRENGTH_COLORS = {
    "Máquina eficiente": "#22C55E",
    "Traição ou máquina inoperante": "#EF4444",
    "Voto orgânico / opinião": "#3B82F6",
    "Sem penetração": "#94A3B8",
}

LOCAL_STRENGTH_LABELS = {
    "Máquina eficiente": "Alianças de alto retorno",
    "Traição ou máquina inoperante": "Acordos sem entrega",
    "Voto orgânico / opinião": "Votação própria",
    "Sem penetração": "Zonas neutras",
}

LOCAL_STRENGTH_ICONS = {
    "Máquina eficiente": "🤝",
    "Traição ou máquina inoperante": "⚠️",
    "Voto orgânico / opinião": "⭐",
    "Sem penetração": "❄️",
}

LOCAL_STRENGTH_LEGEND = {
    "Máquina eficiente": (LOCAL_STRENGTH_LABELS["Máquina eficiente"], "Nota alta + market share alto"),
    "Traição ou máquina inoperante": (LOCAL_STRENGTH_LABELS["Traição ou máquina inoperante"], "Nota alta + market share baixo"),
    "Voto orgânico / opinião": (LOCAL_STRENGTH_LABELS["Voto orgânico / opinião"], "Nota baixa + market share alto"),
    "Sem penetração": (LOCAL_STRENGTH_LABELS["Sem penetração"], "Nota baixa + market share baixo"),
}


def _normalized_name(value: object) -> str:
    name = unicodedata.normalize("NFKD", str(value or "").strip().upper())
    return " ".join("".join(char for char in name if not unicodedata.combining(char)).split())


def _style(fig, *, colorbar_title: str = ""):
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    fig.update_traces(marker_line_color="rgba(210,228,255,0.75)", marker_line_width=0.45)
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 4, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#eaf2ff"},
        coloraxis_colorbar={"title": colorbar_title},
    )
    return fig


def continuous_choropleth(
    frame: pd.DataFrame, geojson: dict, *, location: str, color: str,
    colors: list[str], hover_name: str, custom_data: list[str] | None = None,
    colorbar_title: str = "", color_range: tuple[float, float] | None = None,
):
    fig = px.choropleth(
        frame, geojson=geojson, locations=location, featureidkey="properties.id",
        color=color, hover_name=hover_name, custom_data=custom_data,
        color_continuous_scale=colors, range_color=color_range,
    )
    return _style(fig, colorbar_title=colorbar_title)


def categorical_choropleth(
    frame: pd.DataFrame, geojson: dict, *, location: str, category: str,
    categories: list[str], colors: list[str], hover_name: str,
    custom_data: list[str] | None = None,
):
    plot_frame = frame.copy()
    plot_frame["_category_index"] = plot_frame[category].map({value: index for index, value in enumerate(categories)})
    count = len(categories)
    scale = [stop for index, color in enumerate(colors)
             for stop in ((index / count, color), ((index + 1) / count, color))]
    fig = continuous_choropleth(
        plot_frame, geojson, location=location, color="_category_index",
        colors=scale, hover_name=hover_name, custom_data=custom_data,
        color_range=(-0.5, count - 0.5),
    )
    fig.update_coloraxes(colorbar={"tickvals": list(range(count)), "ticktext": categories, "title": ""})
    return fig


def _add_boundary(fig, coordinates: tuple[list, list], *, width: float) -> None:
    lon, lat = coordinates
    if lon and lat:
        fig.add_trace(go.Scattergeo(
            lon=lon, lat=lat, mode="lines",
            line={"color": "rgba(255,255,255,0.96)", "width": width},
            hoverinfo="skip", showlegend=False,
        ))


def territorial_map(votes: pd.DataFrame | None, kind: str):
    geojson, tse, municipalities, _ = load_geo_reference()
    if not geojson or votes is None or votes.empty:
        return None
    if kind == "votos_mesorregiao":
        totals = votes.groupby(votes["nm_mesorregiao"].map(_normalized_name))["qt_votos"].sum()
        mesoregion_geojson = geojson.get("mesoregions", {})
        features = mesoregion_geojson.get("features", [])
        if not features:
            return None
        frame = pd.DataFrame({"nome": [feature["properties"]["id"] for feature in features]})
        frame["votos"] = frame["nome"].map(_normalized_name).map(totals).fillna(0)
        frame["votos"] = pd.to_numeric(frame["votos"], errors="coerce").fillna(0)
        frame["votos_cor"] = np.log1p(frame["votos"])
        fig = continuous_choropleth(
            frame, mesoregion_geojson, location="nome", color="votos_cor",
            colors=["#e8f1ff", "#bfd9ff", "#60a5fa", "#2563eb", "#0b1f4d"],
            hover_name="nome", custom_data=["votos"], colorbar_title="Votos",
        )
    else:
        frame = votes.copy()
        if "nivel_territorial" in frame.columns:
            rows = frame["nivel_territorial"].astype(str).str.lower().eq("municipio")
            if rows.any():
                frame = frame[rows]
        if "cd_ibge_municipio" in frame.columns:
            frame["codigo_ibge"] = frame["cd_ibge_municipio"].astype("string")
        else:
            code_col = next((col for col in ("cd_municipio", "CD_MUNICIPIO", "codigo_tse") if col in frame), None)
            if code_col is None:
                return None
            frame["codigo_tse"] = frame[code_col].astype("string")
            frame = frame.merge(tse[["codigo_tse", "codigo_ibge"]], on="codigo_tse", how="left")
        frame = frame.groupby("codigo_ibge", as_index=False)["qt_votos"].sum().rename(columns={"qt_votos": "votos"})
        frame["codigo_ibge"] = frame["codigo_ibge"].astype("string")
        frame = frame.dropna(subset=["codigo_ibge"])
        frame = frame.groupby("codigo_ibge", as_index=False)["votos"].sum()
        all_cities = municipalities[["codigo_ibge", "nome"]].drop_duplicates("codigo_ibge")
        frame = all_cities.merge(frame, on="codigo_ibge", how="left")
        frame["votos"] = pd.to_numeric(frame["votos"], errors="coerce").fillna(0)
        frame["codigo_ibge_str"] = frame["codigo_ibge"].astype("string")
        frame["votos_cor"] = np.log1p(frame["votos"])
        fig = continuous_choropleth(
            frame, geojson, location="codigo_ibge_str", color="votos_cor",
            colors=["#e8f1ff", "#bfd9ff", "#60a5fa", "#2563eb", "#0b1f4d"],
            hover_name="nome", custom_data=["votos"], colorbar_title="Votos",
        )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>Votos: %{customdata[0]:,.0f}<extra></extra>")
    boundaries = geojson.get("regional_lines", {})
    if kind == "votos_mesorregiao":
        fig.update_traces(marker_line_color="rgba(255,255,255,0.96)", marker_line_width=1.5)
        centers = geojson.get("mesoregion_centers", [])
        total_votes = float(pd.to_numeric(votes["qt_votos"], errors="coerce").fillna(0).sum())
        labels = []
        custom_data = []
        for center in centers:
            region_votes = float(totals.get(_normalized_name(center["name"]), 0))
            percentage = 100 * region_votes / total_votes if total_votes > 0 else 0.0
            labels.append(f"{percentage:.1f}%".replace(".", ","))
            custom_data.append([center["name"], region_votes])
        if centers:
            fig.add_trace(go.Scattergeo(
                lon=[center["lon"] for center in centers],
                lat=[center["lat"] for center in centers],
                mode="markers+text", text=labels, textposition="middle center",
                textfont={"color": "#FFFFFF", "size": 11, "family": "Arial Black, Arial, sans-serif"},
                marker={
                    "size": 46, "color": "rgba(5,18,43,0.86)",
                    "line": {"color": "#FFFFFF", "width": 1.2},
                },
                customdata=custom_data,
                hovertemplate="<b>%{customdata[0]}</b><br>Participação: %{text}<br>Votos: %{customdata[1]:,.0f}<extra></extra>",
                showlegend=False,
            ))
    else:
        fig.update_traces(marker_line_color="rgba(255,255,255,0.92)", marker_line_width=1.0)
    _add_boundary(fig, boundaries.get("state", ([], [])), width=3.0)
    return fig


def _territorial_code(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def local_political_strength_map(
    capital_local: pd.DataFrame | None,
    votes: pd.DataFrame | None,
    selected_class: str | None = None,
) -> tuple[go.Figure | None, float | None, list[dict[str, object]]]:
    """Classify the effectiveness of local political capital in each municipality."""
    geojson, tse, municipalities, _ = load_geo_reference()
    capital_required = {"cd_municipio", "nm_municipio", "capital_local_0a100"}
    vote_required = {
        "cd_municipio",
        "nm_municipio",
        "qt_votos",
        "qt_votos_validos_municipio",
        "pct_market_share",
    }
    if (
        not geojson
        or tse is None
        or municipalities is None
        or municipalities.empty
        or capital_local is None
        or capital_local.empty
        or votes is None
        or votes.empty
        or not capital_required.issubset(capital_local.columns)
        or not vote_required.issubset(votes.columns)
    ):
        return None, None, []

    capital = capital_local.copy()
    capital["_codigo_tse"] = _territorial_code(capital["cd_municipio"])
    capital["capital_local_0a100"] = pd.to_numeric(
        capital["capital_local_0a100"], errors="coerce"
    )
    capital = (
        capital.sort_values("capital_local_0a100", ascending=False)
        .drop_duplicates("_codigo_tse")
    )

    municipal_votes = votes.copy()
    if "nivel_territorial" in municipal_votes.columns:
        levels = municipal_votes["nivel_territorial"].astype(str).str.strip().str.casefold()
        if levels.eq("municipio").any():
            municipal_votes = municipal_votes.loc[levels.eq("municipio")].copy()
    municipal_votes["_codigo_tse"] = _territorial_code(municipal_votes["cd_municipio"])
    for column in ("qt_votos", "qt_votos_validos_municipio", "pct_market_share"):
        municipal_votes[column] = pd.to_numeric(municipal_votes[column], errors="coerce")
    municipal_votes = municipal_votes.groupby("_codigo_tse", as_index=False).agg(
        nm_municipio=("nm_municipio", "first"),
        qt_votos=("qt_votos", "sum"),
        qt_votos_validos_municipio=("qt_votos_validos_municipio", "max"),
        pct_market_share=("pct_market_share", "first"),
    )

    valid_votes = float(municipal_votes["qt_votos_validos_municipio"].fillna(0).sum())
    candidate_votes = float(municipal_votes["qt_votos"].fillna(0).sum())
    if valid_votes > 0:
        statewide_market_share = candidate_votes / valid_votes * 100
    else:
        available_shares = municipal_votes["pct_market_share"].dropna()
        statewide_market_share = (
            float(available_shares.median()) if not available_shares.empty else 0.0
        )

    code_reference = tse[["codigo_tse", "codigo_ibge"]].drop_duplicates().copy()
    code_reference["codigo_tse"] = _territorial_code(code_reference["codigo_tse"])
    code_reference["codigo_ibge"] = _territorial_code(code_reference["codigo_ibge"])
    combined = capital.merge(municipal_votes, on="_codigo_tse", how="left")
    votes_by_name = municipal_votes.copy()
    votes_by_name["_municipio_norm"] = votes_by_name["nm_municipio"].map(
        _normalized_name
    )
    votes_by_name = votes_by_name.drop_duplicates("_municipio_norm").set_index(
        "_municipio_norm"
    )
    combined["_municipio_norm"] = combined["nm_municipio_x"].map(_normalized_name)
    for column in ("qt_votos", "pct_market_share"):
        combined[column] = combined[column].fillna(
            combined["_municipio_norm"].map(votes_by_name[column])
        )
    combined = combined.merge(
        code_reference,
        left_on="_codigo_tse",
        right_on="codigo_tse",
        how="left",
    )

    municipality_reference = municipalities[["codigo_ibge", "nome"]].drop_duplicates(
        "codigo_ibge"
    ).copy()
    municipality_reference["codigo_ibge"] = _territorial_code(
        municipality_reference["codigo_ibge"]
    )
    name_to_code = dict(
        zip(
            municipality_reference["nome"].map(_normalized_name),
            municipality_reference["codigo_ibge"],
        )
    )
    combined["codigo_ibge"] = combined["codigo_ibge"].fillna(
        combined["nm_municipio_x"].map(_normalized_name).map(name_to_code)
    )
    combined = combined.dropna(subset=["codigo_ibge"]).drop_duplicates("codigo_ibge")

    frame = municipality_reference.rename(columns={"nome": "municipio"}).merge(
        combined[[
            "codigo_ibge",
            "capital_local_0a100",
            "pct_market_share",
            "qt_votos",
        ]],
        on="codigo_ibge",
        how="left",
    )
    frame["codigo_ibge_str"] = frame["codigo_ibge"].astype("string")
    frame["municipio"] = frame["municipio"].fillna("Município")
    frame["capital_local_0a100"] = pd.to_numeric(
        frame["capital_local_0a100"], errors="coerce"
    )
    frame["pct_market_share"] = pd.to_numeric(
        frame["pct_market_share"], errors="coerce"
    )
    frame["qt_votos"] = pd.to_numeric(frame["qt_votos"], errors="coerce").fillna(0)
    note_high = frame["capital_local_0a100"].gt(50)
    market_share_high = frame["pct_market_share"].ge(statewide_market_share)
    valid_classification = (
        frame["capital_local_0a100"].notna()
        & frame["pct_market_share"].notna()
    )
    frame["classe_forca_local"] = np.select(
        [
            valid_classification & note_high & market_share_high,
            valid_classification & note_high & ~market_share_high,
            valid_classification & ~note_high & market_share_high,
        ],
        [
            "Máquina eficiente",
            "Traição ou máquina inoperante",
            "Voto orgânico / opinião",
        ],
        default="Sem penetração",
    )
    frame["leitura_forca_local"] = frame["classe_forca_local"].map(
        {key: value[0] for key, value in LOCAL_STRENGTH_LEGEND.items()}
    )
    frame["nota_label"] = frame["capital_local_0a100"].map(
        lambda value: f"{value:.1f}/100" if pd.notna(value) else "Indisponível"
    )
    frame["market_share_label"] = frame["pct_market_share"].map(
        lambda value: f"{value:.2f}%" if pd.notna(value) else "Indisponível"
    )
    frame["referencia_label"] = f"{statewide_market_share:.2f}%"

    total_candidate_votes = float(frame["qt_votos"].sum())
    summaries: list[dict[str, object]] = []
    for classification in LOCAL_STRENGTH_COLORS:
        class_rows = frame.loc[
            frame["classe_forca_local"].eq(classification)
        ].copy()
        class_votes = float(class_rows["qt_votos"].sum())
        leader = class_rows.sort_values("qt_votos", ascending=False).head(1)
        summaries.append({
            "classification": classification,
            "municipalities": int(len(class_rows)),
            "votes": class_votes,
            "vote_share": (
                class_votes / total_candidate_votes if total_candidate_votes > 0 else 0.0
            ),
            "leader": (
                str(leader.iloc[0]["municipio"]).title() if not leader.empty else "—"
            ),
            "leader_votes": (
                float(leader.iloc[0]["qt_votos"]) if not leader.empty else 0.0
            ),
        })

    selected_class = (
        selected_class if selected_class in LOCAL_STRENGTH_COLORS else None
    )
    map_colors = [
        color if selected_class in (None, classification) else "#334155"
        for classification, color in LOCAL_STRENGTH_COLORS.items()
    ]
    fig = categorical_choropleth(
        frame,
        geojson,
        location="codigo_ibge_str",
        category="classe_forca_local",
        categories=list(LOCAL_STRENGTH_COLORS),
        colors=map_colors,
        hover_name="municipio",
        custom_data=[
            "classe_forca_local",
            "leitura_forca_local",
            "nota_label",
            "market_share_label",
            "referencia_label",
            "codigo_ibge_str",
            "municipio",
        ],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>%{customdata[1]}"
            "<br>Capital local: %{customdata[2]}"
            "<br>Market share municipal: %{customdata[3]}"
            "<br>Referência estadual: %{customdata[4]}<extra></extra>"
        ),
        marker_line_color="rgba(255,255,255,0.92)",
        marker_line_width=1.0,
    )
    fig.update_coloraxes(showscale=False)
    _add_boundary(fig, geojson.get("regional_lines", {}).get("state", ([], [])), width=3.0)
    return fig, statewide_market_share, summaries


def local_political_strength_municipality_map(
    codigo_ibge: str,
    municipality: str,
    classification: str,
) -> go.Figure | None:
    """Render only the selected municipality using its local-strength class color."""
    geojson, _, _, _ = load_geo_reference()
    if not geojson or classification not in LOCAL_STRENGTH_COLORS:
        return None

    code = str(codigo_ibge).strip()
    selected_features = [
        feature
        for feature in geojson.get("features", [])
        if str(feature.get("properties", {}).get("id", "")).strip() == code
    ]
    if not selected_features:
        return None

    selected_geojson = {
        "type": "FeatureCollection",
        "features": selected_features,
    }
    frame = pd.DataFrame(
        {
            "codigo_ibge": [code],
            "municipio": [municipality],
            "classe_forca_local": [classification],
        }
    )
    fig = categorical_choropleth(
        frame,
        selected_geojson,
        location="codigo_ibge",
        category="classe_forca_local",
        categories=[classification],
        colors=[LOCAL_STRENGTH_COLORS[classification]],
        hover_name="municipio",
        custom_data=["classe_forca_local"],
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<extra></extra>",
        marker_line_color="rgba(255,255,255,0.98)",
        marker_line_width=2.4,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(margin={"l": 4, "r": 4, "t": 4, "b": 4})
    return fig
