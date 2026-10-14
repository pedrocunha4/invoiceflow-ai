from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from core.api_client import (
    fetch_invoice,
    fetch_invoices,
)
from core.i18n import t
from core.ui import (
    esc,
    html_block,
    section_header,
)

from .invoice_review_components.decision_panel import (
    render_decision_panel,
)
from .invoice_review_components.invoice_details import (
    render_financial_card,
    render_supplier_card,
    render_validation_card,
)
from .invoice_review_components.pdf_panel import (
    render_pdf_panel,
)
from .invoice_review_components.review_header import (
    render_review_header,
)

def select_review_invoice(
    invoice_id: Any,
) -> None:
    st.session_state[
        "review_invoice_id"
    ] = invoice_id


def render_review_workspace(
    invoices: List[Dict[str, Any]],
) -> None:
    valid = [
        invoice
        for invoice in invoices
        if invoice.get("id")
        is not None
    ]

    pending = sum(
        1
        for invoice in valid
        if invoice.get(
            "status"
        ) == "needs_review"
    )

    title_col, queue_col = (
        st.columns(
            [5, 1],
            vertical_alignment="center",
        )
    )

    with title_col:
        section_header(
            t("review.title"),
            t("review.caption"),
        )

    with queue_col:
        if pending:
            html_block(
                '<div class="review-queue-pill">'
                f'{esc(t("review.in_queue", n=pending))}'
                '</div>'
            )

    if not valid:
        st.info(
            t("review.empty")
        )
        return

    labels = {
        invoice["id"]: (
            f'#{invoice["id"]} · '
            f'{invoice.get("supplier_name") or t("chart.unknown_supplier")}'
            f' · '
            f'{invoice.get("invoice_number") or t("review.no_number")}'
        )
        for invoice in valid
    }

    with st.container(
        border=True,
        key="card_review_top",
    ):
        (
            select_col,
            actions_col,
        ) = st.columns(
            [4.5, 1],
            gap="small",
            vertical_alignment="bottom",
        )

        with select_col:
            selected_id = (
                st.selectbox(
                    t(
                        "review.select"
                    ),
                    options=list(
                        labels
                    ),
                    format_func=(
                        lambda invoice_id:
                        labels[invoice_id]
                    ),
                    key=(
                        "review_invoice_id"
                    ),
                )
            )

        current_index = next(
            (
                index
                for index, invoice
                in enumerate(valid)
                if invoice["id"]
                == selected_id
            ),
            0,
        )

        previous_invoice = (
            valid[
                current_index - 1
            ]
            if current_index > 0
            else None
        )

        next_invoice = (
            valid[
                current_index + 1
            ]
            if (
                current_index
                < len(valid) - 1
            )
            else None
        )

        with actions_col:
            (
                previous_col,
                next_col,
            ) = st.columns(
                2,
                gap="small",
            )

            with previous_col:
                st.button(
                    "‹",
                    key=(
                        "review_previous"
                    ),
                    disabled=(
                        previous_invoice
                        is None
                    ),
                    on_click=(
                        select_review_invoice
                    ),
                    args=(
                        (
                            previous_invoice[
                                "id"
                            ],
                        )
                        if previous_invoice
                        else ()
                    ),
                    width="stretch",
                )

            with next_col:
                st.button(
                    "›",
                    key="review_next",
                    disabled=(
                        next_invoice
                        is None
                    ),
                    on_click=(
                        select_review_invoice
                    ),
                    args=(
                        (
                            next_invoice[
                                "id"
                            ],
                        )
                        if next_invoice
                        else ()
                    ),
                    width="stretch",
                )

        invoice, error = (
            fetch_invoice(
                selected_id
            )
        )

        if (
            error
            or invoice is None
        ):
            st.error(
                t(
                    "error.invoice",
                    error=error,
                )
            )
            return

        summary = next(
            (
                item
                for item in valid
                if item["id"]
                == selected_id
            ),
            {},
        )

        currency = (
            invoice.get(
                "currency"
            )
            or summary.get(
                "currency"
            )
        )

        status = invoice.get(
            "status"
        )

        render_review_header(
            invoice,
            status,
        )

    data_col, pdf_col = (
        st.columns(
            [1, 1.1],
            gap="small",
        )
    )

    with data_col:
        with st.container(
            key="review_left_stack"
        ):
            render_supplier_card(
                invoice
            )

            render_financial_card(
                invoice,
                currency,
            )

            render_validation_card(
                invoice
            )

    with pdf_col:
        render_pdf_panel(
            invoice
        )

    render_decision_panel(
        selected_id,
        status,
    )


def render_review_page() -> None:
    invoices, error = (
        fetch_invoices()
    )

    if error:
        section_header(
            t("review.title")
        )

        st.error(
            t(
                "error.invoices",
                error=error,
            )
        )

        return

    render_review_workspace(
        invoices
    )