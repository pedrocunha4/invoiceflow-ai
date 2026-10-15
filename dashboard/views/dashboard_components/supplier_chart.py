from __future__ import annotations

import re
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from core.i18n import t
from core.ui import (
    card_head_html,
    format_money,
    html_block,
    to_float,
)

SUPPLIER_CHART_LIMIT = 10
CARD_HEIGHT = 440

SUPPLIER_SUFFIX_RE = re.compile(
    r"[,\s]+LDA\.?\s*$",
    re.IGNORECASE,
)


def chart_label(
    name: str,
) -> str:
    return (
        SUPPLIER_SUFFIX_RE
        .sub("", name)
        .strip()
        or name
    )


def supplier_totals(
    invoices: List[Dict[str, Any]],
    limit: int = SUPPLIER_CHART_LIMIT,
) -> pd.DataFrame:
    totals: Dict[str, float] = {}

    for invoice in invoices:
        amount = to_float(
            invoice.get("total")
        )

        if (
            amount is None
            or amount != amount
        ):
            continue

        supplier = (
            str(
                invoice.get(
                    "supplier_name"
                )
                or ""
            ).strip()
            or t(
                "chart.unknown_supplier"
            )
        )

        totals[supplier] = (
            totals.get(
                supplier,
                0.0,
            )
            + amount
        )

    frame = pd.DataFrame(
        {
            "Supplier": list(
                totals.keys()
            ),
            "Total": list(
                totals.values()
            ),
        }
    )

    if frame.empty:
        return frame

    frame = (
        frame
        .sort_values(
            "Total",
            ascending=False,
        )
        .head(limit)
        .reset_index(
            drop=True
        )
    )

    labels = frame[
        "Supplier"
    ].map(
        chart_label
    )

    frame["Supplier"] = frame[
        "Supplier"
    ].where(
        labels.duplicated(
            keep=False
        ),
        labels,
    )

    return frame


def supplier_chart_spec() -> Dict[str, Any]:
    y_axis = {
        "field": "Supplier",
        "type": "nominal",
        "sort": "-x",
        "axis": {
            "title": None,
            "labelLimit": 280,
            "labelColor": "#E2E8F0",
            "labelFontSize": 12,
            "labelPadding": 10,
            "ticks": False,
            "domain": False,
        },
    }

    x_axis = {
        "field": "Total",
        "type": "quantitative",
        "axis": {
            "title": None,
            "labelColor": "#64748B",
            "labelFontSize": 10,
            "labelExpr": (
                "format(datum.value, '~s') + ' €'"
            ),
            "gridColor": "#16233B",
            "domain": False,
            "ticks": False,
        },
    }

    return {
        "background": "transparent",
        "padding": {
            "left": 4,
            "right": 78,
            "top": 6,
            "bottom": 4,
        },
        "autosize": {
            "type": "fit",
            "contains": "padding",
        },
        "config": {
            "view": {
                "stroke": None,
            }
        },
        "height": {
            "step": 36,
        },
        "layer": [
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusEnd": 4,
                    "height": {
                        "band": 0.6,
                    },
                },
                "encoding": {
                    "y": y_axis,
                    "x": x_axis,
                    "color": {
                        "condition": {
                            "test": (
                                "datum.Rank === 0"
                            ),
                            "value": "#38BDF8",
                        },
                        "value": "#1D5F8F",
                    },
                    "tooltip": [
                        {
                            "field": "Supplier",
                            "type": "nominal",
                        },
                        {
                            "field": "Label",
                            "type": "nominal",
                            "title": "Total",
                        },
                    ],
                },
            },
            {
                "mark": {
                    "type": "text",
                    "align": "left",
                    "dx": 7,
                    "fontSize": 11,
                    "color": "#CBD5E1",
                },
                "encoding": {
                    "y": {
                        "field": "Supplier",
                        "type": "nominal",
                        "sort": "-x",
                    },
                    "x": {
                        "field": "Total",
                        "type": "quantitative",
                    },
                    "text": {
                        "field": "Label",
                        "type": "nominal",
                    },
                },
            },
        ],
    }


def render_supplier_chart(
    invoices: List[Dict[str, Any]],
    height: int = CARD_HEIGHT,
) -> None:
    with st.container(
        border=True,
        height=height,
        key="card_chart",
    ):
        html_block(
            card_head_html(
                t("chart.title"),
                t("chart.caption"),
            )
        )

        data = supplier_totals(
            invoices
        )

        if data.empty:
            st.info(
                t("chart.empty")
            )
            return

        data["Label"] = data[
            "Total"
        ].map(
            lambda value: format_money(
                value,
                "EUR",
            )
        )

        data["Rank"] = range(
            len(data)
        )

        st.vega_lite_chart(
            data,
            supplier_chart_spec(),
            width="stretch",
            theme=None,
        )