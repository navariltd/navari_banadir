# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum


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
		columns.append(_("Qty in Alternative UOM") + ":Float:120")  # Column for converted quantity

	if filters.get("group_by") == "Warehouse":
		columns.insert(0, _("Warehouse") + ":Link/Warehouse:150")
	else:
		columns.insert(0, _("Company") + ":Link/Company:250")

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
	if filters.get("current_date"):
		query = query.where(bin.modified <= filters.get("current_date"))
		
    # Apply company filter if provided
	if filters.get("company"):
		query = query.where(wh.company == filters.get("company"))

	if filters.get("group_by") == "Warehouse":
		if filters.get("company"):
			query = query.where(wh.company == filters.get("company"))

		query = query.select(bin.warehouse).groupby(bin.warehouse)
	else:
		query = query.select(wh.company).groupby(wh.company)

	# Select item_code, uom, and actual_qty
	query = query.select(
		item.item_code, 
		item.stock_uom,  # Include UOM
		Sum(bin.actual_qty).as_("actual_qty")
	)

	# Include conversion to alternative UOM if selected
	if filters.get("alternative_uom"):
		# Join with UOM Conversion table if necessary
		uom_conversion = frappe.qb.DocType("UOM Conversion Detail")
		query = query.left_join(uom_conversion).on(
			(item.item_code == uom_conversion.parent) &
			(uom_conversion.uom == filters.get("alternative_uom"))
		)

		# Calculate the converted quantity in the alternative UOM
		query = query.select(
			uom_conversion.uom.as_("alternative_uom"),
			(Sum(bin.actual_qty) / uom_conversion.conversion_factor).as_("qty_in_alternative_uom")
		)
        

	query = query.groupby(item.item_code)

	return query.run() 

def get_conversion_factor(item_code, alternative_uom):
	
    uom_conversion = frappe.db.get_value("UOM Conversion Detail", {"parent": item_code, "uom": alternative_uom}, "conversion_factor")
	
    return uom_conversion or 1