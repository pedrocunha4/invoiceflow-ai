import io
import pdfplumber


def extract_text_from_pdf(content: bytes) -> str:
    extracted_text = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            if text:
                extracted_text.append(text)

    return "\n".join(extracted_text)