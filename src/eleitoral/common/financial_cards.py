"""Expandable cards for the shared financial overview."""
from __future__ import annotations

import html
from decimal import Decimal, InvalidOperation

import pandas as pd


def financial_values(frame: pd.DataFrame | None) -> dict[str, Decimal | None]:
    """Read one candidate summary without summing repeated or unrelated totals."""
    values = {}
    for field in ("receita_total", "receita_financeira", "receita_estimavel", "despesa_contratada", "despesa_paga"):
        value = None
        if frame is not None and len(frame) == 1 and field in frame.columns:
            try:
                parsed = Decimal(str(frame.iloc[0][field]))
                if parsed.is_finite():
                    value = parsed
            except (InvalidOperation, ValueError, TypeError):
                pass
        values[field] = value
    for field, left, right in (
        ("resultado", "receita_financeira", "despesa_paga"),
        ("saldo_a_pagar", "despesa_contratada", "despesa_paga"),
    ):
        values[field] = values[left] - values[right] if values[left] is not None and values[right] is not None else None
    return values


def _money(value: Decimal | None) -> str:
    if value is None:
        return "Indisponível"
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _indicator(title: str, value: Decimal | None, description: str, status: bool = False) -> str:
    diagnostic = ""
    if status and value is not None:
        tone, label = (
            ("positive", "↑ Caixa positivo") if value > 0 else
            ("negative", "↓ Déficit temporário de liquidez") if value < 0 else
            ("neutral", "Caixa equilibrado")
        )
        diagnostic = f'<span class="financial-status financial-status-{tone}">{label}</span>'
    return (
        f'<div class="financial-indicator"><h4>{html.escape(title)}</h4>'
        f'<div class="financial-value">{_money(value)}</div>{diagnostic}'
        f'<p>{html.escape(description)}</p></div>'
    )


def financial_cards_html(frame: pd.DataFrame | None = None) -> str:
    """Render financial totals and liquidity from the candidate's stage 05a."""
    values = financial_values(frame)
    contents = (
        _indicator("Dinheiro / Espécie", values["receita_financeira"], "Receita financeira: indica a liquidez real disponível.")
        + _indicator("Bens e Serviços Doados", values["receita_estimavel"], "Receita estimável: sem entrada de fluxo de caixa."),
        _indicator("Despesas Contratadas", values["despesa_contratada"], "Volume total de obrigações assumidas.")
        + _indicator("Despesas Pagas", values["despesa_paga"], "Total executado e quitado."),
        _indicator("Saldo Líquido / Resultado", values["resultado"], "Receita financeira − despesas pagas.", status=True)
        + _indicator("Saldo a Pagar", values["saldo_a_pagar"], "Despesas contratadas − despesas pagas. Passivo pendente a ser quitado até o fim da prestação."),
    )
    titles = (
        "Arrecadação (Receitas)",
        "Compromissos (Despesas)",
        "Liquidez & Saúde do Caixa",
    )
    cards = "".join(
        '<details class="financial-overview-card">'
        '<summary><span class="financial-overview-badge">'
        f'{html.escape(title)}</span>'
        '<span class="financial-overview-chevron" aria-hidden="true"></span></summary>'
        f'<div class="financial-overview-content">{content}</div></details>'
        for title, content in zip(titles, contents)
    )
    return """<style>
    .financial-overview-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;align-items:start;width:100%;margin:18px 0 28px}
    .financial-overview-card {min-width:0;overflow:hidden;border:1px solid rgba(96,165,250,.3);border-radius:14px;background:linear-gradient(145deg,rgba(11,31,77,.76),rgba(7,24,54,.68));color:#eaf2ff;box-shadow:0 12px 30px rgba(0,0,0,.14)}
    .financial-overview-card[open] {border-color:rgba(147,197,253,.5)}
    .financial-overview-card summary {display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:132px;box-sizing:border-box;padding:20px 18px;cursor:pointer;list-style:none}
    .financial-overview-card summary::-webkit-details-marker {display:none}
    .financial-overview-card summary:hover {background:rgba(96,165,250,.08)}
    .financial-overview-card summary:focus-visible {outline:2px solid #93c5fd;outline-offset:-3px;border-radius:14px}
    .financial-overview-badge {display:inline-flex;align-items:center;min-height:72px;box-sizing:border-box;padding:12px 16px;border:1px solid rgba(134,239,172,.3);border-radius:14px;background:#15803d;color:#fff;font-size:clamp(1.1rem,1.45vw,1.5rem);font-weight:800;line-height:1.3;overflow-wrap:break-word}
    .financial-overview-chevron {width:9px;height:9px;flex:none;border-right:2px solid #93c5fd;border-bottom:2px solid #93c5fd;transform:rotate(45deg);transition:transform .2s;margin:0 3px 5px}
    .financial-overview-card[open] .financial-overview-chevron {transform:rotate(225deg);margin-bottom:0;margin-top:5px}
    .financial-overview-content {min-height:72px;padding:20px;box-sizing:border-box;border-top:1px solid rgba(96,165,250,.2)}
    .financial-indicator + .financial-indicator {margin-top:22px;padding-top:22px;border-top:1px solid rgba(147,197,253,.2)}
    .financial-indicator h4 {margin:0 0 10px;color:#eaf2ff;font-size:1rem;font-weight:750;line-height:1.4}
    .financial-value {color:#f8fbff;font-size:clamp(1.3rem,1.7vw,1.9rem);font-weight:800;line-height:1.25;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
    .financial-indicator p {margin:12px 0 0;color:#b7c7e6;font-size:.85rem;line-height:1.55}
    .financial-status {display:inline-block;margin-top:12px;padding:6px 10px;border-radius:8px;font-size:.8rem;font-weight:700;line-height:1.4}
    .financial-status-positive {background:rgba(22,163,74,.18);color:#86efac}
    .financial-status-negative {background:rgba(220,38,38,.18);color:#fca5a5}
    .financial-status-neutral {background:rgba(147,197,253,.12);color:#bfdbfe}
    @media(max-width:900px) {.financial-overview-grid {grid-template-columns:1fr}}
    @media(max-width:600px) {.financial-overview-grid {grid-template-columns:1fr}.financial-overview-card summary {min-height:110px}}
    </style><div class="financial-overview-grid" role="group" aria-label="Balanço macro e liquidez de caixa">""" + cards + "</div>"
