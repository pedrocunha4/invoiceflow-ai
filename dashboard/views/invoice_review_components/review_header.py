from __future__ import annotations

from typing import Any, Dict

from core.i18n import t
from core.status import status_meta
from core.ui import (
    display,
    esc,
    html_block,
    icon_svg,
)

from .invoice_details import validation_issues


def render_review_header(
    invoice: Dict[str, Any],
    status: Any,
) -> None:
    meta = status_meta(
        status
    )

    number = display(
        invoice.get(
            "invoice_number"
        )
    )

    supplier = display(
        invoice.get(
            "supplier_name"
        )
    )

    issues = validation_issues(
        invoice
    )

    html = (
        '<div class="review-invoice-head">'
        '<div>'
        '<div class="inv-head">'
        f'<span class="inv-no">{esc(number)}</span>'
        f'<span class="badge badge-{meta["tone"]}">'
        f'{esc(meta["label"])}'
        '</span>'
        '</div>'
        f'<div class="inv-sub">{esc(supplier)}</div>'
        '</div>'
        '<div class="review-last-update">'
        f'{esc(t("review.last_update_ai"))}'
        '</div>'
        '</div>'
    )

    if issues:
        html += (
            '<div class="review-flag">'
            '<span class="review-flag-icon">'
            f'{icon_svg("warn", 15)}'
            '</span>'
            '<span>'
            f'<strong>{esc(t("review.flagged"))}:</strong> '
            f'{esc(issues[0])}'
            '</span>'
            '</div>'
        )

    html_block(
        html
    )