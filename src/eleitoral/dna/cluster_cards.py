"""HTML presentation of electoral clusters inside the DNA subsection."""
from __future__ import annotations

import html

import pandas as pd

from eleitoral.common.dna_copy import sentence_label


CLASS_STYLES = {
    "BASE ELEITORAL": ("🎯 Base Principal", "base"),
    "ELEITOR CONSOLIDADO": ("🛡️ Eleitor Consolidado", "consolidated"),
    "ELEITOR EMERGENTE": ("🚀 Eleitor Emergente", "emerging"),
}
DEMOGRAPHIC_ICONS = {
    "Gênero": "👤",
    "Faixa etária": "👴",
    "Escolaridade": "📚",
    "Estado civil": "💍",
}


def cluster_cards_html(profiles: list[dict]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    percent = lambda value: f"{value:.1f}%".replace(".", ",")
    classes = list(CLASS_STYLES)
    classes += sorted({p["classification"] for p in profiles} - set(classes))
    segments = []
    cards = []
    total_share = 0.0

    for classification in classes:
        members = [p for p in profiles if p["classification"] == classification]
        share = sum(max(0.0, float(p["share"])) for p in members)
        label, tone = CLASS_STYLES.get(classification, (sentence_label(classification), "other"))
        total_share += share
        if share > 0:
            segments.append(
                f'<span class="dna-base-segment dna-base-{tone}" style="width:{min(share, 100):.4f}%" '
                f'title="{esc(sentence_label(classification))}: {percent(share)}" '
                f'aria-label="{esc(sentence_label(classification))}: {percent(share)}">'
                f'<span class="dna-base-segment-name">{esc(sentence_label(classification))}</span>'
                f'<strong>{percent(share)}</strong></span>'
            )

        for profile in sorted(members, key=lambda p: p["share"], reverse=True):
            bars = []
            chips = []
            for demographic_label, category, value in profile["demographics"]:
                valid = pd.notna(value) and 0 <= value <= 100
                category_text = sentence_label(category)
                if category_text and category_text.casefold() not in {"nao informado", "não informado"}:
                    icon = DEMOGRAPHIC_ICONS.get(demographic_label, "•")
                    chips.append(
                        f'<span class="dna-base-chip" title="{esc(demographic_label)}">'
                        f'{icon} {esc(category_text)}</span>'
                    )
                bar = (
                    f'<div class="dna-base-track" role="meter" aria-label="{esc(demographic_label)}: {esc(category_text)}" '
                    f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{value:.4f}">'
                    f'<span style="width:{value:.4f}%"></span></div>'
                    if valid else ""
                )
                bars.append(
                    f'<div class="dna-base-demographic"><div><span>{esc(demographic_label)}</span>'
                    f'<strong>{percent(value) if valid else "Não informado"}</strong></div>'
                    f'<p>{esc(category_text)}</p>{bar}</div>'
                )
            votes = f'{profile["votes"]:,.0f}'.replace(",", ".")
            chips_html = f'<span class="dna-base-chips">{"".join(chips)}</span>' if chips else ""
            cards.append(f'''<details class="dna-base-profile">
                <summary class="dna-base-profile-summary">
                    <span class="dna-base-profile-heading">
                        <span class="dna-base-profile-meta"><span class="dna-base-badge dna-base-{tone}">{esc(label)}</span></span>
                        {chips_html}
                    </span>
                    <span class="dna-base-profile-result"><strong>{percent(profile["share"])}</strong><small>da votação do candidato · {votes} votos</small></span>
                    <span class="dna-base-chevron" aria-hidden="true"></span>
                </summary>
                <div class="dna-base-profile-content">
                    <div class="dna-base-demographics">{''.join(bars)}</div>
                    <p class="dna-base-note">Percentuais das categorias dominantes dentro deste perfil.</p>
                    <div class="dna-base-reason"><strong>Leitura estratégica</strong><p>{esc(profile["reason"])}</p></div>
                </div>
            </details>''')

    remainder = max(0.0, 100.0 - total_share)
    if remainder > 0.001:
        segments.append(
            f'<span class="dna-base-segment dna-base-remainder" style="width:{remainder:.4f}%" '
            f'title="Não classificado: {percent(remainder)}">'
            f'<span class="dna-base-segment-name">Não classificado</span>'
            f'<strong>{percent(remainder)}</strong></span>'
        )
    composition = (
        '<div class="dna-base-composition" role="img" aria-label="Composição da votação por classificação">'
        f'<div class="dna-base-composition-track">{"".join(segments)}</div>'
        '</div>'
    )
    content = (
        f'{composition}<div class="dna-base-list">{"".join(cards)}</div>'
        if profiles else '<p class="dna-base-note">Perfis de clusters indisponíveis para este candidato.</p>'
    )
    return f'''<style>
    .dna-base-section {{margin:28px 0;padding:30px;border:1px solid rgba(96,165,250,.3);border-radius:20px;background:linear-gradient(135deg,rgba(11,31,77,.76),rgba(7,24,54,.68));color:#eaf2ff;box-shadow:0 12px 30px rgba(0,0,0,.14)}}
    .dna-base-note {{color:#b7c7e6;font-size:.86rem;line-height:1.5}}
    .dna-base-composition {{margin:22px 0 26px}}
    .dna-base-composition-track {{display:flex;width:100%;height:72px;border-radius:16px;overflow:hidden;background:rgba(147,197,253,.13)}}
    .dna-base-segment {{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;height:100%;flex-shrink:0;min-width:0;overflow:hidden;box-sizing:border-box;padding:8px 6px;color:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.16)}}
    .dna-base-segment + .dna-base-segment {{border-left:1px solid rgba(255,255,255,.22)}}
    .dna-base-segment-name {{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:clamp(.7rem,1.1vw,.98rem);font-weight:750;line-height:1.2}}
    .dna-base-segment strong {{font-size:clamp(.85rem,1.4vw,1.25rem);font-weight:850;line-height:1.2;font-variant-numeric:tabular-nums}}
    .dna-base-segment.dna-base-consolidated,.dna-base-segment.dna-base-emerging {{color:#05233b}}
    .dna-base-base {{background:#2563eb}}
    .dna-base-consolidated {{background:#38bdf8}}
    .dna-base-emerging {{background:#10b981}}
    .dna-base-other {{background:#8b5cf6}}
    .dna-base-remainder {{background:rgba(147,197,253,.13)}}
    .dna-base-list {{display:grid;gap:12px}}
    .dna-base-profile {{min-width:0;border:1px solid rgba(96,165,250,.23);border-radius:14px;background:rgba(15,42,80,.5);overflow-wrap:anywhere}}
    .dna-base-profile[open] {{border-color:rgba(147,197,253,.5);background:rgba(15,42,80,.7)}}
    .dna-base-profile-summary {{display:flex;align-items:center;gap:18px;padding:18px 22px;cursor:pointer;list-style:none}}
    .dna-base-profile-summary::-webkit-details-marker {{display:none}}
    .dna-base-profile-summary:focus-visible {{outline:2px solid #93c5fd;outline-offset:-3px;border-radius:14px}}
    .dna-base-profile-summary:hover {{background:rgba(96,165,250,.08)}}
    .dna-base-profile-heading {{display:flex;flex:1;min-width:0;flex-direction:column;gap:10px}}
    .dna-base-profile-meta {{display:flex;align-items:center;flex-wrap:wrap;gap:9px}}
    .dna-base-badge {{display:inline-flex;align-items:center;max-width:100%;box-sizing:border-box;border-radius:18px;padding:10px 18px;font-size:1.95rem;line-height:1.2;font-weight:800;border:1px solid transparent}}
    .dna-base-badge.dna-base-base {{color:#dbeafe;background:rgba(37,99,235,.24);border-color:rgba(96,165,250,.4)}}
    .dna-base-badge.dna-base-consolidated {{color:#cffafe;background:rgba(56,189,248,.18);border-color:rgba(103,232,249,.35)}}
    .dna-base-badge.dna-base-emerging {{color:#d1fae5;background:rgba(16,185,129,.18);border-color:rgba(52,211,153,.38)}}
    .dna-base-badge.dna-base-other {{color:#ede9fe;background:rgba(139,92,246,.2);border-color:rgba(167,139,250,.35)}}
    .dna-base-chips {{display:flex;flex-wrap:wrap;gap:6px}}
    .dna-base-chip {{display:inline-flex;align-items:center;padding:4px 8px;border:1px solid rgba(147,197,253,.22);border-radius:999px;background:rgba(147,197,253,.09);color:#eaf2ff;font-size:.78rem;line-height:1.3}}
    .dna-base-profile-result {{display:flex;flex-direction:column;align-items:flex-end;gap:3px;white-space:nowrap}}
    .dna-base-profile-result strong {{font-size:1.45rem;color:#93c5fd}}
    .dna-base-profile-result small {{font-size:.78rem;color:#b7c7e6}}
    .dna-base-chevron {{width:9px;height:9px;flex:none;border-right:2px solid #93c5fd;border-bottom:2px solid #93c5fd;transform:rotate(45deg);transition:transform .2s;margin:0 4px 5px}}
    .dna-base-profile[open] .dna-base-chevron {{transform:rotate(225deg);margin-bottom:0;margin-top:5px}}
    .dna-base-profile-content {{padding:20px 22px 22px;border-top:1px solid rgba(96,165,250,.2)}}
    .dna-base-demographics {{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}
    .dna-base-demographic>div:first-child {{display:flex;justify-content:space-between;gap:8px;font-size:.8rem}}
    .dna-base-demographic p {{font-size:.9rem;margin:5px 0 9px;line-height:1.4}}
    .dna-base-track {{height:6px;border-radius:4px;background:rgba(147,197,253,.15);overflow:hidden}}
    .dna-base-track span {{height:100%;display:block;background:#60a5fa;border-radius:4px}}
    .dna-base-reason {{border-top:1px solid rgba(96,165,250,.2);padding-top:16px;font-size:.9rem;line-height:1.6}}
    .dna-base-reason p {{margin:8px 0 0;color:#b7c7e6}}
    @media(max-width:700px) {{.dna-base-profile-summary {{align-items:flex-start;flex-wrap:wrap;gap:12px}}.dna-base-profile-result {{align-items:flex-start;white-space:normal}}.dna-base-chevron {{margin-left:auto}}}}
    @media(max-width:600px) {{.dna-base-section {{padding:18px}}.dna-base-demographics {{grid-template-columns:1fr}}.dna-base-profile-summary {{padding:16px}}.dna-base-profile-content {{padding:18px 16px}}}}
    </style><section class="dna-base-section" aria-label="Base eleitoral do candidato">{content}</section>'''
