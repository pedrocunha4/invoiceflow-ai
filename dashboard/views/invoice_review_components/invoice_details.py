from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import streamlit as st
from core.i18n import t
from core.ui import (
    card_head_html,
    display,
    esc,
    format_money,
    html_block,
    icon_svg,
    kv_row_html,
    to_float,
)

VALIDATION_KEYS = ("validation_errors", "validation_error", "validation_issues",)

def translate_validation_issue(
    issue: str,
) -> str:
    """Translate known backend validation messages."""

    total_mismatch = re.fullmatch(
        r"Total mismatch: expected ([\d.]+) but received ([\d.]+)\.",
        issue.strip(),
    )

    if total_mismatch:
        expected, received = total_mismatch.groups()

        return t(
            "validation.total_mismatch",
            expected=expected,
            received=received,
        )

    return issue


def validation_issues(
    invoice: Dict[str, Any],
) -> Optional[List[str]]:
    """Business-validation findings sent by the API."""

    key = next(
        (
            key
            for key in VALIDATION_KEYS
            if key in invoice
        ),
        None,
    )

    if key is None:
        return None

    issues = invoice[key]

    if isinstance(issues, str):
        issues = (
            [issues]
            if issues.strip()
            else []
        )

    elif isinstance(issues, dict):
        issues = [
            f"{key}: {value}"
            for key, value
            in issues.items()
        ]

    elif not isinstance(
        issues,
        list,
    ):
        issues = (
            [str(issues)]
            if issues
            else []
        )

    return [
        translate_validation_issue(
            str(item)
        )
        for item in issues
    ]


def render_supplier_card(
    invoice: Dict[str, Any],
) -> None:
    with st.container(
        border=True,
        key="card_supplier",
    ):
        html_block(
            card_head_html(
                t("card.supplier")
            )
        )

        html_block(
            '<div class="kvs">'
            + kv_row_html(
                t("field.supplier"),
                display(
                    invoice.get(
                        "supplier_name"
                    )
                ),
            )
            + kv_row_html(
                t("field.vat_number"),
                display(
                    invoice.get(
                        "supplier_vat_number"
                    )
                ),
            )
            + kv_row_html(
                t("field.invoice_number"),
                display(
                    invoice.get(
                        "invoice_number"
                    )
                ),
            )
            + kv_row_html(
                t("field.invoice_date"),
                display(
                    invoice.get(
                        "invoice_date"
                    )
                ),
            )
            + "</div>"
        )


def render_financial_card(
    invoice: Dict[str, Any],
    currency: Optional[str],
) -> None:
    with st.container(
        border=True,
        key="card_financial",
    ):
        html_block(
            card_head_html(
                t("card.financial")
            )
        )

        html_block(
            '<div class="kvs">'
            + kv_row_html(
                t("field.subtotal"),
                format_money(
                    invoice.get(
                        "subtotal"
                    ),
                    currency,
                ),
            )
            + kv_row_html(
                t("field.vat"),
                format_money(
                    invoice.get(
                        "vat_amount"
                    ),
                    currency,
                ),
            )
            + kv_row_html(
                t("field.total"),
                format_money(
                    invoice.get(
                        "total"
                    ),
                    currency,
                ),
                total=True,
            )
            + "</div>"
        )


def build_validation_checks(
    invoice: Dict[str, Any],
) -> List[Dict[str, str]]:
    checks: List[
        Dict[str, str]
    ] = []

    subtotal = to_float(
        invoice.get(
            "subtotal"
        )
    )

    vat_amount = to_float(
        invoice.get(
            "vat_amount"
        )
    )

    total = to_float(
        invoice.get(
            "total"
        )
    )

    if (
        subtotal is not None
        and vat_amount is not None
        and total is not None
    ):
        matches = abs(
            (
                subtotal
                + vat_amount
            )
            - total
        ) <= 0.011

        checks.append(
            {
                "tone": (
                    "ok"
                    if matches
                    else "bad"
                ),
                "label": t(
                    "check.totals"
                ),
                "status": (
                    t("check.passed")
                    if matches
                    else t("check.failed")
                ),
            }
        )

    # Stored invoices have already passed the
    # structured API schema.
    checks.append(
        {
            "tone": "ok",
            "label": t(
                "check.structured"
            ),
            "status": t(
                "check.passed"
            ),
        }
    )

    issues = validation_issues(
        invoice
    )

    if issues is not None:
        if issues:
            for issue in issues:
                checks.append(
                    {
                        "tone": "warn",
                        "label": issue,
                        "status": t(
                            "check.warning"
                        ),
                    }
                )

        else:
            checks.append(
                {
                    "tone": "ok",
                    "label": t(
                        "check.business"
                    ),
                    "status": t(
                        "check.passed"
                    ),
                }
            )

    return checks


def render_validation_card(
    invoice: Dict[str, Any],
) -> None:
    icon_for = {
        "ok": "check",
        "warn": "warn",
        "bad": "x",
    }

    rows = "".join(
        (
            f'<div class="chk">'
            f'<span class="chk-ico chk-{check["tone"]}">'
            f'{icon_svg(icon_for[check["tone"]], 14)}'
            f'</span>'
            f'<span class="chk-label">'
            f'{esc(check["label"])}'
            f'</span>'
            f'<span class="chk-status chk-{check["tone"]}">'
            f'{esc(check["status"])}'
            f'</span>'
            f'</div>'
        )
        for check in build_validation_checks(
            invoice
        )
    )

    with st.container(
        border=True,
        key="card_checks",
    ):
        html_block(
            card_head_html(
                t(
                    "validation.checks_title"
                ),
                t(
                    "validation.checks_caption"
                ),
            )
        )

        html_block(
            f'<div class="chks">'
            f'{rows}'
            f'</div>'
        )