import io

import pdfplumber

MAX_PDF_PAGES = 2
MAX_EXTRACTED_TEXT_CHARS = 10_000


class PdfLimitError(Exception):
    """Raised when a PDF exceeds the allowed processing limits."""


def extract_text_from_pdf(
    content: bytes,
) -> str:
    extracted_text = []

    with pdfplumber.open(
        io.BytesIO(content)
    ) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise PdfLimitError(
                "The PDF exceeds the maximum number of pages."
            )

        for page in pdf.pages:
            text = page.extract_text()

            if text:
                extracted_text.append(
                    text
                )

    result = "\n".join(
        extracted_text
    )

    if (
        len(result)
        > MAX_EXTRACTED_TEXT_CHARS
    ):
        raise PdfLimitError(
            "The PDF contains too much text."
        )

    return result