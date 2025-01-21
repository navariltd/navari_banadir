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
            "label": __("Transit Number"),
            "fieldtype": "Link",
            "options": "Sales Invoice",
        },
        {
            "fieldname": "alternative_uom",
            "label": __("Alternative UOM"),
            "fieldtype": "Link",
            "options": "UOM",
        },
        {
            "fieldname": "container_no",
            "label": __("Container No"),
            "fieldtype": "Check",
        }
	],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (data && data.is_total_row) {
          value = `<b>${value}</b>`;
        }
        return value;
      },
};
