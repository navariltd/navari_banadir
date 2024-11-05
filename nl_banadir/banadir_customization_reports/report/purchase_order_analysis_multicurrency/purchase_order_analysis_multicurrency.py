# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

# import frappe


import copy

import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import date_diff, flt, getdate
from erpnext.accounts.report.utils import convert, get_rate_as_at
from nl_banadir.banadir_customization_reports.report.utils import format_in_lakhs


def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)

	columns = get_columns(filters)
	data = get_data(filters)
	

	if not data:
		return [], [], None, []

	data, chart_data = prepare_data(data, filters)
	if filters.get("in_party_currency")==1:
		data=convert_to_party_currency(data, filters)
	else:
		data=convert_currency_columns(data, filters)
	return columns, data, None, chart_data


def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))


def get_data(filters):
	po = frappe.qb.DocType("Purchase Order")
	po_item = frappe.qb.DocType("Purchase Order Item")
	pi_item = frappe.qb.DocType("Purchase Invoice Item")

	query = (
		frappe.qb.from_(po)
		.from_(po_item)
		.left_join(pi_item)
		.on(pi_item.po_detail == po_item.name)
		.select(
			po.transaction_date.as_("date"),
			po_item.schedule_date.as_("required_date"),
			po_item.project,
			po.name.as_("purchase_order"),
			po.order_confirmation_no,
			po.plc_conversion_rate,
			po.conversion_rate,
			po.branch,
			po.status,
			po.supplier,
			po.name,
			po.grand_total,
			po.base_grand_total,
			po_item.item_code,
			po_item.qty,
			po_item.received_qty,
			po.custom_container_qty,
			
			(po_item.qty - po_item.received_qty).as_("pending_qty"),
			Sum(IfNull(pi_item.qty, 0)).as_("billed_qty"),
			po_item.base_amount.as_("amount"),
			(po_item.received_qty * po_item.base_rate).as_("received_qty_amount"),
			(po_item.billed_amt * IfNull(po.conversion_rate, 1)).as_("billed_amount"),
			(po_item.base_amount - (po_item.billed_amt * IfNull(po.conversion_rate, 1))).as_(
				"pending_amount"
			),
			po.set_warehouse.as_("warehouse"),
			po.company,
			po_item.name,
		)
		.where((po_item.parent == po.name) & (po.status.notin(("Stopped", "Closed"))) & (po.docstatus == 1))
		.groupby(po_item.name)
		.orderby(po.transaction_date)
	)

	for field in ("company", "name"):
		if filters.get(field):
			query = query.where(po[field] == filters.get(field))

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(po.transaction_date.between(filters.get("from_date"), filters.get("to_date")))

	if filters.get("status"):
		query = query.where(po.status.isin(filters.get("status")))

	if filters.get("project"):
		query = query.where(po_item.project == filters.get("project"))

	data = query.run(as_dict=True)
	return data


def prepare_data(data, filters):
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
 
	is_inr = True if presentation_currency == "INR" else False
	completed, pending = 0, 0
	pending_field = "pending_amount"
	completed_field = "billed_amount"

	if filters.get("group_by_po"):
		purchase_order_map = {}

	for row in data:
		# sum data for chart
		completed += row[completed_field]
		pending += row[pending_field]
		# prepare data for report view
		row["advance_paid"] = calculate_advance_paid(row["purchase_order"])
		row["qty_to_bill"] = flt(row["qty"]) - flt(row["billed_qty"])
		row["balance"] = flt(row["base_grand_total"]) - flt(row["advance_paid"])
		
		# Fetch additional fields if they exist
		row["branch"] = row.get("branch", None)
		row["order_confirmation_no"] = row.get("order_confirmation_no", None)
		row["plc_conversion_rate"] = row.get("plc_conversion_rate", 1.0)
		row["conversion_rate"] = row.get("conversion_rate", 1.0)
		if filters.get("in_party_currency")==1:
			row['billing_currency']=billing_currency(data, filters)

		# Convert amount to lakhs if currency is INR
		if is_inr:
			row["amount"] = format_in_lakhs(row["amount"])
			row["received_qty_amount"] = format_in_lakhs(row["received_qty_amount"])
			row["billed_amount"] = format_in_lakhs(row["billed_amount"])
			row["pending_amount"] = format_in_lakhs(row["pending_amount"])
			row["advance_paid"] = format_in_lakhs(row["advance_paid"])
			row["balance"] = format_in_lakhs(row["balance"])
		if filters.get("group_by_po"):
			po_name = row["purchase_order"]

			if po_name not in purchase_order_map:
				# create an entry
				row_copy = copy.deepcopy(row)
				purchase_order_map[po_name] = row_copy
			else:
				# update existing entry
				po_row = purchase_order_map[po_name]
				po_row["required_date"] = min(getdate(po_row["required_date"]), getdate(row["required_date"]))

				# sum numeric columns
				fields = [
					"qty",
					"received_qty",
					"pending_qty",
	 "custom_container_qty",
					"billed_qty",
					"qty_to_bill",
					"amount",
					"received_qty_amount",
					"billed_amount",
					"pending_amount",
					"plc_conversion_rate",  # Ensure these are summed as well
					"conversion_rate",
				]
				for field in fields:
					po_row[field] = flt(row[field]) + flt(po_row[field])

				
	chart_data = prepare_chart_data(pending, completed)

	if filters.get("group_by_po"):
		data = []
		for po in purchase_order_map:
			data.append(purchase_order_map[po])
		return data, chart_data

	return data, chart_data



def prepare_chart_data(pending, completed):
	labels = ["Amount to Bill", "Billed Amount"]

	return {
		"data": {"labels": labels, "datasets": [{"values": [pending, completed]}]},
		"type": "donut",
		"height": 300,
	}


def get_columns(filters):
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 90},
		{"label": _("Required By"), "fieldname": "required_date", "fieldtype": "Date", "width": 90},
		{
			"label": _("Purchase Order"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 160,
		},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 130},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 130,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 130,
		},
	]
	if filters.get("in_party_currency")==1:
		columns.append(
			{
				"label": _("Billing Currency"),
				"fieldname": "billing_currency",
				"fieldtype": "Data",
				"width": 100,
			}
		)
  
	if not filters.get("group_by_po"):
		columns.append(
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			}
		)

	columns.extend(
		[
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"precision":2,
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Received Qty"),
				"fieldname": "received_qty",
				"fieldtype": "Float",
	"precision":2,
				"width": 120,
				"convertible": "qty",
			},
			{
				"label": _("Pending Qty"),
				"fieldname": "pending_qty",
				"fieldtype": "Float",
				"precision":2,
				"width": 80,
				"convertible": "qty",
			},
   
				{
					"label":"Container Qty",
					"fieldname":"custom_container_qty",
					"fieldtype":"Float",
					"precision":2,
				},

			{
				"label": _("Billed Qty"),
				"fieldname": "billed_qty",
				"fieldtype": "Float",
	"precision":2,
				"width": 80,
				"convertible": "qty",
			},
			{
				"label": _("Qty to Bill"),
				"fieldname": "qty_to_bill",
				"fieldtype": "Float",
				"precision":2,
				"width": 80,
				"convertible": "qty",
			},
  
			{
				"label": _(f"Amount(<strong>{presentation_currency}</strong>)") if not filters.get("in_party_currency") else _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"options": "currency",
	"precision":2,
				"width": 110,
				"convertible": "rate",
			},
	{
				"label":f"Advance Paid (<strong>{presentation_currency}</strong>)" if not filters.get("in_party_currency") else _("Advance Paid"),
				"fieldname":"advance_paid",
				"fieldtype": "Currency",
				"options": "currency",
					"precision":2,	
						"width":100,	
				},
	{
				"label": f"Balance Amount(<strong>{presentation_currency}</strong>)" if not filters.get("in_party_currency") else _("Balance Amount"),
				"fieldname": "balance",
				"fieldtype": "Currency",
				"options": "currency",
				"precision": 2,
				"width": 130,
				"convertible": "rate",
			},
			{
				"label": _(f"Billed Amount(<strong>{presentation_currency}</strong>)") if not filters.get("in_party_currency") else _("Billed Amount"),
				"fieldname": "billed_amount",
				"fieldtype": "Currency",
				"options": "currency",
	"precision":2,
				"width": 110,
				"convertible": "rate",
			},
   

			{
				"label": _(f"Pending Amount(<strong>{presentation_currency}</strong>)" if not filters.get("in_party_currency") else "Pending Amount"),
				"fieldname": "pending_amount",
				"fieldtype": "Currency",
				"options": "currency",
	"precision":2,
				"width": 130,
	
				"convertible": "rate",
			},
			{
				"label": _(f"Received Qty Amount(<strong>{presentation_currency}</strong>)") if not filters.get("in_party_currency") else _("Received Qty Amount"),
				"fieldname": "received_qty_amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 130,
				"precision":2,
				"convertible": "rate",
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			},
			{
				"label": _("Company"),
				"fieldname": "company",
				"fieldtype": "Link",
				"options": "Company",
				"width": 100,
			},
{
			"label": _("Branch"),
			"fieldname": "branch",
			"fieldtype": "Link",
			"options": "Branch",
			"width": 100,
		},
		{
			"label": _("Order Confirmation No"),
			"fieldname": "order_confirmation_no",
			"fieldtype": "Data",
			"width": 100,
		},
		
		{
			"label": _("Exchange Rate"),
			"fieldname": "conversion_rate",
			"fieldtype": "Float",
			"precision":4,
			"width": 100,
		},
		{
		"label": _("Currency"),
		"fieldname": "currency",
		"fieldtype": "Currency",
		"width": 100,
		},
 

		]
	)

	return columns

def convert_currency_columns(data, filters):
	date = filters.get("to_date") or frappe.utils.now()
	to_currency = frappe.get_cached_value("Company", filters.company, "default_currency")
	from_currency = filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
	currency_fields = ['amount', 'received_qty_amount', 'billed_amount', 'pending_amount','balance','advance_paid']  # Add other fields as necessary

	for entry in data:
		for field in currency_fields:
			entry["currency"]=from_currency
			entry[field] = convert(entry.get(field, 0), from_currency, to_currency, date)
	
	return data

def calculate_advance_paid(purchase_order):
	advance_paid = 0
	payment_references = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Purchase Order", "reference_name": purchase_order, "docstatus": 1},
		fields=["parent"]
	)
	
	if payment_references:
		base_paid_amounts = frappe.get_all(
			"Payment Entry",
			filters={"name": ["in", [pr['parent'] for pr in payment_references]]},
			fields=["base_paid_amount"]
		)
		advance_paid = sum([amount['base_paid_amount'] for amount in base_paid_amounts]) or 0.0  # Ensures advance_paid is 0 if None

	return advance_paid


def convert_to_party_currency(data, filters):
		for entry in data:
			entry["amount"] =  entry["amount"] / entry["conversion_rate"]
			entry["received_qty_amount"] = entry["received_qty_amount"] / entry["conversion_rate"]
			entry["billed_amount"] = entry["billed_amount"] / entry["conversion_rate"]
			entry["pending_amount"] = entry["pending_amount"] / entry["conversion_rate"]
			entry["advance_paid"] = entry["advance_paid"] / entry["conversion_rate"]
			entry["balance"] = entry["balance"] / entry["conversion_rate"]
		
		return data
		
def billing_currency(data, filters):
	if filters.get("in_party_currency")==1:
		
		for entry in data:
			supplier_currency = frappe.db.get_value("Supplier", entry["supplier"], "default_currency")
			if not supplier_currency:  # This checks for both None and empty string
				supplier_currency = ""
	return supplier_currency
	

