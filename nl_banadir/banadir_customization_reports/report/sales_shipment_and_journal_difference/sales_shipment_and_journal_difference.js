// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Shipment and Journal Difference"] = {
	filters: [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
			"reqd": 1,
		},
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
        },
        {
            "fieldname": "currency",
            "label": __("Currency"),
            "fieldtype": "Link",
            "options": "Currency",
        },
        {
            "fieldname": "journal_entry",
            "label": __("Journal Entry"),
            "fieldtype": "Link",
            "options": "Journal Entry",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value("company")
                    }
                }
            }
        },
        {
            "fieldname": "sales_invoice",
            "label": __("Sales Invoice"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value("company")
                    }
                }
            }
        },
        {
            "fieldname": "sales_shipment",
            "label": __("Sales Shipment"),
            "fieldtype": "Link",
            "options": "Sales Shipment Cost",
            "get_query": function() {
                return {
                    "filters": {
                        "company": frappe.query_report.get_filter_value("company")
                    }
                }
            }
        }
	],
};
