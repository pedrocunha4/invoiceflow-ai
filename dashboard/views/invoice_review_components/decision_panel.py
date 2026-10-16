from __future__ import annotations

from typing import Any

import streamlit as st
from core.api_client import update_invoice_status
from core.i18n import t
from core.ui import (
    card_head_html,
    html_block,
    set_flash,
)


def handle_review_decision(
    invoice_id: Any,
    new_status: str,
    level: str,
    message: str,
) -> None:
    if (
        st.session_state.get(
            "demo_role"
        )
        == "viewer"
    ):
        return

    ok, error = update_invoice_status(
        invoice_id,
        new_status,
    )

    if ok:
        set_flash(
            level,
            message,
        )
    else:
        set_flash(
            "error",
            error,
        )


def render_decision_panel(
    invoice_id: Any,
    current_status: Any,
) -> None:
    read_only = (
        st.session_state.get(
            "demo_role"
        )
        == "viewer"
    )

    decisions = [
        (
            t("decision.approve"),
            "approved",
            "btn_approve",
            "success",
            t("decision.approved_msg"),
            ":material/check_circle:",
        ),
        (
            t("decision.needs_review"),
            "needs_review",
            "btn_review",
            "warning",
            t("decision.review_msg"),
            ":material/error:",
        ),
        (
            t("decision.reject"),
            "rejected",
            "btn_reject",
            "error",
            t("decision.rejected_msg"),
            ":material/cancel:",
        ),
    ]

    with st.container(
        border=True,
        key="card_decision",
    ):
        html_block(
            card_head_html(
                t("decision.title"),
                t("decision.caption"),
            )
        )

        if read_only:
            st.info(
                t(
                    "decision.read_only"
                )
            )

        columns = st.columns(
            3,
            gap="small",
        )

        for column, (
            label,
            status,
            key,
            level,
            message,
            icon,
        ) in zip(
            columns,
            decisions,
        ):
            with column:
                st.button(
                    label,
                    key=key,
                    icon=icon,
                    disabled=(
                        read_only
                        or current_status
                        == status
                    ),
                    on_click=(
                        handle_review_decision
                    ),
                    args=(
                        invoice_id,
                        status,
                        level,
                        message,
                    ),
                    width="stretch",
                )