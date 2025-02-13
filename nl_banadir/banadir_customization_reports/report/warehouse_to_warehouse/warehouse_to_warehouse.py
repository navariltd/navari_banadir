# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	""" Main function for report execution. """
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	""" Returns the report column structure. """
	return [
		{"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 120},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150, "hidden":1},
		{"label": "From Warehouse", "fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"label": "To Warehouse", "fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"label": "Transferred Qty", "fieldname": "qty", "fieldtype": "Float", "width": 120},
		{"label": "Current Qty in Destination", "fieldname": "current_qty", "fieldtype": "Float", "width": 150, "hidden":1},
		{"label":"Valuation Rate", "fieldname":"valuation_rate", "fieldtype":"Currency","options":"currency", "width": 120, "hidden":1 if filters.get('hide_column') else 0},
		{"label":"Rate", "fieldname":"rate", "fieldtype":"Currency","options":"currency", "width": 120, "options":"currency","hidden":1 if filters.get('hide_column') else 0},
		{"label":"Amount", "fieldname":"amount", "fieldtype":"Currency","options":"currency", "width": 120, "options":"currency","hidden":1 if filters.get('hide_column') else 0},
		{"label":"Currency", "fieldname":"currency", "fieldtype":"Link","options":"Currency", "width": 12, "hidden":1},
		
	]


def get_conditions(filters):
	""" Generates SQL conditions dynamically based on filters. """
	conditions = ["se.docstatus = 1", "se.stock_entry_type = 'Material Transfer'"]
	values = {}

	if filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	if filters.get("from_warehouse"):
		conditions.append("sed.s_warehouse = %(from_warehouse)s")
		values["from_warehouse"] = filters["from_warehouse"]

	if filters.get("to_warehouse"):
		conditions.append("sed.t_warehouse = %(to_warehouse)s")
		values["to_warehouse"] = filters["to_warehouse"]

	if filters.get("company"):
		conditions.append("se.company = %(company)s")
		values["company"] = filters["company"]

	return " AND ".join(conditions), values

def fetch_stock_data(filters):
	"""Fetches stock entry data based on filters."""
	conditions, values = get_conditions(filters)

	query = f"""
		SELECT 
			se.posting_date, 
			se.name AS stock_entry, 
			sed.item_code, 
			sed.item_name, 
			sed.s_warehouse AS from_warehouse, 
			sed.t_warehouse AS to_warehouse, 
			sed.transfer_qty as qty,
			sed.valuation_rate,
			sed.basic_rate as rate,
			sed.amount,
			(SELECT actual_qty FROM `tabBin` WHERE item_code = sed.item_code AND warehouse = sed.t_warehouse) AS current_qty
		FROM `tabStock Entry` se
		JOIN `tabStock Entry Detail` sed ON se.name = sed.parent
		WHERE {conditions}
		ORDER BY se.posting_date DESC, se.name
	"""

	return frappe.db.sql(query, values, as_dict=True)

def calculate_subtotals(data, filters):
	"""Processes data to calculate subtotals and grand totals."""
	formatted_data = []
	current_stock_entry = None
	subtotal_qty = 0
	subtotal_current_qty = 0
	total_qty = 0
	total_current_qty = 0

	for row in data:
		if current_stock_entry and current_stock_entry != row["stock_entry"]:
			total_value=frappe.db.get_value("Stock Entry", current_stock_entry, "total_outgoing_value")
			formatted_data.append({
				"posting_date": "",
				"stock_entry": f"Total for {current_stock_entry}",
				"item_code": "",
				"item_name": "",
				"from_warehouse": "",
				"to_warehouse": "",
				"qty": subtotal_qty,
				"current_qty": subtotal_current_qty,
				"is_total": True,
				"amount":total_value,
			})
			total_qty += subtotal_qty
			total_current_qty += subtotal_current_qty
			subtotal_qty = 0
			subtotal_current_qty = 0

		formatted_data.append(row)
		subtotal_qty += row.get("qty", 0)
		subtotal_current_qty += row.get("current_qty", 0) if row.get("current_qty") is not None else 0
		current_stock_entry = row["stock_entry"]

	# Add last subtotal row
	if current_stock_entry:
		formatted_data.append({
			"posting_date": "",
			"stock_entry": f"Total for {current_stock_entry}",
			"item_code": "",
			"item_name": "",
			"from_warehouse": "",
			"to_warehouse": "",
			"qty": subtotal_qty,
			"current_qty": subtotal_current_qty,
			"is_total": True,
			"currency":frappe.get_cached_value('Company',  filters.get('company'),  'default_currency')
		})
		total_qty += subtotal_qty
		total_current_qty += subtotal_current_qty

	return formatted_data, total_qty, total_current_qty

def get_data(filters):
	"""Fetches stock data, processes subtotals, and adds a grand total row."""
	data = fetch_stock_data(filters)
	data = convert_alternative_uom(data, filters)
	data = currency_(data, filters)
	
	formatted_data, total_qty, total_current_qty = calculate_subtotals(data, filters)

	# Append the final grand total row
	formatted_data.append({
		"posting_date": "",
		"stock_entry": "Grand Total",
		"item_code": "",
		"item_name": "",
		"from_warehouse": "",
		"to_warehouse": "",
		"qty": total_qty,
		"current_qty": total_current_qty,
		"is_total": True,
		"currency":frappe.get_cached_value('Company',  filters.get('company'),  'default_currency')

	})

	return formatted_data

def convert_alternative_uom(data, filters):
	alternative_uom = filters.get('alternative_uom')
	
	for row in data:
		item_code = row.get('item_code')
		
		if item_code:
			conversion_factor = get_conversion_factor(item_code, alternative_uom)
			
			for key in ['qty']:
				if key in row:
						value = row[key]
						if isinstance(value, (int, float)):
							new_value = value / conversion_factor
							row[key] = new_value 
       
			for key in ['valuation_rate', 'rate']:
				if key in row:
					value = row[key]
					if isinstance(value, (int, float)):
						new_value = value * conversion_factor
						row[key] = new_value
	return data

def get_conversion_factor(item_code, alternative_uom):
	uom_conversion = frappe.db.get_value("UOM Conversion Detail", {"parent": item_code, "uom": alternative_uom}, "conversion_factor")
	return uom_conversion or 1

def currency_(data, filters):
	company = filters.get('company')
	currency = frappe.db.get_value("Company", company, "default_currency")
	for row in data:
		row['currency'] = currency
	return data