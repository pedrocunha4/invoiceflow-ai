from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from dotenv import load_dotenv

from .i18n import t

load_dotenv()

API_BASE_URL = os.getenv(
    "INVOICEFLOW_API_URL",
    "http://127.0.0.1:8000",
)

API_KEY = os.getenv(
    "INVOICEFLOW_API_KEY",
    "",
)


def api_headers() -> dict[str, str]:
    """Headers used for authenticated API requests."""

    if not API_KEY:
        return {}

    return {
        "X-API-Key": API_KEY,
    }

MAX_PDF_EMBED_BYTES = 6 * 1024 * 1024


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def api_get(
    path: str,
    timeout: int = 10,
) -> Tuple[Optional[Any], Optional[str]]:
    try:
        response = requests.get(
            f"{API_BASE_URL}{path}",
            headers=api_headers(),
            timeout=timeout,
        )

    except requests.RequestException:
        return None, t("api.connection_unavailable")

    if response.status_code >= 500:
        return None, t("api.service_unavailable")

    if response.status_code >= 400:
        return None, t("api.request_failed")

    data = safe_json(response)

    if data is None:
        return None, t("api.invalid_json")

    return data, None


def check_api_health() -> bool:
    try:
        response = requests.get(
            f"{API_BASE_URL}/health",
            headers=api_headers(),
            timeout=3,
        )
        return response.status_code == 200

    except requests.RequestException:
        return False


def fetch_stats() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = api_get("/dashboard/stats")

    if error:
        return None, error

    return (
        data if isinstance(data, dict) else {},
        None,
    )


def fetch_invoices() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    data, error = api_get("/invoices")

    if error:
        return [], error

    invoices = (
        data.get("invoices", [])
        if isinstance(data, dict)
        else []
    )

    return invoices, None


def fetch_invoice(
    invoice_id: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data, error = api_get(
        f"/invoices/{invoice_id}"
    )

    if error:
        return None, error

    if not isinstance(data, dict):
        return None, t("api.unexpected_format")

    return data, None


@st.cache_data(
    ttl=600,
    max_entries=16,
    show_spinner=False,
)
def _download_pdf(invoice_id: Any) -> bytes:
    response = requests.get(
        f"{API_BASE_URL}/invoices/{invoice_id}/pdf",
        headers=api_headers(),
        timeout=15,
    )

    response.raise_for_status()

    content = response.content

    if not content.startswith(b"%PDF"):
        raise ValueError(
            "The response is not a PDF file."
        )

    return content


def fetch_invoice_pdf_url(invoice_id: Any) -> Optional[str]:
    """Return a temporary signed URL for the original invoice PDF."""

    data, error = api_get(
        f"/invoices/{invoice_id}/pdf-url"
    )

    if error or not isinstance(data, dict):
        return None

    url = data.get("url")

    return url if isinstance(url, str) and url else None


def fetch_invoice_pdf(
    invoice_id: Any,
) -> Optional[bytes]:
    try:
        content = _download_pdf(
            invoice_id
        )

    except (
        requests.RequestException,
        ValueError,
    ):
        return None

    if len(content) > MAX_PDF_EMBED_BYTES:
        return None

    return content


def process_invoice(
    uploaded_file: Any,
) -> Tuple[str, Any]:
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/invoices/extract",
            headers=api_headers(),
            files=files,
            timeout=60,
        )

    except requests.RequestException as exc:
        return "network", str(exc)

    if response.status_code == 200:
        return (
            "success",
            safe_json(response),
        )

    if response.status_code == 409:
        body = safe_json(response)

        detail = (
            body.get("detail")
            if isinstance(body, dict)
            else None
        )

        reason = (
            detail.get("reason")
            if isinstance(detail, dict)
            else None
        )

        if reason == "file_hash":
            message = t(
                "process.duplicate_file"
            )

        elif reason == "invoice_number":
            message = t(
                "process.duplicate_number"
            )

        else:
            message = t(
                "process.duplicate_default"
            )

        return "duplicate", message

    if response.status_code == 400:
        body = safe_json(response)

        detail = (
            body.get("detail")
            if isinstance(body, dict)
            else None
        )

        if detail == "The uploaded file is not a valid PDF.":
            message = t(
                "process.invalid_pdf"
            )

        elif detail == "The uploaded file is empty.":
            message = t(
                "process.empty_file"
            )

        else:
            message = t(
                "process.invalid_file"
            )

        return (
            "invalid_invoice",
            message,
        )
    
    if response.status_code == 422:
        body = safe_json(response)

        detail = (
            body.get("detail")
            if isinstance(body, dict)
            else None
        )

        if detail == "No readable text was found in the PDF.":
            message = t(
                "process.no_readable_text"
            )

        elif detail == "The PDF exceeds the maximum number of pages.":
            message = t(
                "process.too_many_pages"
            )

        elif detail == "The PDF contains too much text.":
            message = t(
                "process.too_much_text"
            )

        else:
            message = t(
                "process.invalid_invoice"
            )

        return (
            "invalid_invoice",
            message,
        )

    body = safe_json(response)

    return (
        "error",
        (
            response.status_code,
            body
            if body is not None
            else response.text,
        ),
    )


def update_invoice_status(
    invoice_id: Any,
    new_status: str,
) -> Tuple[bool, str]:
    try:
        response = requests.patch(
            f"{API_BASE_URL}/invoices/{invoice_id}/status",
            headers=api_headers(),
            json={"status": new_status},
            timeout=10,
        )

    except requests.RequestException:
        return (
            False,
            t("api.connection_unavailable"),
        )

    if response.status_code == 200:
        return True, ""

    if response.status_code >= 500:
        return (
            False,
            t("api.service_unavailable"),
        )

    return (
        False,
        t("api.request_failed"),
    )