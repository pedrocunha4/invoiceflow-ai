from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st
from core.i18n import t
from core.ui import (
    card_head_html,
    esc,
    format_money,
    html_block,
)

QUEUE_LIMIT = 5
CARD_HEIGHT = 440

VALIDATION_KEYS = ("validation_errors", "validation_error", "validation_issues",)


def queue_reason(
    invoice: Dict[str, Any],
) -> str:
    for key in VALIDATION_KEYS:
        value = invoice.get(
            key
        )

        if (
            isinstance(
                value,
                (list, tuple),
            )
            and value
        ):
            value = value[0]

        elif (
            isinstance(
                value,
                dict,
            )
            and value
        ):
            value = next(
                iter(
                    value.values()
                )
            )

        if (
            isinstance(
                value,
                str,
            )
            and value.strip()
        ):
            text = value.strip()

            return (
                text
                if len(text) <= 90
                else text[:87] + "..."
            )

    return t(
        "queue.generic"
    )


def recent_first(
    invoices: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    try:
        return sorted(
            invoices,
            key=lambda invoice: int(
                invoice["id"]
            ),
            reverse=True,
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return list(
            invoices
        )


def review_queue_html(
    items: List[Dict[str, Any]],
) -> str:
    rows = []

    for invoice in items:
        supplier = (
            invoice.get(
                "supplier_name"
            )
            or t(
                "chart.unknown_supplier"
            )
        )

        number = (
            invoice.get(
                "invoice_number"
            )
            or t(
                "review.no_number"
            )
        )

        rows.append(
            '<div class="q-row">'
            '<span class="q-dot"></span>'
            '<div class="q-main">'
            f'<div class="q-name">'
            f'{esc(supplier)}'
            f'</div>'
            f'<div class="q-meta">'
            f'{esc(number)} · '
            f'{esc(queue_reason(invoice))}'
            f'</div>'
            '</div>'
            f'<div class="q-amount">'
            f'{esc(format_money(invoice.get("total"), invoice.get("currency")))}'
            f'</div>'
            '</div>'
        )

    return (
        '<div class="q-list">'
        + "".join(rows)
        + "</div>"
    )


def render_review_queue(
    invoices: List[Dict[str, Any]],
    height: int = CARD_HEIGHT,
) -> None:
    pending = [
        invoice
        for invoice in invoices
        if invoice.get(
            "status"
        ) == "needs_review"
    ]

    with st.container(
        border=True,
        height=height,
        key="card_queue",
    ):
        html_block(
            card_head_html(
                t("queue.title"),
                t("queue.caption"),
                badge=len(pending),
            )
        )

        if not pending:
            html_block(
                f'<div class="q-empty">'
                f'{esc(t("queue.empty"))}'
                f'</div>'
            )
            return

        html_block(
            review_queue_html(
                recent_first(
                    pending
                )[:QUEUE_LIMIT]
            )
        )