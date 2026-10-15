from __future__ import annotations

from typing import Any

from .i18n import t

STATUS_META = {
    "approved": {
        "tone": "ok",
    },
    "needs_review": {
        "tone": "warn",
    },
    "rejected": {
        "tone": "bad",
    },
}


def status_meta(
    status: Any,
) -> dict[str, str]:
    meta = STATUS_META.get(
        status
    )

    if meta:
        return {
            **meta,
            "label": t(
                f"status.{status}"
            ),
        }

    return {
        "label": str(
            status
            or t("status.unknown")
        ).replace(
            "_",
            " ",
        ).title(),
        "tone": "neutral",
    }