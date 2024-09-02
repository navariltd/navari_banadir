# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days


def execute(filters=None):
    if not filters:
        filters = {}
    columns = get_columns(filters)
    stock = get_total_stock(filters)

    return columns, stock


def get_columns(filters):
    columns = [
        _("Item") + ":Link/Item:150",
        _("UOM") + ":Link/UOM:100",
        _("Current Qty") + ":Float:100",
    ]

    if filters.get("alternative_uom"):
        columns.append(_("Alternative UOM") + ":Link/UOM:100")
        columns.append(
            _("Qty in Alternative UOM") + ":Float:120"
        )  # Column for converted quantity

    if filters.get("group_by") == "Warehouse":
        columns.insert(0, _("Warehouse") + ":Link/Warehouse:0")
    else:
        columns.insert(0, _("Company") + ":Link/Company:0")

    return columns


def get_total_stock(filters):
    bin = frappe.qb.DocType("Bin")
    item = frappe.qb.DocType("Item")
    wh = frappe.qb.DocType("Warehouse")

    query = (
        frappe.qb.from_(bin)
        .inner_join(item)
        .on(bin.item_code == item.item_code)
        .inner_join(wh)
        .on(wh.name == bin.warehouse)
        .where(bin.actual_qty != 0)
    )

    # Apply date filter if provided
    if filters.get("filter_date"):
        next_day = add_days(filters.get("filter_date"), 1)
        query = query.where(bin.modified <= next_day)

    # Apply company filter if provided
    if filters.get("company"):
        query = query.where(wh.company == filters.get("company"))

    # Apply item group filter if provided
    if filters.get("item_group"):
        query = query.where(item.item_group == filters.get("item_group"))

    # Apply warehouse filter if provided
    if filters.get("warehouse"):
        query = query.where(bin.warehouse == filters.get("warehouse"))

    # Grouping by Warehouse or Company
    group_by_field = (
        bin.warehouse if filters.get("group_by") == "Warehouse" else wh.company
    )
    query = query.select(
        group_by_field.as_("group_by_field"),
        item.item_code,
        item.stock_uom,  # Include UOM
        Sum(bin.actual_qty).as_("actual_qty"),
    ).groupby(group_by_field, item.item_code)

    # Include conversion to alternative UOM if selected
    if filters.get("alternative_uom"):
        uom_conversion = frappe.qb.DocType("UOM Conversion Detail")
        query = query.left_join(uom_conversion).on(
            (item.item_code == uom_conversion.parent)
            & (uom_conversion.uom == filters.get("alternative_uom"))
        )

        # Adjust the select clause to include the alternative UOM conversion
        query = query.select(
            uom_conversion.uom.as_("alternative_uom"),
            (Sum(bin.actual_qty) / uom_conversion.conversion_factor).as_(
                "qty_in_alternative_uom"
            ),
        )

    return query.run()


def get_conversion_factor(item_code, alternative_uom):
    uom_conversion = frappe.db.get_value(
        "UOM Conversion Detail",
        {"parent": item_code, "uom": alternative_uom},
        "conversion_factor",
    )
    return uom_conversion or 1
