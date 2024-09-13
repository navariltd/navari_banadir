// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Project Summary Report"] = {
	"filters": [
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project",
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
        },
        {
            "fieldname": "purchased_only",
            "label": __("Purchased Only"),
            "fieldtype": "Check",
            "default": 0
        }
	]
};
