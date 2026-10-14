from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from core.i18n import t
from core.ui import (
    esc,
    html_block,
    icon_svg,
    to_float,
)

def kpi_card_html(
    tone: str,
    icon: str,
    label: str,
    value: str,
    foot: str = "",
) -> str:
    return (
        f'<div class="kpi kpi-{tone}">'
        f'<div class="kpi-top">'
        f'<span class="kpi-icon">{icon_svg(icon, 16)}</span>'
        f'<span class="kpi-label">{esc(label)}</span>'
        f'</div>'
        f'<div class="kpi-value">{esc(value)}</div>'
        f'{foot}'
        f'</div>'
    )


def kpi_foot_html(
    percent: int,
    note: str,
) -> str:
    percent = max(
        0,
        min(100, percent),
    )

    return (
        '<div class="kpi-foot">'
        '<div class="kpi-bar">'
        f'<span style="width:{percent}%"></span>'
        '</div>'
        f'<span class="kpi-note">{esc(note)}</span>'
        '</div>'
    )


def render_metrics(
    stats: Dict[str, Any],
) -> None:
    total_value = (
        to_float(
            stats.get("total_amount")
        )
        or 0.0
    )

    total = int(
        to_float(
            stats.get("total_invoices")
        )
        or 0
    )

    approved = int(
        to_float(
            stats.get("approved")
        )
        or 0
    )

    needs_review = int(
        to_float(
            stats.get("needs_review")
        )
        or 0
    )

    rejected = int(
        to_float(
            stats.get("rejected")
        )
        or 0
    )

    def share(
        count: int,
    ) -> int:
        return (
            round(
                100 * count / total
            )
            if total
            else 0
        )

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

    with st.container(
        key="kpi_row"
    ):
        columns = st.columns(
            5,
            gap="small",
        )

        for column, card in zip(
            columns,
            cards,
        ):
            with column:
                html_block(
                    card
                )