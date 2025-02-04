// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Warehouse To Warehouse"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "from_warehouse",
			"label": "From Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname": "to_warehouse",
			"label": "To Warehouse",
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname": "company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "item_code",
			"label": "Item Code",
			"fieldtype": "Link",
			"options": "Item"

		},
		{
			"fieldname": "alternative_uom",
			"label": "Alternative UOM",
			"fieldtype": "Link",
			"options": "UOM"
			
		}
	]
};
