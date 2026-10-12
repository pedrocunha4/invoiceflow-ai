from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv(
    "INVOICEFLOW_API_URL",
    "http://127.0.0.1:8000"
)

FAVICON_PATH = Path(__file__).parent / "icon" / "favicon.png"

# Internal page identifiers (used for routing). Display names live in
# TRANSLATIONS under the "nav.<page>" keys.
NAV_PAGES = ["Dashboard", "Process Invoice", "Invoice Review"]

# Internal status keys come from the API and must never be translated.
# Only their display labels (TRANSLATIONS "status.<key>") change per language.
STATUS_META: Dict[str, Dict[str, str]] = {
    "approved": {"color": "green", "dot": "🟢"},
    "needs_review": {"color": "orange", "dot": "🟡"},
    "rejected": {"color": "red", "dot": "🔴"},
}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}

SUPPLIER_CHART_LIMIT = 10

# Keys the API may use to return validation findings for an invoice.
# Adjust to match your backend response if it uses a different field name.
VALIDATION_KEYS = ("validation_errors", "validation_error", "validation_issues")

# ---------------------------------------------------------------------------
# Internationalisation (EN / PT)
# ---------------------------------------------------------------------------

LANGUAGES = ("EN", "PT")
DEFAULT_LANG = "EN"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "EN": {
        # Navigation / sidebar / header
        "nav.Dashboard": "Dashboard",
        "nav.Process Invoice": "Process Invoice",
        "nav.Invoice Review": "Invoice Review",
        "sidebar.tagline": "Intelligent invoice processing",
        "sidebar.api_online": "API Online",
        "sidebar.api_offline": "API Offline",
        "header.title": "Invoice Operations",
        "header.subtitle": "Review, validate and approve supplier invoices extracted by AI.",
        # API / errors
        "api.invalid_json": "The API returned an invalid JSON response.",
        "api.unexpected_format": "Unexpected response format.",
        "api.connect_error": "Could not connect to the API: {error}",
        "api.status_failed": "Status update failed (HTTP {code}).",
        "api.unreachable": "The service is currently unavailable. " "Please try again later.",
        "api.service_unavailable": ("The service is temporarily unavailable. " "Please try again later."),
        "api.connection_unavailable": ("The service could not be reached. " "Please try again later."),
        "api.request_failed": ("The request could not be completed. " "Please try again."),
        "error.stats": "Unable to load dashboard statistics: {error}",
        "error.invoices": "Unable to load invoices: {error}",
        "error.invoice": "Unable to load invoice: {error}",
        # Statuses
        "status.approved": "Approved",
        "status.needs_review": "Needs Review",
        "status.rejected": "Rejected",
        "status.unknown": "Unknown",
        # Dashboard
        "dashboard.overview": "Overview",
        "dashboard.overview_caption": "Processing volume and review status at a glance.",
        "kpi.total": "Total Invoices",
        "kpi.approved": "Approved",
        "kpi.needs_review": "Needs Review",
        "kpi.rejected": "Rejected",
        "kpi.value": "Total Processed Value",
        # Chart
        "chart.title": "Processed Value by Supplier",
        "chart.caption": "Top {n} suppliers by total processed invoice value.",
        "chart.empty": "No invoice values available to chart yet.",
        "chart.x": "Supplier",
        "chart.y": "Processed value (€)",
        "chart.unknown_supplier": "Unknown supplier",
        # Registry
        "registry.title": "Invoice Registry",
        "registry.caption": "All processed invoices and their current review status.",
        "registry.empty": "No invoices have been processed yet. Open Process Invoice to upload your first PDF.",
        "registry.search": "Search by supplier or invoice number",
        "registry.all_statuses": "All statuses",
        "registry.date_range": "Invoice date range",
        "registry.showing": "Showing {shown} of {total} invoices",
        "registry.no_match": "No invoices match your filters.",
        "col.id": "ID",
        "col.supplier": "Supplier",
        "col.vat": "VAT Number",
        "col.number": "Invoice Number",
        "col.date": "Date",
        "col.amount": "Amount",
        "col.currency": "Currency",
        "col.status": "Status",
        # Process invoice
        "process.title": "Process Invoice",
        "process.caption": "Upload a PDF and let the AI extract, validate and register it.",
        "process.uploader": "Invoice PDF",
        "process.button": "Process with AI",
        "process.spinner": "Extracting and validating invoice...",
        "process.success": "Invoice processed successfully and added to the registry.",
        "process.duplicate_default": "Duplicate invoice detected.",
        "process.duplicate_file": "This PDF has already been processed.",
        "process.duplicate_number": (
            "An invoice with this supplier and invoice number already exists."
        ),
        "process.no_readable_text": "No readable text was found in the PDF.",
        "process.invalid_invoice": (
            "The uploaded PDF does not contain a valid invoice "
            "or the required invoice fields could not be extracted."
        ),
        "process.failed": "The invoice could not be processed. HTTP {code}.",
        "process.details": "Technical details",
        "process.empty_body": "The response body was empty.",
        "process.service_error": ("The invoice could not be processed at the moment. " "Please try again later."),
        # Review
        "review.title": "Invoice Review",
        "review.caption": "Verify the AI-extracted data and record your decision.",
        "review.empty": "There are no invoices to review yet. Process an invoice first.",
        "review.select": "Select an invoice",
        "review.no_number": "no number",
        "review.current_status": "Current status",
        "review.invoice_no": "Invoice #{id}",
        "review.view_pdf": "View original PDF",
        "review.pdf_unavailable": "Original PDF not available for this invoice.",
        "card.supplier": "Supplier details",
        "card.financial": "Financial summary",
        "field.supplier": "Supplier",
        "field.invoice_number": "Invoice Number",
        "field.vat_number": "VAT Number",
        "field.invoice_date": "Invoice Date",
        "field.subtotal": "Subtotal",
        "field.vat": "VAT",
        "field.total": "Total",
        "validation.title": "Validation",
        "validation.flagged": "The validation checks flagged the following:",
        "validation.ok": "No validation issues reported.",
        "decision.title": "Review decision",
        "decision.caption": "Your decision is saved immediately and reflected in the registry.",
        "decision.approve": "Approve",
        "decision.needs_review": "Needs Review",
        "decision.reject": "Reject",
        "decision.approved_msg": "Invoice approved.",
        "decision.review_msg": "Invoice marked for review.",
        "decision.rejected_msg": "Invoice rejected.",
    },
    "PT": {
        # Navigation / sidebar / header
        "nav.Dashboard": "Painel",
        "nav.Process Invoice": "Processar fatura",
        "nav.Invoice Review": "Revisão de faturas",
        "sidebar.tagline": "Processamento inteligente de faturas",
        "sidebar.api_online": "API Online",
        "sidebar.api_offline": "API Offline",
        "header.title": "Operações de Faturas",
        "header.subtitle": "Reveja, valide e aprove faturas de fornecedores extraídas por IA.",
        # API / errors
        "api.invalid_json": "A API devolveu uma resposta JSON inválida.",
        "api.unexpected_format": "Formato de resposta inesperado.",
        "api.connect_error": "Não foi possível ligar à API: {error}",
        "api.status_failed": "Falha ao atualizar o estado (HTTP {code}).",
        "api.unreachable": "O serviço está atualmente indisponível. " "Tente novamente mais tarde.",
        "api.service_unavailable": ("O serviço está temporariamente indisponível. " "Tente novamente mais tarde."),
        "api.connection_unavailable": ("Não foi possível contactar o serviço. " "Tente novamente mais tarde."),
        "api.request_failed": ("Não foi possível concluir o pedido. " "Tente novamente."),
        "error.stats": "Não foi possível carregar as estatísticas do painel: {error}",
        "error.invoices": "Não foi possível carregar as faturas: {error}",
        "error.invoice": "Não foi possível carregar a fatura: {error}",
        # Statuses
        "status.approved": "Aprovada",
        "status.needs_review": "Requer revisão",
        "status.rejected": "Rejeitada",
        "status.unknown": "Desconhecido",
        # Dashboard
        "dashboard.overview": "Visão geral",
        "dashboard.overview_caption": "Volume de processamento e estado das revisões num relance.",
        "kpi.total": "Total de faturas",
        "kpi.approved": "Aprovadas",
        "kpi.needs_review": "Requerem revisão",
        "kpi.rejected": "Rejeitadas",
        "kpi.value": "Valor total processado",
        # Chart
        "chart.title": "Valor processado por fornecedor",
        "chart.caption": "Top {n} fornecedores por valor total de faturas processadas.",
        "chart.empty": "Ainda não há valores de faturas para apresentar no gráfico.",
        "chart.x": "Fornecedor",
        "chart.y": "Valor processado (€)",
        "chart.unknown_supplier": "Fornecedor desconhecido",
        # Registry
        "registry.title": "Registo de faturas",
        "registry.caption": "Todas as faturas processadas e o respetivo estado de revisão.",
        "registry.empty": "Ainda não foram processadas faturas. Abra Processar fatura para carregar o primeiro PDF.",
        "registry.search": "Pesquisar por fornecedor ou número da fatura",
        "registry.all_statuses": "Todos os estados",
        "registry.date_range": "Intervalo de datas da fatura",
        "registry.showing": "A mostrar {shown} de {total} faturas",
        "registry.no_match": "Nenhuma fatura corresponde aos filtros.",
        "col.id": "ID",
        "col.supplier": "Fornecedor",
        "col.vat": "NIF",
        "col.number": "Nº da fatura",
        "col.date": "Data",
        "col.amount": "Valor",
        "col.currency": "Moeda",
        "col.status": "Estado",
        # Process invoice
        "process.title": "Processar fatura",
        "process.caption": "Carregue um PDF e deixe a IA extrair, validar e registar a fatura.",
        "process.uploader": "PDF da fatura",
        "process.button": "Processar com IA",
        "process.spinner": "A extrair e a validar a fatura...",
        "process.success": "Fatura processada com sucesso e adicionada ao registo.",
        "process.duplicate_default": "Fatura duplicada detetada.",
        "process.duplicate_file": "Este PDF já foi processado.",
        "process.duplicate_number": (
            "Já existe uma fatura deste fornecedor com o mesmo número."
        ),
        "process.no_readable_text": "Não foi encontrado texto legível no PDF.",
        "process.invalid_invoice": (
            "O PDF carregado não contém uma fatura válida "
            "ou não foi possível extrair os campos obrigatórios."
        ),
        "process.failed": "Não foi possível processar a fatura. HTTP {code}.",
        "process.details": "Detalhes técnicos",
        "process.empty_body": "O corpo da resposta estava vazio.",
        "process.service_error": ("Não foi possível processar a fatura neste momento. " "Tente novamente mais tarde."),
        # Review
        "review.title": "Revisão de faturas",
        "review.caption": "Verifique os dados extraídos pela IA e registe a sua decisão.",
        "review.empty": "Ainda não há faturas para rever. Processe primeiro uma fatura.",
        "review.select": "Selecione uma fatura",
        "review.no_number": "sem número",
        "review.current_status": "Estado atual",
        "review.invoice_no": "Fatura n.º {id}",
        "review.view_pdf": "Ver PDF original",
        "review.pdf_unavailable": "O PDF original não está disponível para esta fatura.",
        "card.supplier": "Dados do fornecedor",
        "card.financial": "Resumo financeiro",
        "field.supplier": "Fornecedor",
        "field.invoice_number": "Nº da fatura",
        "field.vat_number": "NIF",
        "field.invoice_date": "Data da fatura",
        "field.subtotal": "Subtotal",
        "field.vat": "IVA",
        "field.total": "Total",
        "validation.title": "Validação",
        "validation.flagged": "As verificações de validação assinalaram o seguinte:",
        "validation.ok": "Sem problemas de validação reportados.",
        "decision.title": "Decisão de revisão",
        "decision.caption": "A sua decisão é guardada de imediato e refletida no registo.",
        "decision.approve": "Aprovar",
        "decision.needs_review": "Requer revisão",
        "decision.reject": "Rejeitar",
        "decision.approved_msg": "Fatura aprovada.",
        "decision.review_msg": "Fatura marcada para revisão.",
        "decision.rejected_msg": "Fatura rejeitada.",
    },
}


def current_lang() -> str:
    lang = st.session_state.get("lang", DEFAULT_LANG)
    return lang if lang in TRANSLATIONS else DEFAULT_LANG


def t(key: str, **kwargs: Any) -> str:
    """Translate `key` into the active language (falls back to English)."""
    text = TRANSLATIONS[current_lang()].get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
# Colours, borders, radius and widget backgrounds come from the native theme
# in .streamlit/config.toml. This block only keeps layout, sidebar, spacing,
# the review-decision buttons and branding.

CSS = """
<style>
[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppDeployButton"], .stDeployButton, #MainMenu, footer { display: none !important; }
.block-container { padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1200px; }

/* Typography & vertical rhythm */
h1 { font-size: 1.9rem !important; font-weight: 650 !important; letter-spacing: -0.02em; padding-bottom: 0.1rem !important; }
h3 { font-size: 1.05rem !important; font-weight: 600 !important; margin-top: 0.6rem; padding-bottom: 0.2rem !important; }
h4 { font-size: 1.05rem !important; font-weight: 600 !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #94A3B8 !important; }
[data-testid="stCaptionContainer"] { margin-bottom: 0.5rem; }
hr { margin: 1rem 0 !important; }

/* Language switch (top-right of the header) */
.st-key-lang { margin-top: 1.1rem; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #0A1222; border-right: 1px solid #1B2740; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { gap: 0.3rem; align-items: stretch !important; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div { width: 100%; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid="stMarkdownContainer"]) { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: 0.75rem 1rem; border-radius: 10px; width: 100%; cursor: pointer; border: 1px solid transparent; }
[data-testid="stSidebar"] [data-testid="stRadio"] label p { font-size: 1.05rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background-color: #111B2E; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background-color: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.35); }

/* Metric cards */
[data-testid="stMetric"] { background-color: #111B2E; border: 1px solid #1F2D47; border-radius: 12px; padding: 1rem 1.1rem; }
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 0.8rem; }
[data-testid="stMetricValue"] { color: #F8FAFC; font-size: 1.7rem; font-weight: 600; }

/* File uploader (layout / dimensions) */
[data-testid="stFileUploaderDropzone"] { display: flex; align-items: center; justify-content: center; gap: 1.2rem; background-color: #0D1626; border: 1.5px dashed #2B3C5E; padding: 2.8rem 1.5rem; min-height: 150px; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: #3B82F6; }
[data-testid="stFileUploaderDropzoneInstructions"] { flex: 0 1 auto; }

/* Buttons: full width + size */
.stElementContainer:has(.stButton), .element-container:has(.stButton), [data-testid="stElementContainer"]:has([data-testid="stButton"]) { width: 100% !important; }
.stButton, [data-testid="stButton"] { width: 100% !important; }
.stButton > button { width: 100%; min-height: 2.6rem; font-weight: 500; transition: all 0.15s ease; }

/* Review decision buttons */
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
    meta = STATUS_META.get(status)
    if meta:
        return {**meta, "label": t(f"status.{status}")}
    return {
        "label": str(status or t("status.unknown")).replace("_", " ").title(),
        "color": "gray",
        "dot": "⚪",
    }


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


def api_get(
    path: str,
    timeout: int = 10
) -> Tuple[Optional[Any], Optional[str]]:

    try:
        response = requests.get(
            f"{API_BASE_URL}{path}",
            timeout=timeout
        )

    except requests.RequestException:
        return None, t(
            "api.connection_unavailable"
        )

    if response.status_code >= 500:
        return None, t(
            "api.service_unavailable"
        )

    if response.status_code >= 400:
        return None, t(
            "api.request_failed"
        )

    try:
        return response.json(), None

    except ValueError:
        return None, t(
            "api.invalid_json"
        )


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
        return None, t("api.unexpected_format")
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
        detail = body.get("detail") if isinstance(body, dict) else None

        reason = (
            detail.get("reason")
            if isinstance(detail, dict)
            else None
        )

        if reason == "file_hash":
            message = t("process.duplicate_file")
        elif reason == "invoice_number":
            message = t("process.duplicate_number")
        else:
            message = t("process.duplicate_default")

        return "duplicate", message

    # PDF exists but is not a valid invoice
    if response.status_code == 422:
        body = safe_json(response)
        detail = body.get("detail") if isinstance(body, dict) else None

        if detail == "No readable text was found in the PDF.":
            message = t("process.no_readable_text")
        else:
            message = t("process.invalid_invoice")

        return "invalid_invoice", message

    # Other errors
    body = safe_json(response)

    return "error", (
        response.status_code,
        body if body is not None else response.text
    )


def update_invoice_status(
    invoice_id: Any,
    new_status: str
) -> Tuple[bool, str]:

    try:
        response = requests.patch(
            f"{API_BASE_URL}/invoices/{invoice_id}/status",
            json={
                "status": new_status
            },
            timeout=10,
        )

    except requests.RequestException:
        return (
            False,
            t("api.connection_unavailable")
        )

    if response.status_code == 200:
        return True, ""

    if response.status_code >= 500:
        return (
            False,
            t("api.service_unavailable")
        )

    return (
        False,
        t("api.request_failed")
    )


# ---------------------------------------------------------------------------
# Layout: header (with language switch) + sidebar
# ---------------------------------------------------------------------------


def render_language_switch() -> None:
    """EN / PT switch. The value lives in st.session_state["lang"] and is
    mirrored in the URL (?lang=PT), so it survives a page refresh."""
    st.segmented_control(
        "Language",
        list(LANGUAGES),
        default=DEFAULT_LANG,
        required=True,
        key="lang",
        bind="query-params",
        label_visibility="collapsed",
        width="stretch",
    )


def render_header() -> None:
    title_col, lang_col = st.columns([8, 1.3])
    # The switch is created first so every t() call below already sees the
    # language chosen in this run.
    with lang_col:
        render_language_switch()
    with title_col:
        st.title(t("header.title"))
        st.caption(t("header.subtitle"))


def render_sidebar(api_online: bool) -> str:
    with st.sidebar:
        st.markdown("### :blue[◆] InvoiceFlow AI")
        st.caption(t("sidebar.tagline"))
        page = st.radio(
            "Navigation",
            NAV_PAGES,
            key="page",
            label_visibility="collapsed",
            format_func=lambda page_id: t(f"nav.{page_id}"),
        )
        st.divider()
        if api_online:
            st.markdown(f':green[●] **{t("sidebar.api_online")}**')
        else:
            st.markdown(f':red[●] **{t("sidebar.api_offline")}**')
        return page


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


def render_metrics(stats: Dict[str, Any]) -> None:
    columns = st.columns(5, gap="medium")
    total_value = to_float(stats.get("total_amount")) or 0.0
    dot = {key: meta["dot"] for key, meta in STATUS_META.items()}
    cards = [
        (t("kpi.total"), f'{int(to_float(stats.get("total_invoices")) or 0)}'),
        (f'{dot["approved"]} {t("kpi.approved")}', f'{int(to_float(stats.get("approved")) or 0)}'),
        (f'{dot["needs_review"]} {t("kpi.needs_review")}', f'{int(to_float(stats.get("needs_review")) or 0)}'),
        (f'{dot["rejected"]} {t("kpi.rejected")}', f'{int(to_float(stats.get("rejected")) or 0)}'),
        (t("kpi.value"), f"{total_value:,.2f} €"),
    ]
    for column, (label, value) in zip(columns, cards):
        column.metric(label, value)


SUPPLIER_SUFFIX_RE = re.compile(r"[,\s]+LDA\.?\s*$", re.IGNORECASE)


def chart_label(name: str) -> str:
    """Visual-only label: strips a trailing ", LDA." / " LDA" style suffix."""
    return SUPPLIER_SUFFIX_RE.sub("", name).strip() or name


def supplier_totals(
    invoices: List[Dict[str, Any]], limit: int = SUPPLIER_CHART_LIMIT
) -> pd.DataFrame:
    """Sum invoice totals per supplier and keep the top `limit` suppliers.

    Ignores missing/invalid totals. Returns a DataFrame with columns
    "Supplier" (display label) and "Total", sorted by total (highest
    first). Empty if there is nothing valid to chart. Source data is
    never modified.
    """
    totals: Dict[str, float] = {}
    for invoice in invoices:
        amount = to_float(invoice.get("total"))
        if amount is None or amount != amount:  # None or NaN
            continue
        supplier = (
            str(invoice.get("supplier_name") or "").strip()
            or t("chart.unknown_supplier")
        )
        totals[supplier] = totals.get(supplier, 0.0) + amount

    frame = pd.DataFrame(
        {"Supplier": list(totals.keys()), "Total": list(totals.values())}
    )
    if frame.empty:
        return frame

    frame = (
        frame.sort_values("Total", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )

    # Clean labels for display only; if two different suppliers collapse to
    # the same label, keep their full names so the bars are not merged.
    labels = frame["Supplier"].map(chart_label)
    frame["Supplier"] = frame["Supplier"].where(
        labels.duplicated(keep=False), labels
    )
    return frame


def render_supplier_chart(invoices: List[Dict[str, Any]]) -> None:
    section_header(
        t("chart.title"),
        t("chart.caption", n=SUPPLIER_CHART_LIMIT),
    )

    data = supplier_totals(invoices)
    if data.empty:
        st.info(t("chart.empty"))
        return

    with st.container(border=True):
        st.bar_chart(
            data,
            x="Supplier",
            y="Total",
            x_label=t("chart.x"),
            y_label=t("chart.y"),
            horizontal=True,
            sort="-Total",
            height=min(420, max(200, 48 * len(data) + 60)),
        )
def parse_invoice_date(value: Any):
    """Convert an invoice date into a Python date object."""

    if not value:
        return None

    try:
        return pd.to_datetime(
            value,
            errors="raise"
        ).date()

    except (ValueError, TypeError, OverflowError):
        return None

def filter_invoices(
    invoices: List[Dict[str, Any]],
    query: str,
    status_key: str,
    start_date: Any = None,
    end_date: Any = None
) -> List[Dict[str, Any]]:
    """
    Filter invoices by search query, status and invoice date range.

    `status_key` is "all" or one of the internal status keys.
    """

    query = query.strip().lower()
    result = []

    for invoice in invoices:

        # Status filter
        if (
            status_key != "all"
            and invoice.get("status") != status_key
        ):
            continue

        # Search filter
        haystack = (
            f'{invoice.get("supplier_name", "")} '
            f'{invoice.get("invoice_number", "")}'
        ).lower()

        if query and query not in haystack:
            continue

        # Invoice date filter
        if start_date is not None and end_date is not None:

            invoice_date = parse_invoice_date(
                invoice.get("invoice_date")
            )

            if invoice_date is None:
                continue

            if not (
                start_date
                <= invoice_date
                <= end_date
            ):
                continue

        result.append(invoice)

    return result


def render_invoice_table(
    invoices: List[Dict[str, Any]]
) -> None:

    section_header(
        t("registry.title"),
        t("registry.caption")
    )

    if not invoices:
        st.info(t("registry.empty"))
        return

    with st.container(border=True):

        search_col, status_col, date_col = st.columns(
            [2.4, 1.2, 1.7]
        )

        # Search
        query = search_col.text_input(
            "Search",
            placeholder=t("registry.search"),
            label_visibility="collapsed",
            key="registry_search",
        )

        # Status
        status_key = status_col.selectbox(
            "Status filter",
            ["all"] + list(STATUS_META),
            format_func=lambda key: (
                t("registry.all_statuses")
                if key == "all"
                else t(f"status.{key}")
            ),
            label_visibility="collapsed",
            key="registry_status",
        )


        date_format = (
            "DD/MM/YYYY"
            if current_lang() == "PT"
            else "YYYY-MM-DD"
)
        
        # Invoice date range
        date_range = date_col.date_input(
            t("registry.date_range"),
            value=(),
            key="registry_date_range",
            format=date_format,
            label_visibility="collapsed",
)

        start_date = None
        end_date = None

        if (
            isinstance(date_range, (tuple, list))
            and len(date_range) == 2
        ):
            start_date, end_date = date_range

        # Apply all filters together
        filtered = filter_invoices(
            invoices=invoices,
            query=query,
            status_key=status_key,
            start_date=start_date,
            end_date=end_date,
        )

        st.caption(
            t(
                "registry.showing",
                shown=len(filtered),
                total=len(invoices)
            )
        )

        if not filtered:
            st.info(t("registry.no_match"))
            return

        col = {
            name: t(f"col.{name}")
            for name in (
                "id",
                "supplier",
                "vat",
                "number",
                "date",
                "amount",
                "currency",
                "status",
            )
        }

        rows = []

        for invoice in filtered:

            meta = status_meta(
                invoice.get("status")
            )

            rows.append(
                {
                    col["id"]:
                        invoice.get("id"),

                    col["supplier"]:
                        invoice.get("supplier_name"),

                    col["vat"]:
                        invoice.get(
                            "supplier_vat_number"
                        ),

                    col["number"]:
                        invoice.get("invoice_number"),

                    col["date"]:
                        invoice.get("invoice_date"),

                    col["amount"]:
                        to_float(
                            invoice.get("total")
                        ),

                    col["currency"]:
                        invoice.get("currency"),

                    col["status"]:
                        (
                            f'{meta["dot"]} '
                            f'{meta["label"]}'
                        ),
                }
            )

        st.dataframe(
            rows,
            hide_index=True,
            column_config={
                col["id"]:
                    st.column_config.NumberColumn(
                        col["id"],
                        format="%d",
                        width="small"
                    ),

                col["amount"]:
                    st.column_config.NumberColumn(
                        col["amount"],
                        format="%.2f"
                    ),
            },
        )


def render_dashboard() -> None:
    section_header(t("dashboard.overview"), t("dashboard.overview_caption"))
    stats, error = fetch_stats()
    if error:
        st.error(t("error.stats", error=error))
    else:
        render_metrics(stats or {})

    invoices, error = fetch_invoices()
    if error:
        st.error(t("error.invoices", error=error))
    else:
        render_supplier_chart(invoices)
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
            t("process.success")
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

        st.warning(payload)

    elif outcome == "invalid_invoice":

        st.warning(payload)

    elif outcome == "network":

        st.error(
            t("api.connect_error", error=payload)
        )

    else:

        st.error(
            t("process.service_error")
        )

def render_upload_section() -> None:

    section_header(
        t("process.title"),
        t("process.caption"),
    )

    with st.container(border=True):

        upload_version = st.session_state.get("upload_version", 0)
        uploaded_file = st.file_uploader(t("process.uploader"), type=["pdf"], key=f"invoice_upload_{upload_version}",)

        if uploaded_file is not None:

            st.caption(
                f"{uploaded_file.name} · "
                f"{uploaded_file.size / 1024:,.1f} KB"
            )

        st.write("")

        clicked = st.button(
            t("process.button"),
            type="primary",
            disabled=uploaded_file is None,
            key="btn_process",
            width="stretch",
        )

    if clicked and uploaded_file is not None:

        with st.spinner(
            t("process.spinner")
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
            f"{t('review.invoice_no', id=invoice.get('id'))} · "
            f"{md_escape(display(invoice.get('supplier_name')))}"
        )
    with right:
        st.caption(t("review.current_status"))
        st.markdown(f"#### :{meta['color']}[● {meta['label']}]")


def render_pdf_action(invoice: Dict[str, Any]) -> None:
    """Link to the original PDF. The API generates the signed URL and
    redirects; the dashboard only points at the endpoint."""
    invoice_id = invoice.get("id")
    file_path = invoice.get("file_path")

    if not file_path:
        st.button(
            t("review.view_pdf"),
            disabled=True,
            key=f"pdf_unavailable_{invoice_id}",
            width="stretch",
        )
        st.caption(t("review.pdf_unavailable"))
        return

    pdf_url = f"{API_BASE_URL}/invoices/{invoice_id}/pdf"

    st.link_button(
        t("review.view_pdf"),
        pdf_url,
        width="stretch",
    )


def render_supplier_card(invoice: Dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown(f"**{t('card.supplier')}**")
        left, right = st.columns(2)
        with left:
            field(t("field.supplier"), invoice.get("supplier_name"))
            field(t("field.invoice_number"), invoice.get("invoice_number"))
        with right:
            field(t("field.vat_number"), invoice.get("supplier_vat_number"))
            field(t("field.invoice_date"), invoice.get("invoice_date"))


def render_financial_card(invoice: Dict[str, Any], currency: Optional[str]) -> None:
    with st.container(border=True):
        st.markdown(f"**{t('card.financial')}**")
        first, second, third = st.columns(3)
        with first:
            field(t("field.subtotal"), format_money(invoice.get("subtotal"), currency))
        with second:
            field(t("field.vat"), format_money(invoice.get("vat_amount"), currency))
        with third:
            field(t("field.total"), format_money(invoice.get("total"), currency), highlight=True)


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
        st.markdown(f"**{t('validation.title')}**")
        if issues:
            items = "\n".join(f"- {md_escape(item)}" for item in issues)
            st.warning(f"{t('validation.flagged')}\n\n{items}")
        else:
            st.success(t("validation.ok"))


def handle_review_decision(
    invoice_id: Any,
    new_status: str,
    level: str,
    message: str
) -> None:

    ok, error = update_invoice_status(
        invoice_id,
        new_status
    )

    if ok:
        set_flash(
            level,
            message
        )

    else:
        set_flash(
            "error",
            error
        )


def render_decision_panel(
    invoice_id: Any,
    current_status: Any
) -> None:

    decisions = [
        (
            t("decision.approve"),
            "approved",
            "btn_approve",
            "success",
            t("decision.approved_msg")
        ),
        (
            t("decision.needs_review"),
            "needs_review",
            "btn_review",
            "warning",
            t("decision.review_msg")
        ),
        (
            t("decision.reject"),
            "rejected",
            "btn_reject",
            "error",
            t("decision.rejected_msg")
        ),
    ]

    with st.container(border=True):

        st.markdown(f"**{t('decision.title')}**")

        st.caption(
            t("decision.caption")
        )

        columns = st.columns(3)

        for column, (
            label,
            status,
            key,
            level,
            message
        ) in zip(columns, decisions):

            with column:

                st.button(
                    label,
                    key=key,
                    disabled=current_status == status,
                    on_click=handle_review_decision,
                    args=(
                        invoice_id,
                        status,
                        level,
                        message
                    ),
                    width="stretch",
                )


def render_review_workspace(invoices: List[Dict[str, Any]]) -> None:
    section_header(
        t("review.title"),
        t("review.caption"),
    )
    valid = [inv for inv in invoices if inv.get("id") is not None]
    if not valid:
        st.info(t("review.empty"))
        return

    labels = {
        inv["id"]: (
            f'#{inv["id"]} · {inv.get("supplier_name") or t("chart.unknown_supplier")}'
            f' · {inv.get("invoice_number") or t("review.no_number")}'
        )
        for inv in valid
    }
    selected_id = st.selectbox(
        t("review.select"),
        options=list(labels),
        format_func=lambda invoice_id: labels[invoice_id],
        key="review_invoice_id",
    )

    invoice, error = fetch_invoice(selected_id)
    if error or invoice is None:
        st.error(t("error.invoice", error=error))
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
        render_pdf_action(invoice)

    render_validation_card(invoice)
    render_decision_panel(selected_id, status)


def render_review_page() -> None:
    invoices, error = fetch_invoices()
    if error:
        section_header(t("review.title"))
        st.error(t("error.invoices", error=error))
        return
    render_review_workspace(invoices)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="InvoiceFlow AI", page_icon=str(FAVICON_PATH), layout="wide")
    inject_css()

    api_online = check_api_health()
    # Header first: it creates the language switch that every t() call needs.
    render_header()
    page = render_sidebar(api_online)
    render_flash()

    if not api_online:
        st.error(t("api.unreachable", url=API_BASE_URL))
        return

    if page == "Dashboard":
        render_dashboard()
    elif page == "Process Invoice":
        render_upload_section()
    else:
        render_review_page()


if __name__ == "__main__":
    main()