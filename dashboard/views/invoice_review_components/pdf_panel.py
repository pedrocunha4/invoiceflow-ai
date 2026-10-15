from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict

import streamlit as st
from core.api_client import (
    fetch_invoice_pdf,
    fetch_invoice_pdf_url,
)
from core.i18n import t
from core.ui import (
    esc,
    html_block,
    icon_svg,
)


def render_pdf_action(
    invoice: Dict[str, Any],
) -> None:
    invoice_id = invoice.get(
        "id"
    )

    file_path = invoice.get(
        "file_path"
    )

    if not file_path:
        st.button(
            t("review.view_pdf"),
            disabled=True,
            key=(
                f"pdf_unavailable_"
                f"{invoice_id}"
            ),
            width="stretch",
        )

        st.caption(
            t(
                "review.pdf_unavailable"
            )
        )

        return

    pdf_url = fetch_invoice_pdf_url(invoice_id)

    if not pdf_url:
        st.button(
            t("review.view_pdf"),
            disabled=True,
            key=f"pdf_url_unavailable_{invoice_id}",
            width="stretch",
        )
        st.caption(t("review.pdf_unavailable"))
        return

    st.link_button(
        t("review.view_pdf"),
        pdf_url,
        width="stretch",
    )


def render_pdf_panel(
    invoice: Dict[str, Any],
) -> None:
    file_path = invoice.get(
        "file_path"
    )

    file_name = (
        Path(
            str(file_path)
        ).name
        if file_path
        else t("pdf.title")
    )

    with st.container(
        border=True,
        key="card_pdf",
    ):
        html_block(
            '<div class="card-head">'
            '<div class="pdf-head">'
            f'<span class="pdf-ico">'
            f'{icon_svg("file", 16)}'
            f'</span>'
            '<div>'
            f'<div class="card-title pdf-file-name">'
            f'{esc(file_name)}'
            f'</div>'
            f'<div class="card-sub">'
            f'{esc(t("pdf.title"))}'
            f'</div>'
            '</div>'
            '</div>'
            '</div>'
        )

        if file_path:
            content = fetch_invoice_pdf(
                invoice.get("id")
            )

            if content:
                encoded = base64.b64encode(
                    content
                ).decode(
                    "ascii"
                )

                html_block(
                    '<div class="pdf-wrap">'
                    '<iframe class="pdf-frame" '
                    f'title="{esc(file_name)}" '
                    f'src="data:application/pdf;base64,{encoded}">'
                    '</iframe>'
                    '</div>'
                )

            else:
                st.info(
                    t(
                        "pdf.preview_unavailable"
                    )
                )

        render_pdf_action(
            invoice
        )