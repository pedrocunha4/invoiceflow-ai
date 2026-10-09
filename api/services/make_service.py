import os
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from dotenv import load_dotenv


load_dotenv()

MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
MAKE_WEBHOOK_API_KEY = os.getenv("MAKE_WEBHOOK_API_KEY")


def send_make_event(
    event_type: str,
    invoice: Dict[str, Any]
) -> bool:
    """
    Send an invoice event to the Make webhook.

    Returns True if Make accepted the event.
    Returns False if the webhook is unavailable or not configured.
    """

    if not MAKE_WEBHOOK_URL or not MAKE_WEBHOOK_API_KEY:
        return False

    payload = {
        "event": event_type,
        "source": "invoiceflow-ai",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "invoice": invoice
    }

    headers = {
        "Content-Type": "application/json",
        "x-make-apikey": MAKE_WEBHOOK_API_KEY
    }

    try:
        response = requests.post(
            MAKE_WEBHOOK_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        return True

    except requests.RequestException:
        return False