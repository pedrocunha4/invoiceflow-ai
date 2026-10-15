from __future__ import annotations

from typing import Any

import streamlit as st
from core.api_client import process_invoice
from core.i18n import t
from core.ui import (
    card_head_html,
    html_block,
    inject_upload_css,
    section_header,
    set_flash,
)


def render_processing_result(
    outcome: str,
    payload: Any,
) -> None:
    if outcome == "success":
        set_flash(
            "success",
            t("process.success"),
        )

        # Clear the uploaded PDF after success
        st.session_state["upload_version"] = (
            st.session_state.get(
                "upload_version",
                0,
            )
            + 1
        )

        st.rerun()

    elif outcome == "duplicate":
        st.warning(
            payload
        )

    elif outcome == "invalid_invoice":
        st.warning(
            payload
        )

    elif outcome == "network":
        # Generic message only: raw connection details
        # are never exposed to the user.
        st.error(
            t(
                "api.connection_unavailable"
            )
        )

    else:
        st.error(
            t(
                "process.service_error"
            )
        )


def render_upload_section() -> None:
    section_header(
        t("process.title"),
        t("process.caption"),
    )

    # Uploader styling + translated dropzone text.
    inject_upload_css()

    with st.container(
        border=True,
        key="process_card",
    ):
        html_block(
            card_head_html(
                t("process.uploader")
            )
        )

        upload_version = (
            st.session_state.get(
                "upload_version",
                0,
            )
        )

        uploaded_file = st.file_uploader(
            t("process.uploader"),
            type=["pdf"],
            key=(
                f"invoice_upload_"
                f"{upload_version}"
            ),
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            st.caption(
                f"{uploaded_file.name} · "
                f"{uploaded_file.size / 1024:,.1f} KB"
            )

        clicked = st.button(
            t("process.button"),
            type="primary",
            icon=":material/auto_awesome:",
            disabled=uploaded_file is None,
            key="btn_process",
            width="stretch",
        )

    if (
        clicked
        and uploaded_file is not None
    ):
        with st.spinner(
            t("process.spinner")
        ):
            outcome, payload = (
                process_invoice(
                    uploaded_file
                )
            )

        render_processing_result(
            outcome,
            payload,
        )