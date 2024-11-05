# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_serial_nos_from_sle
from frappe.utils import cstr, flt, get_link_to_form, get_time, getdate, nowdate, nowtime


BUYING_VOUCHER_TYPES = ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]
SELLING_VOUCHER_TYPES = ["Sales Invoice", "Delivery Note"]


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{"label": _("Posting Date"), "fieldtype": "Date", "fieldname": "posting_date", "width": 120},
		{"label": _("Posting Time"), "fieldtype": "Time", "fieldname": "posting_time", "width": 90},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"fieldname": "voucher_type",
			"width": 160,
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options": "voucher_type",
			"width": 230,
		},
		{
			"label": _("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"fieldname": "warehouse",
			"options": "Warehouse",
			"width": 120,
		},
		{
			"label": _("Status"),
			"fieldtype": "Data",
			"fieldname": "status",
			"width": 90,
		},
		{
			"label": _("Serial No"),
			"fieldtype": "Link",
			"fieldname": "serial_no",
			"options": "Serial No",
			"width": 130,
		},
		{
		"label":_("Engine No"),
		"fieldtype":"Data",
		"fieldname":"custom_engine_number",
		"width":100,
		},
		{
			"label": _("Valuation Rate"),
			"fieldtype": "Float",
			"fieldname": "valuation_rate",
			"width": 130,
		},
		{
			"label": _("Qty"),
			"fieldtype": "Float",
			"fieldname": "qty",
			"width": 150,
		},
		{
			"label": _("Party Type"),
			"fieldtype": "Data",
			"fieldname": "party_type",
			"width": 90,
		},
		{
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"fieldname": "party",
			"options": "party_type",
			"width": 120,
		},
	]

	return columns


def get_data(filters):
	stock_ledgers = get_stock_ledger_entries(filters, "<=", order="asc", check_serial_no=False)

	if not stock_ledgers:
		return []

	data = []
	serial_bundle_ids = [d.serial_and_batch_bundle for d in stock_ledgers if d.serial_and_batch_bundle]
	bundle_wise_serial_nos = get_serial_nos(filters, serial_bundle_ids)
	for row in stock_ledgers:
		args = frappe._dict(
			{
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"status": "Active" if row.actual_qty > 0 else "Delivered",
				"company": row.company,
				"warehouse": row.warehouse,
				"qty": 1 if row.actual_qty > 0 else -1,
			}
		)

		# get party details depending on the voucher type
		party_field = (
			"supplier"
			if row.voucher_type in BUYING_VOUCHER_TYPES
			else ("customer" if row.voucher_type in SELLING_VOUCHER_TYPES else None)
		)
		args.party_type = party_field.title() if party_field else None
		args.party = (
			frappe.db.get_value(row.voucher_type, row.voucher_no, party_field) if party_field else None
		)

		serial_nos = []
		if row.serial_no:
			parsed_serial_nos = get_serial_nos_from_sle(row.serial_no)
			for serial_no in parsed_serial_nos:
				if filters.get("serial_no") and filters.get("serial_no") != serial_no:
					continue

				
				serial_nos.append(
					{
						"serial_no": serial_no,
						"valuation_rate": abs(row.stock_value_difference / row.actual_qty),
						#"custom_engine_number": engine_no,  # Adding Engine No
					}
				)
		if row.serial_and_batch_bundle:
			serial_nos.extend(bundle_wise_serial_nos.get(row.serial_and_batch_bundle, []))
		for index, bundle_data in enumerate(serial_nos):
			if index == 0:
				new_args = copy.deepcopy(args)
				new_args.serial_no = bundle_data.get("serial_no")
				new_args.valuation_rate = bundle_data.get("valuation_rate")
				new_args.cutom_engine_number=bundle_data.get('custom_engine_number')
				data.append(new_args)
			else:
				data.append(
					{
						"serial_no": bundle_data.get("serial_no"),
						"valuation_rate": bundle_data.get("valuation_rate"),
						"qty": args.qty,
                              "custom_engine_number": bundle_data.get("custom_engine_number"),

					}
				)
    
	return data


def get_serial_nos(filters, serial_bundle_ids):
	bundle_wise_serial_nos = {}
	bundle_filters = {"parent": ["in", serial_bundle_ids]}
	if filters.get("serial_no"):
		bundle_filters["serial_no"] = filters.get("serial_no")

	for d in frappe.get_all(
		"Serial and Batch Entry",
		fields=["serial_no", "parent", "stock_value_difference as valuation_rate"],
		filters=bundle_filters,
		order_by="idx asc",
	):
		engine_no = frappe.db.get_value("Serial No", d.serial_no, "custom_engine_number")
		bundle_wise_serial_nos.setdefault(d.parent, []).append(
			{
				"serial_no": d.serial_no,
				"valuation_rate": abs(d.valuation_rate),
      			"custom_engine_number": engine_no,
			}
		)
	return bundle_wise_serial_nos



def get_stock_ledger_entries(
	previous_sle,
	operator=None,
	order="desc",
	limit=None,
	for_update=False,
	debug=False,
	check_serial_no=True,
	extra_cond=None,
):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	conditions = f" and posting_datetime {operator} %(posting_datetime)s"
	if previous_sle.get("warehouse"):
		conditions += " and warehouse = %(warehouse)s"
	elif previous_sle.get("warehouse_condition"):
		conditions += " and " + previous_sle.get("warehouse_condition")

	if check_serial_no and previous_sle.get("serial_no"):
		serial_no = previous_sle.get("serial_no")
		conditions += (
			""" and
			(
				serial_no = {}
				or serial_no like {}
				or serial_no like {}
				or serial_no like {}
			)
		"""
		).format(
			frappe.db.escape(serial_no),
			frappe.db.escape(f"{serial_no}\n%"),
			frappe.db.escape(f"%\n{serial_no}"),
			frappe.db.escape(f"%\n{serial_no}\n%"),
		)
	# Include item_code condition if present
	if previous_sle.get("item_code"):
		conditions += " and item_code = %(item_code)s"
  
	if not previous_sle.get("posting_date"):
		previous_sle["posting_datetime"] = "1900-01-01 00:00:00"
	else:
		previous_sle["posting_datetime"] = get_combine_datetime(
			previous_sle["posting_date"], previous_sle["posting_time"]
		)

	if operator in (">", "<=") and previous_sle.get("name"):
		conditions += " and name!=%(name)s"

	if extra_cond:
		conditions += f"{extra_cond}"

	return frappe.db.sql(
		"""
		select *, posting_datetime as "timestamp"
		from `tabStock Ledger Entry`
		where is_cancelled = 0
		{conditions}
		order by posting_datetime {order}, creation {order}
		{limit} {for_update}""".format(
			conditions=conditions,
			limit=limit or "",
			for_update=for_update and "for update" or "",
			order=order,
		),
		previous_sle,
		as_dict=1,
		debug=debug,
	)


def get_combine_datetime(posting_date, posting_time):
	import datetime

	if isinstance(posting_date, str):
		posting_date = getdate(posting_date)

	if isinstance(posting_time, str):
		posting_time = get_time(posting_time)

	if isinstance(posting_time, datetime.timedelta):
		posting_time = (datetime.datetime.min + posting_time).time()

	return datetime.datetime.combine(posting_date, posting_time).replace(microsecond=0)
