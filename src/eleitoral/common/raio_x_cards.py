"""Formatação e cards compartilhados do Raio X."""
import html
import unicodedata
import pandas as pd

def _format_number(value: float | int) -> str:
    return f"{float(value):,.0f}".replace(",", ".")


def _format_percent(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "--"
    return f"{float(value) * 100:.1f}%".replace(".", ",")


def _normalized_text(value: object) -> str:
    value = "" if value is None or pd.isna(value) else str(value)
    return " ".join("".join(
        char for char in unicodedata.normalize("NFKD", value.strip().upper())
        if not unicodedata.combining(char)
    ).split())


def _map_side_card(title: str, value: str, caption: str, badge: str = "", tone: str = "") -> str:
    badge_html = (
        f'<div class="raiox-map-side-badge {tone}">{html.escape(badge)}</div>'
        if badge else ""
    )
    caption_html = (
        f'<div class="raiox-map-side-caption">{html.escape(caption)}</div>'
        if caption else ""
    )
    return (
        '<div class="raiox-map-side-card">'
        f'<div class="raiox-map-side-label">{html.escape(title)}</div>'
        f'<div class="raiox-map-side-value">{html.escape(value)}</div>'
        f'{caption_html}'
        f'{badge_html}</div>'
    )
