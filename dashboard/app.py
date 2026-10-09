from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = "http://127.0.0.1:8000"

NAV_PAGES = ["Dashboard", "Process Invoice", "Invoice Review"]

STATUS_META: Dict[str, Dict[str, str]] = {
    "approved": {"label": "Approved", "color": "green", "dot": "🟢"},
    "needs_review": {"label": "Needs Review", "color": "orange", "dot": "🟡"},
    "rejected": {"label": "Rejected", "color": "red", "dot": "🔴"},
}
STATUS_LABEL_TO_KEY = {meta["label"]: key for key, meta in STATUS_META.items()}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}

# Keys the API may use to return validation findings for an invoice.
# Adjust to match your backend response if it uses a different field name.
VALIDATION_KEYS = ("validation_errors", "validation_error", "validation_issues")

# ---------------------------------------------------------------------------
# Styling (single, centralised CSS block - no component HTML anywhere else)
# ---------------------------------------------------------------------------

CSS = """
<style>
.stApp { background-color: #0B1220; color: #E2E8F0; }
.stApp p, .stApp label, .stApp li, [data-testid="stMarkdownContainer"] { color: #E2E8F0; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppDeployButton"], .stDeployButton, #MainMenu, footer { display: none !important; }
.block-container { padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1200px; }
h1 { font-size: 1.9rem !important; font-weight: 650 !important; letter-spacing: -0.02em; color: #F8FAFC !important; padding-bottom: 0.1rem !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; color: #F1F5F9 !important; margin-top: 0.8rem; }
h4 { font-size: 1.05rem !important; font-weight: 600 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #94A3B8 !important; }
hr { border-color: #1F2D47 !important; margin: 1.2rem 0 !important; }
[data-testid="stSidebar"] { background-color: #0A1222; border-right: 1px solid #1B2740; }
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 0.25rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: 0.55rem 0.8rem; border-radius: 10px; width: 100%; cursor: pointer; border: 1px solid transparent; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background-color: #111B2E; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background-color: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.35); }
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child:not([data-testid="stMarkdownContainer"]) { display: none; }
[data-testid="stMetric"] { background-color: #111B2E; border: 1px solid #1F2D47; border-radius: 12px; padding: 1rem 1.1rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 0.8rem; }
[data-testid="stMetricValue"] { color: #F8FAFC; font-size: 1.7rem; font-weight: 600; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: #1F2D47 !important; }
[data-testid="stDataFrame"] { border: 1px solid #1F2D47; border-radius: 12px; overflow: hidden; }
[data-testid="stExpander"] { border: 1px solid #1F2D47; border-radius: 12px; }
[data-testid="stAlert"] { border-radius: 10px; }
[data-testid="stFileUploaderDropzone"] {background-color: #0D1626; border: 1.5px dashed #2B3C5E; border-radius: 12px;  padding: 2.8rem 1.5rem; min-height: 150px;}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #3B82F6; }
[data-baseweb="select"] > div, [data-baseweb="input"] > div { background-color: #0D1626 !important; border-color: #26354F !important; border-radius: 10px !important; }
.stButton > button { width: 100%; min-height: 2.6rem; border-radius: 10px; border: 1px solid #26354F; background-color: #111B2E; color: #E2E8F0; font-weight: 500; transition: all 0.15s ease; }
.stButton > button:hover { border-color: #3B82F6; color: #FFFFFF; }
.stButton > button:disabled { opacity: 0.4; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] { background-color: #2563EB; border-color: #2563EB; color: #FFFFFF; }
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="stBaseButton-primary"]:hover { background-color: #1D4ED8; border-color: #1D4ED8; }
.st-key-btn_approve button { border-color: #15803D; color: #4ADE80; }
.st-key-btn_approve button:hover:not(:disabled) { background-color: rgba(34, 197, 94, 0.12); border-color: #22C55E; color: #4ADE80; }
.st-key-btn_review button { border-color: #B45309; color: #FBBF24; }
.st-key-btn_review button:hover:not(:disabled) { background-color: rgba(245, 158, 11, 0.12); border-color: #F59E0B; color: #FBBF24; }
.st-key-btn_reject button { border-color: #B91C1C; color: #F87171; }
.st-key-btn_reject button:hover:not(:disabled) { background-color: rgba(239, 68, 68, 0.12); border-color: #EF4444; color: #F87171; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def display(value: Any) -> str:
    return "—" if value in (None, "") else str(value)


def format_money(value: Any, currency: Optional[str] = None) -> str:
    amount = to_float(value)
    if amount is None:
        return "—"
    code = str(currency or "EUR").upper()
    return f"{amount:,.2f} {CURRENCY_SYMBOLS.get(code, code)}"


def md_escape(text: Any) -> str:
    """Escape Markdown control characters in values coming from the API."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|$<>~])", r"\\\1", str(text))


def status_meta(status: Any) -> Dict[str, str]:
    default = {
        "label": str(status or "Unknown").replace("_", " ").title(),
        "color": "gray",
        "dot": "⚪",
    }
    return STATUS_META.get(status, default)


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def set_flash(level: str, message: str) -> None:
    st.session_state["flash"] = (level, message)


def render_flash() -> None:
    flash = st.session_state.pop("flash", None)
    if not flash:
        return
    level, message = flash
    {"success": st.success, "warning": st.warning, "error": st.error}.get(
        level, st.info
    )(message)


def section_header(title: str, caption: Optional[str] = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)


def field(label: str, value: Any, highlight: bool = False) -> None:
    text = md_escape(display(value))
    shown = f":blue[**{text}**]" if highlight else f"**{text}**"
    st.markdown(f":gray[{label}]  \n{shown}")


# ---------------------------------------------------------------------------
# API layer
# ---------------------------------------------------------------------------


def api_get(path: str, timeout: int = 10) -> Tuple[Optional[Any], Optional[str]]:
    try:
        response = requests.get(f"{API_BASE_URL}{path}", timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError:
        return None, "The API returned an invalid JSON response."


def check_api_health() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def fetch_stats() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = api_get("/dashboard/stats")
    if error:
        return None, error
    return (data if isinstance(data, dict) else {}), None


def fetch_invoices() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    data, error = api_get("/invoices")
    if error:
        return [], error
    invoices = data.get("invoices", []) if isinstance(data, dict) else []
    return invoices, None


def fetch_invoice(invoice_id: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = api_get(f"/invoices/{invoice_id}")
    if error:
        return None, error
    if not isinstance(data, dict):
        return None, "Unexpected response format."
    return data, None


def process_invoice(uploaded_file: Any) -> Tuple[str, Any]:
    """Send the PDF to the API. Returns (outcome, payload)."""

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf"
        )
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/invoices/extract",
            files=files,
            timeout=60
        )

    except requests.RequestException as exc:
        return "network", str(exc)

    # Successfully processed
    if response.status_code == 200:
        return "success", safe_json(response)

    # Duplicate invoice
    if response.status_code == 409:
        body = safe_json(response)

        detail = (
            body.get("detail")
            if isinstance(body, dict)
            else None
        )

        message = "Duplicate invoice detected."

        if isinstance(detail, dict):
            message = detail.get(
                "message",
                message
            )

        elif isinstance(detail, str):
            message = detail

        return "duplicate", message

    # PDF exists but is not a valid invoice
    if response.status_code == 422:
        body = safe_json(response)

        detail = (
            body.get("detail")
            if isinstance(body, dict)
            else None
        )

        if isinstance(detail, str):
            message = detail
        else:
            message = (
                "The uploaded PDF could not be "
                "recognized as a valid invoice."
            )

        return "invalid_invoice", message

    # Other errors
    body = safe_json(response)

    return "error", (
        response.status_code,
        body if body is not None else response.text
    )


def update_invoice_status(invoice_id: Any, new_status: str) -> Tuple[bool, str]:
    try:
        response = requests.patch(
            f"{API_BASE_URL}/invoices/{invoice_id}/status",
            json={"status": new_status},
            timeout=10,
        )
    except requests.RequestException as exc:
        return False, f"Could not connect to the API: {exc}"
    if response.status_code == 200:
        return True, ""
    return False, f"Status update failed (HTTP {response.status_code})."


# ---------------------------------------------------------------------------
# Layout: sidebar + header
# ---------------------------------------------------------------------------


def render_sidebar(api_online: bool) -> str:
    with st.sidebar:
        st.markdown("### :blue[◆] InvoiceFlow AI")
        st.caption("Intelligent invoice processing")
        page = st.radio(
            "Navigation", NAV_PAGES, key="page", label_visibility="collapsed"
        )
        st.divider()
        if api_online:
            st.markdown(":green[●] **API Online**")
        else:
            st.markdown(":red[●] **API Offline**")
        return page

def render_header() -> None:
    st.title("Invoice Operations")
    st.caption(
        "Review, validate and approve supplier invoices extracted by AI."
    )


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


def render_metrics(stats: Dict[str, Any]) -> None:
    columns = st.columns(5, gap="medium")
    total_value = to_float(stats.get("total_amount")) or 0.0
    cards = [
        ("Total Invoices", f'{int(to_float(stats.get("total_invoices")) or 0)}'),
        ("🟢 Approved", f'{int(to_float(stats.get("approved")) or 0)}'),
        ("🟡 Needs Review", f'{int(to_float(stats.get("needs_review")) or 0)}'),
        ("🔴 Rejected", f'{int(to_float(stats.get("rejected")) or 0)}'),
        ("Total Processed Value", f"{total_value:,.2f} €"),
    ]
    for column, (label, value) in zip(columns, cards):
        column.metric(label, value)


def filter_invoices(
    invoices: List[Dict[str, Any]], query: str, status_label: str
) -> List[Dict[str, Any]]:
    query = query.strip().lower()
    status_key = STATUS_LABEL_TO_KEY.get(status_label)
    result = []
    for invoice in invoices:
        if status_key and invoice.get("status") != status_key:
            continue
        haystack = (
            f'{invoice.get("supplier_name", "")} {invoice.get("invoice_number", "")}'
        ).lower()
        if query and query not in haystack:
            continue
        result.append(invoice)
    return result


def render_invoice_table(invoices: List[Dict[str, Any]]) -> None:
    section_header(
        "Invoice Registry",
        "All processed invoices and their current review status.",
    )
    if not invoices:
        st.info(
            "No invoices have been processed yet. "
            "Open Process Invoice to upload your first PDF."
        )
        return

    with st.container(border=True):
        search_col, status_col = st.columns([3, 1.3])
        query = search_col.text_input(
            "Search",
            placeholder="Search by supplier or invoice number",
            label_visibility="collapsed",
            key="registry_search",
        )
        status_label = status_col.selectbox(
            "Status filter",
            ["All statuses"] + list(STATUS_LABEL_TO_KEY),
            label_visibility="collapsed",
            key="registry_status",
        )
        filtered = filter_invoices(invoices, query, status_label)
        st.caption(f"Showing {len(filtered)} of {len(invoices)} invoices")

        if not filtered:
            st.info("No invoices match your filters.")
            return

        rows = []
        for invoice in filtered:
            meta = status_meta(invoice.get("status"))
            rows.append(
                {
                    "ID": invoice.get("id"),
                    "Supplier": invoice.get("supplier_name"),
                    "VAT Number": invoice.get("supplier_vat_number"),
                    "Invoice Number": invoice.get("invoice_number"),
                    "Date": invoice.get("invoice_date"),
                    "Amount": to_float(invoice.get("total")),
                    "Currency": invoice.get("currency"),
                    "Status": f'{meta["dot"]} {meta["label"]}',
                }
            )

        st.dataframe(
            rows,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d", width="small"),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            },
        )


def render_dashboard() -> None:
    section_header("Overview", "Processing volume and review status at a glance.")
    stats, error = fetch_stats()
    if error:
        st.error(f"Unable to load dashboard statistics: {error}")
    else:
        render_metrics(stats or {})

    invoices, error = fetch_invoices()
    if error:
        st.error(f"Unable to load invoices: {error}")
    else:
        render_invoice_table(invoices)


# ---------------------------------------------------------------------------
# Process Invoice page
# ---------------------------------------------------------------------------


def render_processing_result(
    outcome: str,
    payload: Any
) -> None:

    if outcome == "success":

        set_flash(
            "success",
            (
                "Invoice processed successfully "
                "and added to the registry."
            )
        )

        # Clear the uploaded PDF after success
        st.session_state["upload_version"] = (
            st.session_state.get(
                "upload_version",
                0
            ) + 1
        )

        st.rerun()

    elif outcome == "duplicate":

        st.warning(
            f"Duplicate invoice: {payload}"
        )

    elif outcome == "invalid_invoice":

        st.warning(
            f"Invalid invoice: {payload}"
        )

    elif outcome == "network":

        st.error(
            f"Could not connect to the API: {payload}"
        )

    else:

        status_code, body = payload

        st.error(
            (
                "The invoice could not be processed. "
                f"HTTP {status_code}."
            )
        )

        with st.expander(
            "Technical details"
        ):

            if isinstance(
                body,
                (dict, list)
            ):
                st.json(body)

            else:
                st.text(
                    body
                    or "The response body was empty."
                )

def render_upload_section() -> None:

    section_header(
        "Process Invoice",
        "Upload a PDF and let the AI extract, validate and register it.",
    )

    with st.container(border=True):

        upload_version = st.session_state.get("upload_version", 0)
        uploaded_file = st.file_uploader("Invoice PDF", type=["pdf"], key=f"invoice_upload_{upload_version}",)

        if uploaded_file is not None:

            st.caption(
                f"{uploaded_file.name} · "
                f"{uploaded_file.size / 1024:,.1f} KB"
            )

        st.write("")

        clicked = st.button(
            "Process with AI",
            type="primary",
            disabled=uploaded_file is None,
            key="btn_process",
            use_container_width=True,
        )

    if clicked and uploaded_file is not None:

        with st.spinner(
            "Extracting and validating invoice..."
        ):

            outcome, payload = process_invoice(
                uploaded_file
            )

        render_processing_result(
            outcome,
            payload
        )

# ---------------------------------------------------------------------------
# Invoice Review page
# ---------------------------------------------------------------------------


def render_review_header(invoice: Dict[str, Any], status: Any) -> None:
    meta = status_meta(status)
    left, right = st.columns([3, 1])
    with left:
        st.markdown(f"#### {md_escape(display(invoice.get('invoice_number')))}")
        st.caption(
            f"Invoice #{invoice.get('id')} · "
            f"{md_escape(display(invoice.get('supplier_name')))}"
        )
    with right:
        st.caption("Current status")
        st.markdown(f"#### :{meta['color']}[● {meta['label']}]")


def render_supplier_card(invoice: Dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("**Supplier details**")
        left, right = st.columns(2)
        with left:
            field("Supplier", invoice.get("supplier_name"))
            field("Invoice Number", invoice.get("invoice_number"))
        with right:
            field("VAT Number", invoice.get("supplier_vat_number"))
            field("Invoice Date", invoice.get("invoice_date"))


def render_financial_card(invoice: Dict[str, Any], currency: Optional[str]) -> None:
    with st.container(border=True):
        st.markdown("**Financial summary**")
        first, second, third = st.columns(3)
        with first:
            field("Subtotal", format_money(invoice.get("subtotal"), currency))
        with second:
            field("VAT", format_money(invoice.get("vat_amount"), currency))
        with third:
            field("Total", format_money(invoice.get("total"), currency), highlight=True)


def render_validation_card(invoice: Dict[str, Any]) -> None:
    key = next((k for k in VALIDATION_KEYS if k in invoice), None)
    if key is None:
        return
    issues = invoice[key]
    if isinstance(issues, str):
        issues = [issues] if issues.strip() else []
    elif isinstance(issues, dict):
        issues = [f"{k}: {v}" for k, v in issues.items()]
    elif not isinstance(issues, list):
        issues = [str(issues)] if issues else []

    with st.container(border=True):
        st.markdown("**Validation**")
        if issues:
            items = "\n".join(f"- {md_escape(item)}" for item in issues)
            st.warning(f"The validation checks flagged the following:\n\n{items}")
        else:
            st.success("No validation issues reported.")


def render_decision_panel(invoice_id: Any, current_status: Any) -> None:
    decisions = [
        ("Approve", "approved", "btn_approve", "success", "Invoice approved."),
        (
            "Needs Review",
            "needs_review",
            "btn_review",
            "warning",
            "Invoice marked for review.",
        ),
        ("Reject", "rejected", "btn_reject", "error", "Invoice rejected."),
    ]
    with st.container(border=True):
        st.markdown("**Review decision**")
        st.caption("Your decision is saved immediately and reflected in the registry.")
        columns = st.columns(3)
        for column, (label, status, key, level, message) in zip(columns, decisions):
            with column:
                if st.button(label, key=key, disabled=current_status == status):
                    ok, error = update_invoice_status(invoice_id, status)
                    if ok:
                        set_flash(level, message)
                        st.rerun()
                    else:
                        st.error(error)


def render_review_workspace(invoices: List[Dict[str, Any]]) -> None:
    section_header(
        "Invoice Review",
        "Verify the AI-extracted data and record your decision.",
    )
    valid = [inv for inv in invoices if inv.get("id") is not None]
    if not valid:
        st.info("There are no invoices to review yet. Process an invoice first.")
        return

    labels = {
        inv["id"]: (
            f'#{inv["id"]} · {inv.get("supplier_name") or "Unknown supplier"}'
            f' · {inv.get("invoice_number") or "no number"}'
        )
        for inv in valid
    }
    selected_id = st.selectbox(
        "Select an invoice",
        options=list(labels),
        format_func=lambda invoice_id: labels[invoice_id],
        key="review_invoice_id",
    )

    invoice, error = fetch_invoice(selected_id)
    if error or invoice is None:
        st.error(f"Unable to load invoice: {error}")
        return

    summary = next((inv for inv in valid if inv["id"] == selected_id), {})
    currency = invoice.get("currency") or summary.get("currency")
    status = invoice.get("status")

    render_review_header(invoice, status)
    detail_col, finance_col = st.columns([1.2, 1], gap="large")
    with detail_col:
        render_supplier_card(invoice)
    with finance_col:
        render_financial_card(invoice, currency)
    render_validation_card(invoice)
    render_decision_panel(selected_id, status)


def render_review_page() -> None:
    invoices, error = fetch_invoices()
    if error:
        section_header("Invoice Review")
        st.error(f"Unable to load invoices: {error}")
        return
    render_review_workspace(invoices)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="InvoiceFlow AI", page_icon="dashboard/icon/favicon.png", layout="wide")
    inject_css()

    api_online = check_api_health()
    page = render_sidebar(api_online)
    render_header()
    render_flash()

    if not api_online:
        st.error(
            f"The API is not reachable at {API_BASE_URL}. "
            "Start the FastAPI server and click Refresh data."
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
