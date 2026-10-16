from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from core.i18n import current_lang, t
from core.status import status_meta
from core.ui import (
    card_head_html,
    display,
    esc,
    html_block,
    section_header,
    to_float,
)


def parse_invoice_date(
    value: Any,
):
    if not value:
        return None

    try:
        parsed = pd.to_datetime(
            value,
            errors="raise",
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        return None

    return (
        None
        if pd.isna(parsed)
        else parsed.date()
    )


def filter_invoices(
    invoices: List[Dict[str, Any]],
    query: str,
    status_key: str,
    start_date: Any = None,
    end_date: Any = None,
) -> List[Dict[str, Any]]:
    query = (
        query
        .strip()
        .lower()
    )

    result = []

    for invoice in invoices:
        if (
            status_key != "all"
            and invoice.get(
                "status"
            ) != status_key
        ):
            continue

        haystack = (
            f'{invoice.get("supplier_name", "")} '
            f'{invoice.get("invoice_number", "")}'
        ).lower()

        if (
            query
            and query not in haystack
        ):
            continue

        if (
            start_date is not None
            and end_date is not None
        ):
            invoice_date = parse_invoice_date(
                invoice.get(
                    "invoice_date"
                )
            )

            if invoice_date is None:
                continue

            if not (
                start_date
                <= invoice_date
                <= end_date
            ):
                continue

        result.append(
            invoice
        )

    return result


def reset_registry_filters(
    lang: str,
) -> None:
    st.session_state[
        "registry_search"
    ] = ""

    st.session_state[
        "registry_date_range"
    ] = ()

    st.session_state[
        f"registry_status_label_{lang}"
    ] = t(
        "registry.all_statuses"
    )


def render_invoice_table(
    invoices: List[Dict[str, Any]],
) -> None:
    lang = current_lang()

    if not invoices:
        section_header(
            t("registry.title"),
            t("registry.caption"),
        )

        st.info(
            t("registry.empty")
        )

        return

    with st.container(
        border=True,
        key="registry_panel",
    ):
        html_block(
            card_head_html(
                t("registry.title"),
                t("registry.caption"),
            )
        )

        (
            search_col,
            status_col,
            date_col,
            clear_col,
        ) = st.columns(
            [
                1.95,
                0.90,
                1.20,
                0.70,
            ],
            gap="small",
        )

        # Search

        with search_col:
            html_block(
                f'<div class="flabel">'
                f'{esc(t("registry.label_search"))}'
                f'</div>'
            )

            query = st.text_input(
                "Search",
                placeholder=t(
                    "registry.search"
                ),
                label_visibility="collapsed",
                key="registry_search",
            )

        # Status

        with status_col:
            html_block(
                f'<div class="flabel">'
                f'{esc(t("registry.label_status"))}'
                f'</div>'
            )

            status_options = {
                t(
                    "registry.all_statuses"
                ): "all",
                t(
                    "status.approved"
                ): "approved",
                t(
                    "status.needs_review"
                ): "needs_review",
                t(
                    "status.rejected"
                ): "rejected",
            }

            selected_status = (
                st.selectbox(
                    "Status filter",
                    options=list(
                        status_options.keys()
                    ),
                    label_visibility="collapsed",
                    key=(
                        f"registry_status_"
                        f"label_{lang}"
                    ),
                )
            )

            status_key = (
                status_options[
                    selected_status
                ]
            )

        # Invoice date

        date_format = (
            "DD/MM/YYYY"
            if lang == "PT"
            else "YYYY-MM-DD"
        )

        with date_col:
            html_block(
                f'<div class="flabel">'
                f'{esc(t("registry.label_date"))}'
                f'</div>'
            )

            if (
                "registry_date_range"
                not in st.session_state
            ):
                st.session_state[
                    "registry_date_range"
                ] = ()

            current_range = (
                st.session_state[
                    "registry_date_range"
                ]
            )

            if (
                isinstance(
                    current_range,
                    (tuple, list),
                )
                and len(
                    current_range
                ) == 2
            ):
                date_label = (
                    f"{current_range[0]} → "
                    f"{current_range[1]}"
                )

            else:
                date_label = t(
                    "registry.any_date"
                )

            with st.popover(
                date_label,
                width="stretch",
            ):
                st.date_input(
                    t(
                        "registry.date_range"
                    ),
                    key="registry_date_range",
                    format=date_format,
                    label_visibility="collapsed",
                )

        # Clear filters

        date_range = (
            st.session_state.get(
                "registry_date_range",
                (),
            )
        )

        has_filters = bool(
            query.strip()
            or status_key != "all"
            or (
                isinstance(
                    date_range,
                    (tuple, list),
                )
                and len(
                    date_range
                ) > 0
            )
        )

        with clear_col:
            html_block(
                '<div class="flabel">'
                '&nbsp;'
                '</div>'
            )

            st.button(
                f'✕ {t("registry.clear")}',
                key=(
                    f"registry_clear_"
                    f"{lang}"
                ),
                disabled=not has_filters,
                on_click=(
                    reset_registry_filters
                ),
                args=(lang,),
                width="stretch",
            )

        # Apply filters

        start_date = None
        end_date = None

        if (
            isinstance(
                date_range,
                (tuple, list),
            )
            and len(
                date_range
            ) == 2
        ):
            (
                start_date,
                end_date,
            ) = date_range

        filtered = filter_invoices(
            invoices=invoices,
            query=query,
            status_key=status_key,
            start_date=start_date,
            end_date=end_date,
        )

        st.caption(
            t(
                "registry.showing",
                shown=len(filtered),
                total=len(invoices),
            )
        )

        if not filtered:
            st.info(
                t(
                    "registry.no_match"
                )
            )
            return

        # Table

        col = {
            name: t(
                f"col.{name}"
            )
            for name in (
                "id",
                "supplier",
                "vat",
                "number",
                "date",
                "amount",
                "currency",
                "status",
            )
        }

        head = "".join(
            [
                f"<th>{esc(col['id'])}</th>",
                f"<th>{esc(col['supplier'])}</th>",
                f"<th>{esc(col['vat'])}</th>",
                f"<th>{esc(col['number'])}</th>",
                f"<th>{esc(col['date'])}</th>",
                (
                    f'<th class="num">'
                    f'{esc(col["amount"])}'
                    f'</th>'
                ),
                f"<th>{esc(col['currency'])}</th>",
                f"<th>{esc(col['status'])}</th>",
            ]
        )

        status_classes = {
            "approved": "badge-green",
            "needs_review": "badge-amber",
            "rejected": "badge-red",
        }

        body = ""

        for invoice in filtered:
            status = invoice.get(
                "status"
            )

            meta = status_meta(
                status
            )

            badge_class = (
                status_classes.get(
                    status,
                    "badge-gray",
                )
            )

            amount = to_float(
                invoice.get(
                    "total"
                )
            )

            amount_text = (
                f"{amount:,.2f}"
                if amount is not None
                else "—"
            )

            body += (
                "<tr>"
                f'<td class="id">'
                f'#{esc(display(invoice.get("id")))}'
                f'</td>'
                f'<td class="sup">'
                f'{esc(display(invoice.get("supplier_name")))}'
                f'</td>'
                f'<td class="mono">'
                f'{esc(display(invoice.get("supplier_vat_number")))}'
                f'</td>'
                f'<td class="mono bright">'
                f'{esc(display(invoice.get("invoice_number")))}'
                f'</td>'
                f'<td class="mono">'
                f'{esc(display(invoice.get("invoice_date")))}'
                f'</td>'
                f'<td class="num">'
                f'{esc(amount_text)}'
                f'</td>'
                f'<td class="mono">'
                f'{esc(display(invoice.get("currency")))}'
                f'</td>'
                '<td>'
                f'<span class="badge {badge_class}">'
                f'{esc(meta["label"])}'
                '</span>'
                '</td>'
                '</tr>'
            )

        html_block(
            '<div class="if-table-wrap">'
            '<table class="if-table">'
            f'<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody>'
            '</table>'
            '</div>'
        )