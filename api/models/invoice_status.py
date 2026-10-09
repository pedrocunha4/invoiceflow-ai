from typing import Literal

from pydantic import BaseModel


class InvoiceStatusUpdate(BaseModel):
    status: Literal[
        "approved",
        "needs_review",
        "rejected"
    ]