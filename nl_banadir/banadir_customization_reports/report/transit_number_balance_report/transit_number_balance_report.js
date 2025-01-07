// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Transit Number Balance Report"] = {
	filters: [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1,
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
        },
        {
            "fieldname": "sales_invoice",
            "label": __("Sales Invoice"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
        },
	],
};
