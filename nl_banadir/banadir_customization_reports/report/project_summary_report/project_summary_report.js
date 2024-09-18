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
            "reqd": 1,
        },
        {
            "fieldname": "task",
            "label": __("Task"),
            "fieldtype": "Link",
            "options": "Task",
        },
        {
            "fieldname": "currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
        },
        {
            "fieldname": "purchased_only",
            "label": __("Purchased Only"),
            "fieldtype": "Check",
            "default": 0
        },
        {
            "fieldname": "task_status",
            "label": __("Task Status"),
            "fieldtype": "Check",
            "default": 0
        }
	]
};
