from __future__ import annotations

import base64
import html
import io
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

DASHBOARD_DIR = Path(__file__).resolve().parent

FAVICON_PATH = (
    DASHBOARD_DIR
    / "icon"
    / "favicon.png"
)

STYLE_PATH = (
    DASHBOARD_DIR
    / "style.css"
)

# Internal page identifiers (used for routing). Display names live in
# TRANSLATIONS under the "nav.<page>" keys.
NAV_PAGES = ["Dashboard", "Process Invoice", "Invoice Review"]

# Material icon shown next to each navigation entry.
NAV_ICONS = {
    "Dashboard": "dashboard",
    "Process Invoice": "upload_file",
    "Invoice Review": "fact_check",
}

# Internal status keys come from the API and must never be translated.
# Only their display labels (TRANSLATIONS "status.<key>") change per language.
STATUS_META: Dict[str, Dict[str, str]] = {
    "approved": {"color": "green", "dot": "🟢", "tone": "ok"},
    "needs_review": {"color": "orange", "dot": "🟡", "tone": "warn"},
    "rejected": {"color": "red", "dot": "🔴", "tone": "bad"},
}

# Cell styling for the status column of the registry table (badge look).
STATUS_CELL_STYLE: Dict[str, str] = {
    "approved": "color: #34D399; background-color: rgba(52, 211, 153, 0.14); font-weight: 600;",
    "needs_review": "color: #FBBF24; background-color: rgba(251, 191, 36, 0.14); font-weight: 600;",
    "rejected": "color: #F87171; background-color: rgba(248, 113, 113, 0.14); font-weight: 600;",
}

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£"}

SUPPLIER_CHART_LIMIT = 10

# Review queue: how many recent invoices are listed.
QUEUE_LIMIT = 5

# Same height for the chart card and the review-queue card.
CARD_HEIGHT = 440

# Upload limit shown in the uploader. For the uploader itself to enforce it,
# also set `[server] maxUploadSize = 10` in .streamlit/config.toml.
MAX_UPLOAD_MB = 10

# Original PDFs larger than this are not embedded in the page (the "open PDF"
# button is still available).
MAX_PDF_EMBED_BYTES = 6 * 1024 * 1024

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
        "kpi.of_total": "{pct}% of total",
        "kpi.awaiting": "Awaiting decision",
        # Chart
        "chart.title": "Processed Value by Supplier",
        "chart.caption": "Top suppliers by total processed invoice value.",
        "chart.empty": "No invoice values available to chart yet.",
        "chart.x": "Supplier",
        "chart.y": "Processed value (€)",
        "chart.unknown_supplier": "Unknown supplier",
        # Review queue
        "queue.title": "Review Queue",
        "queue.caption": "Invoices that need a human decision.",
        "queue.generic": "Invoice requires manual review.",
        "queue.empty": "No invoices are waiting for review.",
        # Registry
        "registry.title": "Invoice Registry",
        "registry.caption": "All processed invoices and their current review status.",
        "registry.empty": "No invoices have been processed yet. Open Process Invoice to upload your first PDF.",
        "registry.search": "Search by supplier or invoice number",
        "registry.all_statuses": "All statuses",
        "registry.date_range": "Invoice date range",
        "registry.label_search": "Search",
        "registry.label_status": "Status",
        "registry.label_date": "Invoice date",
        "registry.any_date": "Any date",
        "registry.clear": "Clear",
        "registry.showing": "Showing {shown} of {total} invoices",
        "registry.no_match": "No invoices match your filters.",
        "col.id": "ID",
        "col.supplier": "Supplier",
        "col.vat": "VAT Number",
        "col.number": "Invoice Number",
        "col.date": "Invoice Date",
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
        "process.drop_title": "Drop supplier invoice here",
        "process.drop_hint": "PDF document · Maximum {mb} MB",
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
        "pipeline.pdf": "PDF",
        "pipeline.extraction": "AI Extraction",
        "pipeline.validation": "Validation",
        "pipeline.database": "Database",
        "pipeline.automation": "Automation",
        # Review
        "review.title": "Invoice Review",
        "review.caption": "Verify the AI-extracted data and record your decision.",
        "review.empty": "There are no invoices to review yet. Process an invoice first.",
        "review.select": "Select an invoice",
        "review.no_number": "no number",
        "review.current_status": "Current status",
        "review.invoice_no": "Invoice #{id}",
        "review.view_pdf": "Open original PDF",
        "review.pdf_unavailable": "Original PDF not available for this invoice.",
        "review.in_queue": "{n} awaiting review",
        "review.flagged": "Flagged by AI",
        "review.last_update_ai": "Last update · AI classification",
        "pdf.title": "Original PDF",
        "pdf.preview_unavailable": "Preview unavailable. Use the button below to open the PDF.",
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
        "validation.checks_title": "Validation Checks",
        "validation.checks_caption": "Checks applied to the extracted data.",
        "validation.flagged": "The validation checks flagged the following:",
        "validation.ok": "No validation issues reported.",
        "check.totals": "Financial totals",
        "check.structured": "Structured data validation",
        "check.business": "Business rules",
        "check.passed": "Passed",
        "check.warning": "Warning",
        "check.failed": "Failed",
        "decision.title": "Review Decision",
        "decision.caption": "Your decision is saved immediately and reflected in the registry.",
        "decision.approve": "Approve",
        "decision.needs_review": "Needs Review",
        "decision.reject": "Reject",
        "decision.approve_hint": "Approve invoice",
        "decision.review_hint": "Keep in review queue",
        "decision.reject_hint": "Reject invoice",
        "decision.current": "Current",
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
        "kpi.of_total": "{pct}% do total",
        "kpi.awaiting": "A aguardar decisão",
        # Chart
        "chart.title": "Valor processado por fornecedor",
        "chart.caption": "Top fornecedores por valor total de faturas processadas.",
        "chart.empty": "Ainda não há valores de faturas para apresentar no gráfico.",
        "chart.x": "Fornecedor",
        "chart.y": "Valor processado (€)",
        "chart.unknown_supplier": "Fornecedor desconhecido",
        # Review queue
        "queue.title": "Fila de revisão",
        "queue.caption": "Faturas que precisam de decisão humana.",
        "queue.generic": "A fatura requer revisão manual.",
        "queue.empty": "Não há faturas a aguardar revisão.",
        # Registry
        "registry.title": "Registo de faturas",
        "registry.caption": "Todas as faturas processadas e o respetivo estado de revisão.",
        "registry.empty": "Ainda não foram processadas faturas. Abra Processar fatura para carregar o primeiro PDF.",
        "registry.search": "Pesquisar por fornecedor ou número da fatura",
        "registry.all_statuses": "Todos os estados",
        "registry.date_range": "Intervalo de datas da fatura",
        "registry.label_search": "Pesquisar",
        "registry.label_status": "Estado",
        "registry.label_date": "Data da fatura",
        "registry.any_date": "Qualquer data",
        "registry.showing": "A mostrar {shown} de {total} faturas",
        "registry.no_match": "Nenhuma fatura corresponde aos filtros.",
        "col.id": "ID",
        "col.supplier": "Fornecedor",
        "col.vat": "NIF",
        "col.number": "Nº da fatura",
        "col.date": "Data da fatura",
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
        "process.drop_title": "Arraste a fatura do fornecedor para aqui",
        "process.drop_hint": "Documento PDF · Máximo {mb} MB",
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
        "pipeline.pdf": "PDF",
        "pipeline.extraction": "Extração por IA",
        "pipeline.validation": "Validação",
        "pipeline.database": "Base de dados",
        "pipeline.automation": "Automação",
        # Review
        "review.title": "Revisão de faturas",
        "review.caption": "Verifique os dados extraídos pela IA e registe a sua decisão.",
        "review.empty": "Ainda não há faturas para rever. Processe primeiro uma fatura.",
        "review.select": "Selecione uma fatura",
        "review.no_number": "sem número",
        "review.current_status": "Estado atual",
        "review.invoice_no": "Fatura n.º {id}",
        "review.view_pdf": "Abrir PDF original",
        "review.pdf_unavailable": "O PDF original não está disponível para esta fatura.",
        "review.in_queue": "{n} a aguardar revisão",
        "review.flagged": "Sinalizada pela IA",
        "review.last_update_ai": "Última atualização · Classificação da IA",
        "pdf.title": "PDF original",
        "pdf.preview_unavailable": "Pré-visualização indisponível. Use o botão abaixo para abrir o PDF.",
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
        "validation.checks_title": "Verificações de validação",
        "validation.checks_caption": "Verificações aplicadas aos dados extraídos.",
        "validation.flagged": "As verificações de validação assinalaram o seguinte:",
        "validation.ok": "Sem problemas de validação reportados.",
        "check.totals": "Totais financeiros",
        "check.structured": "Validação de dados estruturados",
        "check.business": "Regras de negócio",
        "check.passed": "Validado",
        "check.warning": "Alerta",
        "check.failed": "Falhou",
        "decision.title": "Decisão de revisão",
        "decision.caption": "A sua decisão é guardada de imediato e refletida no registo.",
        "decision.approve": "Aprovar",
        "decision.needs_review": "Requer revisão",
        "decision.reject": "Rejeitar",
        "decision.approve_hint": "Aprovar fatura",
        "decision.review_hint": "Manter na fila de revisão",
        "decision.reject_hint": "Rejeitar fatura",
        "decision.current": "Atual",
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
# Icons (inline SVG, no external assets)
# ---------------------------------------------------------------------------

ICONS: Dict[str, str] = {
    "file": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M14 2v6h6"/>',
    "file_text": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "x": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "warn": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "euro": '<path d="M4 10h12"/><path d="M4 14h9"/><path d="M19 6a7.7 7.7 0 0 0-5.2-2A7.9 7.9 0 0 0 6 12c0 4.4 3.5 8 7.8 8 2 0 3.8-.8 5.2-2"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "workflow": '<rect width="8" height="8" x="3" y="3" rx="2"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/><rect width="8" height="8" x="13" y="13" rx="2"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
}


def icon_svg(name: str, size: int = 16) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------


def css_text(value: str) -> str:
    """
    Make translated text safe inside a CSS
    content: "..." value.
    """

    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
    )


def inject_css() -> None:
    """
    Load the static dashboard stylesheet.

    All normal visual styling lives in dashboard/style.css.
    """

    try:
        css = STYLE_PATH.read_text(
            encoding="utf-8"
        )

    except OSError:
        return

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


def inject_dynamic_css() -> None:
    """
    CSS that depends on the current EN / PT language.

    The structural styling of these buttons lives in
    style.css. Only translated pseudo-element content
    stays here.
    """

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
def load_icon_b64(max_px: int) -> str:
    """
    Brand icon as base64 PNG, downscaled to max_px.

    Returns an empty string if the image is not available.
    """

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
    """
    Dynamic uploader styling.

    Normal uploader styling lives in style.css.
    Only the translated text and favicon watermark
    are generated here.
    """

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
# Small helpers
# ---------------------------------------------------------------------------


def esc(value: Any) -> str:
    """HTML-escape any value coming from the API before it enters markup."""
    return html.escape(str(value), quote=True)


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
        "tone": "neutral",
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


def html_block(markup: str) -> None:
    """Render a single-line HTML snippet (must start with a block tag)."""
    st.markdown(markup, unsafe_allow_html=True)


def card_head_html(title: str, caption: Optional[str] = None, badge: Optional[Any] = None) -> str:
    sub = f'<div class="card-sub">{esc(caption)}</div>' if caption else ""
    count = f'<span class="count-badge">{esc(badge)}</span>' if badge is not None else ""
    return (
        '<div class="card-head"><div>'
        f'<div class="card-title">{esc(title)}</div>{sub}'
        f'</div>{count}</div>'
    )


def kv_row_html(label: str, value: str, total: bool = False) -> str:
    cls = "kv kv-total" if total else "kv"
    return f'<div class="{cls}"><span class="kv-k">{esc(label)}</span><span class="kv-v">{esc(value)}</span></div>'


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


@st.cache_data(ttl=600, max_entries=16, show_spinner=False)
def _download_pdf(invoice_id: Any) -> bytes:
    """Read the original PDF through the existing /invoices/{id}/pdf route.

    Raises on any problem, so failures are never cached.
    """
    response = requests.get(f"{API_BASE_URL}/invoices/{invoice_id}/pdf", timeout=15)
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF"):
        raise ValueError("The response is not a PDF file.")
    return content


def fetch_invoice_pdf(invoice_id: Any) -> Optional[bytes]:
    """PDF bytes for the inline preview, or None if it is not available."""
    try:
        content = _download_pdf(invoice_id)
    except (requests.RequestException, ValueError):
        return None
    return content if len(content) <= MAX_PDF_EMBED_BYTES else None


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
    with st.container(key="app_header"):
        title_col, lang_col = st.columns([8, 1.3])
        # The switch is created first so every t() call below already sees the
        # language chosen in this run.
        with lang_col:
            render_language_switch()
        with title_col:
            st.title(t("header.title"))
            st.caption(t("header.subtitle"))


def brand_html() -> str:
    logo = load_icon_b64(96)
    img = f'<img src="data:image/png;base64,{logo}" alt="">' if logo else ""
    return (
        f'<div class="brand">{img}<div>'
        '<div class="brand-name">InvoiceFlow <span>AI</span></div>'
        f'<div class="brand-sub">{esc(t("sidebar.tagline"))}</div>'
        '</div></div>'
    )


def render_sidebar(api_online: bool) -> str:
    with st.sidebar:
        html_block(brand_html())
        page = st.radio(
            "Navigation",
            NAV_PAGES,
            key="page",
            label_visibility="collapsed",
            format_func=lambda page_id: f":material/{NAV_ICONS[page_id]}: {t(f'nav.{page_id}')}",
        )
        with st.container(key="sidebar_status"):
            if api_online:
                html_block(
                    '<div class="api-card"><span class="api-dot"></span>'
                    f'<span>{esc(t("sidebar.api_online"))}</span></div>'
                )
            else:
                html_block(
                    '<div class="api-card api-card-off"><span class="api-dot"></span>'
                    f'<span>{esc(t("sidebar.api_offline"))}</span></div>'
                )
        return page


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------


def kpi_card_html(
    tone: str,
    icon: str,
    label: str,
    value: str,
    foot: str = ""
) -> str:
    return (
        f'<div class="kpi kpi-{tone}">'
        f'<div class="kpi-top"><span class="kpi-icon">{icon_svg(icon, 16)}</span>'
        f'<span class="kpi-label">{esc(label)}</span></div>'
        f'<div class="kpi-value">{esc(value)}</div>{foot}</div>'
    )


def kpi_foot_html(percent: int, note: str) -> str:
    percent = max(0, min(100, percent))
    return (
        '<div class="kpi-foot"><div class="kpi-bar">'
        f'<span style="width:{percent}%"></span></div>'
        f'<span class="kpi-note">{esc(note)}</span></div>'
    )


def render_metrics(stats: Dict[str, Any]) -> None:

    total_value = to_float(stats.get("total_amount")) or 0.0
    total = int(to_float(stats.get("total_invoices")) or 0)
    approved = int(to_float(stats.get("approved")) or 0)
    needs_review = int(to_float(stats.get("needs_review")) or 0)
    rejected = int(to_float(stats.get("rejected")) or 0)

    def share(count: int) -> int:
        return round(100 * count / total) if total else 0

    cards = [
        kpi_card_html(
            "total",
            "file_text",
            t("kpi.total"),
            str(total),
        ),
        kpi_card_html(
            "ok",
            "check",
            t("kpi.approved"),
            str(approved),
            kpi_foot_html(
                share(approved),
                t(
                    "kpi.of_total",
                    pct=share(approved),
                ),
            ),
        ),
        kpi_card_html(
            "warn",
            "alert",
            t("kpi.needs_review"),
            str(needs_review),
            kpi_foot_html(
                share(needs_review),
                t("kpi.awaiting"),
            ),
        ),
        kpi_card_html(
            "bad",
            "x",
            t("kpi.rejected"),
            str(rejected),
            kpi_foot_html(
                share(rejected),
                t(
                    "kpi.of_total",
                    pct=share(rejected),
                ),
            ),
        ),
        kpi_card_html(
            "money",
            "euro",
            t("kpi.value"),
            f"{total_value:,.2f} €",
        ),
    ]

    with st.container(key="kpi_row"):
        columns = st.columns(5, gap="small")

        for column, card in zip(columns, cards):
            with column:
                html_block(card)


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


def supplier_chart_spec() -> Dict[str, Any]:
    """Vega-Lite spec: horizontal bars, full supplier names, value labels.

    The first (largest) bar is highlighted. Everything is styled for the dark
    card, so the chart uses no extra library (Streamlit ships Vega-Lite).
    """
    y_axis = {
        "field": "Supplier",
        "type": "nominal",
        "sort": "-x",
        "axis": {
            "title": None,
            "labelLimit": 280,
            "labelColor": "#E2E8F0",
            "labelFontSize": 12,
            "labelPadding": 10,
            "ticks": False,
            "domain": False,
        },
    }
    x_axis = {
        "field": "Total",
        "type": "quantitative",
        "axis": {
            "title": None,
            "labelColor": "#64748B",
            "labelFontSize": 10,
            "labelExpr": "format(datum.value, '~s') + ' €'",
            "gridColor": "#16233B",
            "domain": False,
            "ticks": False,
        },
    }
    return {
        "background": "transparent",
        "padding": {"left": 4, "right": 78, "top": 6, "bottom": 4},
        "autosize": {"type": "fit", "contains": "padding"},
        "config": {"view": {"stroke": None}},
        "height": {"step": 36},
        "layer": [
            {
                "mark": {"type": "bar", "cornerRadiusEnd": 4, "height": {"band": 0.6}},
                "encoding": {
                    "y": y_axis,
                    "x": x_axis,
                    "color": {
                        "condition": {"test": "datum.Rank === 0", "value": "#38BDF8"},
                        "value": "#1D5F8F",
                    },
                    "tooltip": [
                        {"field": "Supplier", "type": "nominal"},
                        {"field": "Label", "type": "nominal", "title": "Total"},
                    ],
                },
            },
            {
                "mark": {"type": "text", "align": "left", "dx": 7, "fontSize": 11, "color": "#CBD5E1"},
                "encoding": {
                    "y": {"field": "Supplier", "type": "nominal", "sort": "-x"},
                    "x": {"field": "Total", "type": "quantitative"},
                    "text": {"field": "Label", "type": "nominal"},
                },
            },
        ],
    }


def render_supplier_chart(invoices: List[Dict[str, Any]], height: int = CARD_HEIGHT) -> None:
    with st.container(border=True, height=height, key="card_chart"):
        html_block(
            card_head_html(
                t("chart.title"),
                t("chart.caption", n=SUPPLIER_CHART_LIMIT),
            )
        )

        data = supplier_totals(invoices)
        if data.empty:
            st.info(t("chart.empty"))
            return

        data["Label"] = data["Total"].map(lambda value: format_money(value, "EUR"))
        data["Rank"] = range(len(data))

        st.vega_lite_chart(
            data,
            supplier_chart_spec(),
            width="stretch",
            theme=None,
        )


def queue_reason(invoice: Dict[str, Any]) -> str:
    """Why an invoice is in the queue: a real validation message if the API
    sent one, otherwise a generic line (nothing is invented)."""
    for key in VALIDATION_KEYS:
        value = invoice.get(key)
        if isinstance(value, (list, tuple)) and value:
            value = value[0]
        elif isinstance(value, dict) and value:
            value = next(iter(value.values()))
        if isinstance(value, str) and value.strip():
            text = value.strip()
            return text if len(text) <= 90 else text[:87] + "..."
    return t("queue.generic")


def recent_first(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Newest first when ids are numeric; otherwise keep the API order."""
    try:
        return sorted(invoices, key=lambda inv: int(inv["id"]), reverse=True)
    except (KeyError, TypeError, ValueError):
        return list(invoices)


def review_queue_html(items: List[Dict[str, Any]]) -> str:
    rows = []
    for invoice in items:
        supplier = invoice.get("supplier_name") or t("chart.unknown_supplier")
        number = invoice.get("invoice_number") or t("review.no_number")
        rows.append(
            '<div class="q-row"><span class="q-dot"></span><div class="q-main">'
            f'<div class="q-name">{esc(supplier)}</div>'
            f'<div class="q-meta">{esc(number)} · {esc(queue_reason(invoice))}</div></div>'
            f'<div class="q-amount">{esc(format_money(invoice.get("total"), invoice.get("currency")))}</div></div>'
        )
    return '<div class="q-list">' + "".join(rows) + "</div>"


def render_review_queue(invoices: List[Dict[str, Any]], height: int = CARD_HEIGHT) -> None:
    pending = [inv for inv in invoices if inv.get("status") == "needs_review"]

    with st.container(border=True, height=height, key="card_queue"):
        html_block(
            card_head_html(
                t("queue.title"),
                t("queue.caption"),
                badge=len(pending),
            )
        )
        if not pending:
            html_block(f'<div class="q-empty">{esc(t("queue.empty"))}</div>')
            return
        html_block(review_queue_html(recent_first(pending)[:QUEUE_LIMIT]))


def parse_invoice_date(value: Any):
    """Convert an invoice date into a Python date object (None if invalid)."""

    if not value:
        return None

    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (ValueError, TypeError, OverflowError):
        return None

    return None if pd.isna(parsed) else parsed.date()


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

def reset_registry_filters() -> None:
    st.session_state["registry_search"] = ""
    st.session_state["registry_status"] = "all"
    st.session_state["registry_date_range"] = ()

def render_invoice_table(
    invoices: List[Dict[str, Any]]
) -> None:

    if not invoices:
        section_header(
            t("registry.title"),
            t("registry.caption")
        )
        st.info(t("registry.empty"))
        return

    with st.container(border=True, key="registry_panel"):

        html_block(
            card_head_html(
                t("registry.title"),
                t("registry.caption"),
            )
        )

        search_col, status_col, date_col, clear_col = st.columns(
            [2.4, 1.0, 1.25, 0.42],
            gap="small",
        )

        # Search
        with search_col:
            html_block(
                f'<div class="flabel">{esc(t("registry.label_search"))}</div>'
            )

            query = st.text_input(
                "Search",
                placeholder=t("registry.search"),
                label_visibility="collapsed",
                key="registry_search",
            )

        # Status
        with status_col:
            html_block(
                f'<div class="flabel">{esc(t("registry.label_status"))}</div>'
            )

            status_key = st.selectbox(
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

        # -------------------------------------------------
        # Invoice date
        # -------------------------------------------------

        with date_col:

            html_block(
                f'<div class="flabel">'
                f'{esc(t("registry.label_date"))}'
                f'</div>'
            )

            current_range = st.session_state.get(
                "registry_date_range",
                (),
            )

            if (
                isinstance(current_range, (tuple, list))
                and len(current_range) == 2
            ):
                date_label = (
                    f"{current_range[0]} → "
                    f"{current_range[1]}"
                )
            else:
                date_label = t(
                    "registry.any_date"
                )

            with st.popover(
                date_label,
                width="stretch",
            ):
                st.date_input(
                    t("registry.date_range"),
                    value=current_range,
                    key="registry_date_range",
                    format=date_format,
                    label_visibility="collapsed",
                )


        # -------------------------------------------------
        # Clear filters
        # -------------------------------------------------

        date_range = st.session_state.get(
            "registry_date_range",
            (),
        )

        has_filters = bool(
            query.strip()
            or status_key != "all"
            or (
                isinstance(date_range, (tuple, list))
                and len(date_range) > 0
            )
        )

        with clear_col:

            html_block(
                '<div class="flabel">&nbsp;</div>'
            )

            st.button(
                f'✕ {t("registry.clear")}',
                key="registry_clear",
                disabled=not has_filters,
                on_click=reset_registry_filters,
                width="stretch",
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

        head = "".join(
            [
                f"<th>{esc(col['id'])}</th>",
                f"<th>{esc(col['supplier'])}</th>",
                f"<th>{esc(col['vat'])}</th>",
                f"<th>{esc(col['number'])}</th>",
                f"<th>{esc(col['date'])}</th>",
                f'<th class="num">{esc(col["amount"])}</th>',
                f"<th>{esc(col['currency'])}</th>",
                f"<th>{esc(col['status'])}</th>",
            ]
        )

        status_classes = {
            "approved": "badge-green",
            "needs_review": "badge-amber",
            "rejected": "badge-red",
        }

        body = ""

        for invoice in filtered:

            status = invoice.get("status")

            meta = status_meta(status)

            badge_class = status_classes.get(
                status,
                "badge-gray",
            )

            amount = to_float(
                invoice.get("total")
            )

            amount_text = (
                f"{amount:,.2f}"
                if amount is not None
                else "—"
            )

            body += (
                "<tr>"
                f'<td class="id">#{esc(display(invoice.get("id")))}</td>'
                f'<td class="sup">{esc(display(invoice.get("supplier_name")))}</td>'
                f'<td class="mono">{esc(display(invoice.get("supplier_vat_number")))}</td>'
                f'<td class="mono bright">{esc(display(invoice.get("invoice_number")))}</td>'
                f'<td class="mono">{esc(display(invoice.get("invoice_date")))}</td>'
                f'<td class="num">{esc(amount_text)}</td>'
                f'<td class="mono">{esc(display(invoice.get("currency")))}</td>'
                '<td>'
                f'<span class="badge {badge_class}">'
                f'{esc(meta["label"])}'
                '</span>'
                '</td>'
                "</tr>"
            )

        html_block(
            '<div class="if-table-wrap">'
            '<table class="if-table">'
            f'<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody>'
            '</table>'
            '</div>'
        )


def render_dashboard() -> None:
    section_header(
        t("dashboard.overview"),
        t("dashboard.overview_caption"),
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
            chart_col, queue_col = st.columns(
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

        # Generic message only: the raw exception text (host, port, library
        # internals) is never shown, like in the other error paths.
        st.error(
            t("api.connection_unavailable")
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

        upload_version = st.session_state.get(
            "upload_version",
            0,
        )

        uploaded_file = st.file_uploader(
            t("process.uploader"),
            type=["pdf"],
            key=f"invoice_upload_{upload_version}",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            st.caption(
                f"{uploaded_file.name} · "
                f"{uploaded_file.size / 1024:,.1f} KB"
            )

        # Full-width Process with AI button
        clicked = st.button(
            t("process.button"),
            type="primary",
            icon=":material/auto_awesome:",
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
            payload,
        )

# ---------------------------------------------------------------------------
# Invoice Review page
# ---------------------------------------------------------------------------


def render_review_header(
    invoice: Dict[str, Any],
    status: Any
) -> None:

    meta = status_meta(status)

    number = display(
        invoice.get("invoice_number")
    )

    supplier = display(
        invoice.get("supplier_name")
    )

    issues = validation_issues(invoice)

    html = (
        '<div class="review-invoice-head">'
        '<div>'
        '<div class="inv-head">'
        f'<span class="inv-no">{esc(number)}</span>'
        f'<span class="badge badge-{meta["tone"]}">'
        f'{esc(meta["label"])}'
        '</span>'
        '</div>'
        f'<div class="inv-sub">{esc(supplier)}</div>'
        '</div>'
        '<div class="review-last-update">'
        f'{esc(t("review.last_update_ai"))}'
        '</div>'
        '</div>'
    )

    if issues:
        html += (
            '<div class="review-flag">'
            f'<span class="review-flag-icon">{icon_svg("warn", 15)}</span>'
            '<span>'
            f'<strong>{esc(t("review.flagged"))}:</strong> '
            f'{esc(issues[0])}'
            '</span>'
            '</div>'
        )

    html_block(html)


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


def render_pdf_panel(invoice: Dict[str, Any]) -> None:
    """Original PDF next to the extracted data (inline preview when the
    browser can show it; the open-in-new-tab button is always there)."""
    file_path = invoice.get("file_path")
    file_name = Path(str(file_path)).name if file_path else t("pdf.title")

    with st.container(border=True, key="card_pdf"):
        html_block(
            '<div class="card-head"><div class="pdf-head">'
            f'<span class="pdf-ico">{icon_svg("file", 16)}</span><div>'
            f'<div class="card-title pdf-file-name">{esc(file_name)}</div>'
            f'<div class="card-sub">{esc(t("pdf.title"))}</div>'
            '</div></div></div>'
        )

        if file_path:
            content = fetch_invoice_pdf(invoice.get("id"))
            if content:
                encoded = base64.b64encode(content).decode("ascii")
                html_block(
                    '<div class="pdf-wrap"><iframe class="pdf-frame" '
                    f'title="{esc(file_name)}" '
                    f'src="data:application/pdf;base64,{encoded}"></iframe></div>'
                )
            else:
                st.info(t("pdf.preview_unavailable"))

        render_pdf_action(invoice)


def render_supplier_card(invoice: Dict[str, Any]) -> None:
    with st.container(border=True, key="card_supplier"):
        html_block(card_head_html(t("card.supplier")))
        html_block(
            '<div class="kvs">'
            + kv_row_html(t("field.supplier"), display(invoice.get("supplier_name")))
            + kv_row_html(t("field.vat_number"), display(invoice.get("supplier_vat_number")))
            + kv_row_html(t("field.invoice_number"), display(invoice.get("invoice_number")))
            + kv_row_html(t("field.invoice_date"), display(invoice.get("invoice_date")))
            + "</div>"
        )


def render_financial_card(invoice: Dict[str, Any], currency: Optional[str]) -> None:
    with st.container(border=True, key="card_financial"):
        html_block(card_head_html(t("card.financial")))
        html_block(
            '<div class="kvs">'
            + kv_row_html(t("field.subtotal"), format_money(invoice.get("subtotal"), currency))
            + kv_row_html(t("field.vat"), format_money(invoice.get("vat_amount"), currency))
            + kv_row_html(t("field.total"), format_money(invoice.get("total"), currency), total=True)
            + "</div>"
        )


def validation_issues(invoice: Dict[str, Any]) -> Optional[List[str]]:
    """Business-validation findings sent by the API (None if the API does not
    send that field at all)."""
    key = next((k for k in VALIDATION_KEYS if k in invoice), None)
    if key is None:
        return None
    issues = invoice[key]
    if isinstance(issues, str):
        issues = [issues] if issues.strip() else []
    elif isinstance(issues, dict):
        issues = [f"{k}: {v}" for k, v in issues.items()]
    elif not isinstance(issues, list):
        issues = [str(issues)] if issues else []
    return [str(item) for item in issues]


def build_validation_checks(invoice: Dict[str, Any]) -> List[Dict[str, str]]:
    """Only checks that can be derived from data the frontend really has."""
    checks: List[Dict[str, str]] = []

    subtotal = to_float(invoice.get("subtotal"))
    vat_amount = to_float(invoice.get("vat_amount"))
    total = to_float(invoice.get("total"))
    if subtotal is not None and vat_amount is not None and total is not None:
        matches = abs((subtotal + vat_amount) - total) <= 0.011
        checks.append(
            {
                "tone": "ok" if matches else "bad",
                "label": t("check.totals"),
                "status": t("check.passed") if matches else t("check.failed"),
            }
        )

    # A stored invoice has already gone through the Pydantic schema.
    checks.append(
        {
            "tone": "ok",
            "label": t("check.structured"),
            "status": t("check.passed"),
        }
    )

    issues = validation_issues(invoice)
    if issues is not None:
        if issues:
            for issue in issues:
                checks.append(
                    {"tone": "warn", "label": issue, "status": t("check.warning")}
                )
        else:
            checks.append(
                {
                    "tone": "ok",
                    "label": t("check.business"),
                    "status": t("check.passed"),
                }
            )
    return checks


def render_validation_card(invoice: Dict[str, Any]) -> None:
    icon_for = {"ok": "check", "warn": "warn", "bad": "x"}
    rows = "".join(
        f'<div class="chk"><span class="chk-ico chk-{check["tone"]}">'
        f'{icon_svg(icon_for[check["tone"]], 14)}</span>'
        f'<span class="chk-label">{esc(check["label"])}</span>'
        f'<span class="chk-status chk-{check["tone"]}">{esc(check["status"])}</span></div>'
        for check in build_validation_checks(invoice)
    )

    with st.container(border=True, key="card_checks"):
        html_block(
            card_head_html(
                t("validation.checks_title"),
                t("validation.checks_caption"),
            )
        )
        html_block(f'<div class="chks">{rows}</div>')


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

    # The human-in-the-loop zone: three large decision cards.
    with st.container(border=True, key="card_decision"):

        html_block(
            card_head_html(
                t("decision.title"),
                t("decision.caption"),
            )
        )

        columns = st.columns(3, gap="small")

        for column, (
            label,
            status,
            key,
            level,
            message,
            icon,
        ) in zip(columns, decisions):

            with column:

                st.button(
                    label,
                    key=key,
                    icon=icon,
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


def select_review_invoice(invoice_id: Any) -> None:
    st.session_state["review_invoice_id"] = invoice_id

def render_review_workspace(
    invoices: List[Dict[str, Any]]
) -> None:

    valid = [
        inv
        for inv in invoices
        if inv.get("id") is not None
    ]

    pending = sum(
        1
        for inv in valid
        if inv.get("status") == "needs_review"
    )

    # -------------------------------------------------
    # Page title
    # -------------------------------------------------

    title_col, queue_col = st.columns(
        [5, 1],
        vertical_alignment="center",
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
        inv["id"]: (
            f'#{inv["id"]} · '
            f'{inv.get("supplier_name") or t("chart.unknown_supplier")}'
            f' · '
            f'{inv.get("invoice_number") or t("review.no_number")}'
        )
        for inv in valid
    }

    # -------------------------------------------------
    # Top invoice card
    # -------------------------------------------------

    with st.container(
        border=True,
        key="card_review_top",
    ):

        select_col, actions_col = st.columns(
            [4.5, 1],
            gap="small",
            vertical_alignment="bottom",
        )

        with select_col:

            selected_id = st.selectbox(
                t("review.select"),
                options=list(labels),
                format_func=lambda invoice_id: labels[invoice_id],
                key="review_invoice_id",
            )

        current_index = next(
            (
                index
                for index, inv in enumerate(valid)
                if inv["id"] == selected_id
            ),
            0,
        )

        previous_invoice = (
            valid[current_index - 1]
            if current_index > 0
            else None
        )

        next_invoice = (
            valid[current_index + 1]
            if current_index < len(valid) - 1
            else None
        )

        with actions_col:

            previous_col, next_col = st.columns(
                2,
                gap="small",
            )

            with previous_col:
                st.button(
                    "‹",
                    key="review_previous",
                    disabled=previous_invoice is None,
                    on_click=select_review_invoice,
                    args=(
                        previous_invoice["id"],
                    ) if previous_invoice else (),
                    width="stretch",
                )

            with next_col:
                st.button(
                    "›",
                    key="review_next",
                    disabled=next_invoice is None,
                    on_click=select_review_invoice,
                    args=(
                        next_invoice["id"],
                    ) if next_invoice else (),
                    width="stretch",
                )

        invoice, error = fetch_invoice(
            selected_id
        )

        if error or invoice is None:
            st.error(
                t(
                    "error.invoice",
                    error=error,
                )
            )
            return

        summary = next(
            (
                inv
                for inv in valid
                if inv["id"] == selected_id
            ),
            {},
        )

        currency = (
            invoice.get("currency")
            or summary.get("currency")
        )

        status = invoice.get("status")

        render_review_header(
            invoice,
            status,
        )

    # -------------------------------------------------
    # Extracted data + original document
    # -------------------------------------------------

    data_col, pdf_col = st.columns(
        [1, 1.1],
        gap="small",
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

    # -------------------------------------------------
    # Human review
    # -------------------------------------------------

    render_decision_panel(
        selected_id,
        status,
    )


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

    st.set_page_config(
        page_title="InvoiceFlow AI",
        page_icon=str(FAVICON_PATH),
        layout="wide",
    )

    # Load the static stylesheet first.
    inject_css()

    # Check backend availability.
    api_online = check_api_health()

    # The header creates the EN / PT selector.
    render_header()

    # Inject the small amount of CSS that depends
    # on the selected language.
    inject_dynamic_css()

    # Sidebar navigation.
    page = render_sidebar(
        api_online
    )

    # Flash feedback from previous actions.
    render_flash()

    if not api_online:
        st.error(
            t(
                "api.unreachable",
                url=API_BASE_URL,
            )
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
