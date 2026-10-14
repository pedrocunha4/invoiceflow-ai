from __future__ import annotations

import streamlit as st

from core.api_client import check_api_health
from core.i18n import (
    DEFAULT_LANG,
    LANGUAGES,
    t,
)
from core.ui import (
    FAVICON_PATH,
    esc,
    html_block,
    inject_css,
    inject_dynamic_css,
    load_icon_b64,
    render_flash,
)
from views.dashboard import render_dashboard
from views.invoice_review import render_review_page
from views.process_invoice import render_upload_section

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NAV_PAGES = [
    "Dashboard",
    "Process Invoice",
    "Invoice Review",
]

NAV_ICONS = {
    "Dashboard": "dashboard",
    "Process Invoice": "upload_file",
    "Invoice Review": "fact_check",
}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def render_language_switch() -> None:
    st.segmented_control(
        "Language",
        list(LANGUAGES),
        default=DEFAULT_LANG,
        required=True,
        key="lang",
        label_visibility="collapsed",
        width="stretch",
    )


def render_header() -> None:
    with st.container(
        key="app_header"
    ):
        title_col, lang_col = st.columns(
            [8, 1.3]
        )

        with lang_col:
            render_language_switch()

        with title_col:
            st.title(
                t("header.title")
            )

            st.caption(
                t("header.subtitle")
            )


def brand_html() -> str:
    logo = load_icon_b64(
        96
    )

    img = (
        f'<img src="data:image/png;base64,{logo}" alt="">'
        if logo
        else ""
    )

    return (
        '<div class="brand">'
        f'{img}'
        '<div>'
        '<div class="brand-name">'
        'InvoiceFlow <span>AI</span>'
        '</div>'
        '<div class="brand-sub">'
        f'{esc(t("sidebar.tagline"))}'
        '</div>'
        '</div>'
        '</div>'
    )


def render_sidebar(
    api_online: bool,
) -> str:
    with st.sidebar:
        html_block(
            brand_html()
        )

        page = st.radio(
            "Navigation",
            NAV_PAGES,
            key="page",
            label_visibility="collapsed",
            format_func=lambda page_id: (
                f":material/{NAV_ICONS[page_id]}: "
                f"{t(f'nav.{page_id}')}"
            ),
        )

        with st.container(
            key="sidebar_status"
        ):
            if api_online:
                html_block(
                    '<div class="api-card">'
                    '<span class="api-dot"></span>'
                    '<span>'
                    f'{esc(t("sidebar.api_online"))}'
                    '</span>'
                    '</div>'
                )

            else:
                html_block(
                    '<div class="api-card api-card-off">'
                    '<span class="api-dot"></span>'
                    '<span>'
                    f'{esc(t("sidebar.api_offline"))}'
                    '</span>'
                    '</div>'
                )

        return page


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="InvoiceFlow AI",
        page_icon=str(FAVICON_PATH),
        layout="wide",
    )

    inject_css()

    api_online = check_api_health()

    render_header()

    inject_dynamic_css()

    page = render_sidebar(
        api_online
    )

    render_flash()

    if not api_online:
        st.error(
            t("api.unreachable")
        )
        return

    if page == "Dashboard":
        render_dashboard()

    elif page == "Process Invoice":
        render_upload_section()

    else:
        render_review_page()


if __name__ == "__main__":
    main()