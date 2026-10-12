import json
import logging
import os

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    Groq,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)

from api.models.invoice import InvoiceData


load_dotenv()

logger = logging.getLogger(__name__)


MODEL_NAME = "openai/gpt-oss-20b"

AI_TIMEOUT_SECONDS = 20.0

# 2 retries + initial request = maximum of 3 attempts
AI_MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# AI service exceptions
# ---------------------------------------------------------------------------

class AIServiceError(Exception):
    """Base exception for AI service failures."""


class AIServiceUnavailableError(AIServiceError):
    """Temporary Groq service, network or rate-limit failure."""


class AIConfigurationError(AIServiceError):
    """Invalid or missing AI service configuration."""


class AIResponseError(AIServiceError):
    """Unexpected or unusable response returned by the AI service."""


# ---------------------------------------------------------------------------
# Invoice schema
# ---------------------------------------------------------------------------

INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {
            "type": "string"
        },
        "supplier_vat_number": {
            "type": "string"
        },
        "invoice_number": {
            "type": "string"
        },
        "invoice_date": {
            "type": "string"
        },
        "subtotal": {
            "type": "number"
        },
        "vat_amount": {
            "type": "number"
        },
        "total": {
            "type": "number"
        },
        "currency": {
            "type": "string"
        }
    },
    "required": [
        "supplier_name",
        "supplier_vat_number",
        "invoice_number",
        "invoice_date",
        "subtotal",
        "vat_amount",
        "total",
        "currency"
    ],
    "additionalProperties": False
}


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------

def get_groq_client() -> Groq:
    """
    Create a configured Groq client.

    The client uses:
    - an explicit timeout;
    - controlled automatic retries;
    - the API key stored only in the environment.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        logger.error(
            "Groq configuration error: GROQ_API_KEY is missing."
        )

        raise AIConfigurationError(
            "The AI service is not configured."
        )

    return Groq(
        api_key=api_key,
        timeout=AI_TIMEOUT_SECONDS,
        max_retries=AI_MAX_RETRIES
    )


# ---------------------------------------------------------------------------
# Invoice extraction
# ---------------------------------------------------------------------------

def extract_invoice_data(
    invoice_text: str
) -> InvoiceData:

    if not invoice_text.strip():
        raise ValueError(
            "Invoice text is empty."
        )

    client = get_groq_client()

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured information from invoices. "
                        "Extract information about the SUPPLIER that issued "
                        "the invoice, not the customer receiving it. "
                        "Do not invent information. "
                        "Monetary values must be numbers without currency "
                        "symbols. "
                        "Use ISO date format YYYY-MM-DD. "
                        "Use ISO currency codes such as EUR."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "Extract the invoice information from the following "
                        "text:\n\n"
                        + invoice_text
                    )
                }
            ],

            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "invoice_data",
                    "strict": True,
                    "schema": INVOICE_SCHEMA
                }
            }
        )

    except APITimeoutError as exc:
        logger.warning(
            "Groq invoice extraction timed out after retries."
        )

        raise AIServiceUnavailableError(
            "The AI service timed out."
        ) from exc

    except RateLimitError as exc:
        logger.warning(
            "Groq rate limit reached during invoice extraction."
        )

        raise AIServiceUnavailableError(
            "The AI service is temporarily rate limited."
        ) from exc

    except InternalServerError as exc:
        logger.warning(
            "Groq internal server error during invoice extraction."
        )

        raise AIServiceUnavailableError(
            "The AI service is temporarily unavailable."
        ) from exc

    except APIConnectionError as exc:
        logger.warning(
            "Could not connect to Groq during invoice extraction."
        )

        raise AIServiceUnavailableError(
            "The AI service could not be reached."
        ) from exc

    except AuthenticationError as exc:
        logger.error(
            "Groq authentication failed."
        )

        raise AIConfigurationError(
            "The AI service authentication failed."
        ) from exc

    except PermissionDeniedError as exc:
        logger.error(
            "Groq permission denied."
        )

        raise AIConfigurationError(
            "The AI service configuration is not authorized."
        ) from exc

    except APIStatusError as exc:
        logger.error(
            "Groq returned an unexpected HTTP status: %s",
            exc.status_code
        )

        raise AIServiceError(
            "The AI service returned an unexpected response."
        ) from exc

    # Validate basic Groq response structure
    if not response.choices:
        logger.error(
            "Groq returned no choices for invoice extraction."
        )

        raise AIResponseError(
            "The AI returned an invalid response."
        )

    response_content = response.choices[0].message.content

    if not response_content:
        logger.error(
            "Groq returned empty content for invoice extraction."
        )

        raise AIResponseError(
            "The AI returned an empty response."
        )

    try:
        extracted_data = json.loads(
            response_content
        )

    except json.JSONDecodeError as exc:
        logger.error(
            "Groq returned invalid JSON for invoice extraction."
        )

        raise AIResponseError(
            "The AI returned invalid structured data."
        ) from exc

    # Pydantic ValidationError is intentionally allowed to propagate.
    # main.py already treats it as an invalid / unextractable invoice.
    return InvoiceData.model_validate(
        extracted_data
    )