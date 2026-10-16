from __future__ import annotations

from eleitoral.common.local_political_strength import render_local_political_strength
from eleitoral.common.shared_header import (
    apply_shared_visual_model,
    read_selected_parquet,
    render_page_header,
)
from eleitoral.deputados.emendas import render_emendas


def _render_political_impact() -> None:
    votes = read_selected_parquet("votos_municipio")
    render_local_political_strength(votes)
    render_emendas(votes, read_selected_parquet("emendas_legislativa"))


apply_shared_visual_model()
render_page_header("impacto_politico")
_render_political_impact()
