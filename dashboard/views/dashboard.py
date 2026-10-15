from __future__ import annotations

import streamlit as st
from core.api_client import (
    fetch_invoices,
    fetch_stats,
)
from core.i18n import t
from core.ui import section_header

from .dashboard_components.invoice_registry import (
    render_invoice_table,
)
from .dashboard_components.metrics import (
    render_metrics,
)
from .dashboard_components.review_queue import (
    render_review_queue,
)
from .dashboard_components.supplier_chart import (
    render_supplier_chart,
)


def render_dashboard() -> None:
    section_header(
        t("dashboard.overview"),
        t(
            "dashboard.overview_caption"
        ),
    )

    stats, error = fetch_stats()

    if error:
        st.error(
            t(
                "error.stats",
                error=error,
            )
        )

    else:
        render_metrics(
            stats or {}
        )

    invoices, error = fetch_invoices()

    if error:
        st.error(
            t(
                "error.invoices",
                error=error,
            )
        )

    else:
        with st.container(
            key="dashboard_mid_row"
        ):
            (
                chart_col,
                queue_col,
            ) = st.columns(
                [3, 2],
                gap="small",
            )

            with chart_col:
                render_supplier_chart(
                    invoices
                )

            with queue_col:
                render_review_queue(
                    invoices
                )

        render_invoice_table(
            invoices
        )
