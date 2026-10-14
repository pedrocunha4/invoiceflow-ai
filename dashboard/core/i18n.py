from __future__ import annotations

from typing import Any

import streamlit as st


LANGUAGES = ("EN", "PT")
DEFAULT_LANG = "EN"

TRANSLATIONS: dict[str, dict[str, str]] = {
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
        "process.service_error": ("The invoice could not be processed at the moment. " "Please try again later."),
        # Review
        "review.title": "Invoice Review",
        "review.caption": "Verify the AI-extracted data and record your decision.",
        "review.empty": "There are no invoices to review yet. Process an invoice first.",
        "review.select": "Select an invoice",
        "review.no_number": "no number",
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
        "validation.checks_title": "Validation Checks",
        "validation.checks_caption": "Checks applied to the extracted data.",
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
        "registry.clear": "Limpar",
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
        "process.service_error": ("Não foi possível processar a fatura neste momento. " "Tente novamente mais tarde."),
        # Review
        "review.title": "Revisão de faturas",
        "review.caption": "Verifique os dados extraídos pela IA e registe a sua decisão.",
        "review.empty": "Ainda não há faturas para rever. Processe primeiro uma fatura.",
        "review.select": "Selecione uma fatura",
        "review.no_number": "sem número",
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
        "validation.checks_title": "Verificações de validação",
        "validation.checks_caption": "Verificações aplicadas aos dados extraídos.",
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
    lang = st.session_state.get(
        "lang",
        DEFAULT_LANG,
    )

    return (
        lang
        if lang in TRANSLATIONS
        else DEFAULT_LANG
    )


def t(
    key: str,
    **kwargs: Any,
) -> str:
    """Translate a key into the active language, falling back to English."""

    text = TRANSLATIONS[
        current_lang()
    ].get(key)

    if text is None:
        text = TRANSLATIONS[
            DEFAULT_LANG
        ].get(
            key,
            key,
        )

    return (
        text.format(**kwargs)
        if kwargs
        else text
    )