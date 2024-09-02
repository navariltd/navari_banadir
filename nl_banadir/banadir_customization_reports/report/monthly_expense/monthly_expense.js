// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Expense"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"width": "100px",
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"from_account",
			"label": __("From Account"),
			"fieldtype": "Link",
			"options": "Account",
			"reqd": 0,
			"width": "100px"
		},
		{
			"fieldname":"to_account",
			"label": __("To Account"),
			"fieldtype": "Link",
			"options": "Account",
			"reqd": 0,
			"width": "100px"
		},
		{
			"fieldname":"cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"reqd": 0,
			"width": "100px"
		},
		{
			"fieldname":"show_zero_values",
			"label": __("Show Zero Values"),
			"fieldtype": "Check",
			"default": 0,
			"reqd": 0
		}
	]
};