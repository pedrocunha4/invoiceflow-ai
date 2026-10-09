import json
import os

from dotenv import load_dotenv
from groq import Groq

from api.models.invoice import InvoiceData


load_dotenv()


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


def extract_invoice_data(invoice_text: str) -> InvoiceData:

    if not invoice_text.strip():
        raise ValueError("Invoice text is empty.")

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY was not found in the environment."
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",

        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured information from invoices. "
                    "Extract information about the SUPPLIER that issued the invoice, "
                    "not the customer receiving it. "
                    "Do not invent information. "
                    "Monetary values must be numbers without currency symbols. "
                    "Use ISO date format YYYY-MM-DD. "
                    "Use ISO currency codes such as EUR."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extract the invoice information from the following text:\n\n"
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

    response_content = response.choices[0].message.content

    if not response_content:
        raise RuntimeError("The AI returned an empty response.")

    extracted_data = json.loads(response_content)

    return InvoiceData.model_validate(extracted_data)