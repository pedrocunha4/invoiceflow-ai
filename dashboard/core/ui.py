from __future__ import annotations

import base64
import html
import io
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from .i18n import t


DASHBOARD_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ASSETS_DIR = (
    DASHBOARD_DIR
    / "assets"
)

STYLES_DIR = (
    ASSETS_DIR
    / "styles"
)

FAVICON_PATH = (
    ASSETS_DIR
    / "icon"
    / "favicon.png"
)

STYLE_FILES = (
    "base.css",
    "components.css",
    "dashboard.css",
    "sidebar.css",
    "process_invoice.css",
    "buttons.css",
    "invoice_review.css",
    "feedback.css",
    "registry.css",
)

MAX_UPLOAD_MB = 10

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
}

# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------

ICONS: dict[str, str] = {
    "file": (
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12'
        'a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<path d="M14 2v6h6"/>'
    ),
    "file_text": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12'
        'a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/>'
        '<path d="M16 13H8"/>'
        '<path d="M16 17H8"/>'
        '<path d="M10 9H8"/>'
    ),
    "check": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "alert": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 8v4"/>'
        '<path d="M12 16h.01"/>'
    ),
    "x": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="m15 9-6 6"/>'
        '<path d="m9 9 6 6"/>'
    ),
    "warn": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14'
        'A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/>'
        '<path d="M12 17h.01"/>'
    ),
    "euro": (
        '<path d="M4 10h12"/>'
        '<path d="M4 14h9"/>'
        '<path d="M19 6a7.7 7.7 0 0 0-5.2-2'
        'A7.9 7.9 0 0 0 6 12c0 4.4 3.5 8 7.8 8'
        ' 2 0 3.8-.8 5.2-2"/>'
    ),
    "sparkles": (
        '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12'
        'l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8'
        'a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9'
        'a2 2 0 0 1-1.3-1.3z"/>'
    ),
    "shield": (
        '<path d="M20 13c0 5-3.5 7.5-7.66 8.95'
        'a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6'
        'a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72'
        'a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5'
        'a1 1 0 0 1 1 1z"/>'
        '<path d="m9 12 2 2 4-4"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
        '<path d="M3 12a9 3 0 0 0 18 0"/>'
    ),
    "workflow": (
        '<rect width="8" height="8" x="3" y="3" rx="2"/>'
        '<path d="M7 11v4a2 2 0 0 0 2 2h4"/>'
        '<rect width="8" height="8" x="13" y="13" rx="2"/>'
    ),
    "arrow": (
        '<path d="M5 12h14"/>'
        '<path d="m12 5 7 7-7 7"/>'
    ),
}


def icon_svg(
    name: str,
    size: int = 16,
) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" '
        'viewBox="0 0 24 24" '
        'fill="none" '
        'stroke="currentColor" '
        'stroke-width="2" '
        'stroke-linecap="round" '
        'stroke-linejoin="round" '
        'aria-hidden="true">'
        f'{ICONS[name]}'
        '</svg>'
    )


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def css_text(value: str) -> str:
    """Make translated text safe inside a CSS content value."""
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
    )


def inject_css() -> None:
    """Load the static dashboard stylesheets."""

    styles: list[str] = []

    try:
        for filename in STYLE_FILES:
            path = (
                STYLES_DIR
                / filename
            )

            styles.append(
                path.read_text(
                    encoding="utf-8"
                )
            )

    except OSError:
        return

    css = "\n\n".join(
        styles
    )

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


def inject_dynamic_css() -> None:
    """Inject CSS containing translated decision labels."""
    approve_hint = css_text(
        t("decision.approve_hint")
    )

    review_hint = css_text(
        t("decision.review_hint")
    )

    reject_hint = css_text(
        t("decision.reject_hint")
    )

    current_label = css_text(
        t("decision.current")
    )

    css = f"""
    <style>

    .st-key-btn_approve button::after,
    .st-key-btn_review button::after,
    .st-key-btn_reject button::after {{
        grid-area: desc;

        padding-left: 1.85rem;

        font-size: 0.8rem;
        font-weight: 400;

        color: var(--muted);
    }}

    .st-key-btn_approve button::after {{
        content: "{approve_hint}";
    }}

    .st-key-btn_review button::after {{
        content: "{review_hint}";
    }}

    .st-key-btn_reject button::after {{
        content: "{reject_hint}";
    }}

    .st-key-btn_approve button:disabled::before,
    .st-key-btn_review button:disabled::before,
    .st-key-btn_reject button:disabled::before {{
        content: "{current_label}";

        position: absolute;

        top: 0.6rem;
        right: 0.7rem;

        padding:
            0.08rem
            0.45rem;

        border:
            1px solid currentColor;

        border-radius: 6px;

        font-size: 0.62rem;
        font-weight: 700;

        letter-spacing: 0.08em;

        text-transform: uppercase;
    }}

    </style>
    """

    st.markdown(
        css,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def load_icon_b64(
    max_px: int,
) -> str:
    try:
        raw = FAVICON_PATH.read_bytes()

    except OSError:
        return ""

    try:
        from PIL import Image

        with Image.open(
            io.BytesIO(raw)
        ) as image:
            image = image.convert(
                "RGBA"
            )

            image.thumbnail(
                (
                    max_px,
                    max_px,
                )
            )

            buffer = io.BytesIO()

            image.save(
                buffer,
                format="PNG",
                optimize=True,
            )

            raw = buffer.getvalue()

    except Exception:
        pass

    return base64.b64encode(
        raw
    ).decode("ascii")


def inject_upload_css() -> None:
    """Inject translated uploader copy and favicon watermark."""
    watermark = load_icon_b64(
        512
    )

    watermark_rule = ""

    if watermark:
        watermark_rule = f"""
        [data-testid="stFileUploaderDropzone"]::before {{
            content: "";

            position: absolute;

            inset: 0;

            background:
                url(
                    "data:image/png;base64,{watermark}"
                )
                center / auto 70%
                no-repeat;

            opacity: 0.06;

            pointer-events: none;

            z-index: 0;
        }}
        """

    drop_title = css_text(
        t("process.drop_title")
    )

    drop_hint = css_text(
        t(
            "process.drop_hint",
            mb=MAX_UPLOAD_MB,
        )
    )

    css = f"""
    <style>

    {watermark_rule}

    [data-testid="stFileUploaderDropzoneInstructions"]::before {{
        content: "{drop_title}";

        font-weight: 650;

        font-size: 1.08rem;

        color: #F1F5F9;
    }}

    [data-testid="stFileUploaderDropzoneInstructions"]::after {{
        content: "{drop_hint}";

        font-size: 0.85rem;

        color: var(--muted);
    }}

    </style>
    """

    st.markdown(
        css,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def esc(value: Any) -> str:
    """HTML-escape data before inserting it into markup."""
    return html.escape(
        str(value),
        quote=True,
    )

def to_float(
    value: Any,
) -> Optional[float]:
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

def display(
    value: Any,
) -> str:
    return (
        "—"
        if value in (None, "")
        else str(value)
    )

def format_money(
    value: Any,
    currency: Optional[str] = None,
) -> str:
    amount = to_float(
        value
    )

    if amount is None:
        return "—"

    code = str(
        currency or "EUR"
    ).upper()

    return (
        f"{amount:,.2f} "
        f"{CURRENCY_SYMBOLS.get(code, code)}"
    )

def set_flash(
    level: str,
    message: str,
) -> None:
    st.session_state["flash"] = (
        level,
        message,
    )

def render_flash() -> None:
    flash = st.session_state.pop(
        "flash",
        None,
    )

    if not flash:
        return

    level, message = flash

    {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
    }.get(
        level,
        st.info,
    )(message)

def section_header(
    title: str,
    caption: Optional[str] = None,
) -> None:
    st.subheader(
        title
    )

    if caption:
        st.caption(
            caption
        )

def html_block(
    markup: str,
) -> None:
    st.markdown(
        markup,
        unsafe_allow_html=True,
    )

def card_head_html(
    title: str,
    caption: Optional[str] = None,
    badge: Optional[Any] = None,
) -> str:
    sub = (
        f'<div class="card-sub">'
        f'{esc(caption)}'
        f'</div>'
        if caption
        else ""
    )

    count = (
        f'<span class="count-badge">'
        f'{esc(badge)}'
        f'</span>'
        if badge is not None
        else ""
    )

    return (
        '<div class="card-head">'
        '<div>'
        f'<div class="card-title">{esc(title)}</div>'
        f'{sub}'
        '</div>'
        f'{count}'
        '</div>'
    )

def kv_row_html(
    label: str,
    value: str,
    total: bool = False,
) -> str:
    cls = (
        "kv kv-total"
        if total
        else "kv"
    )

    return (
        f'<div class="{cls}">'
        f'<span class="kv-k">{esc(label)}</span>'
        f'<span class="kv-v">{esc(value)}</span>'
        '</div>'
    )