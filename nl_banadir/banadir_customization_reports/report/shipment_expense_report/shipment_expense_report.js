// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Shipment Expense Report"] = {
	"filters": [
        {
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			// default: frappe.defaults.get_user_default("Company"),
			// reqd: 1,
		},
        {
            fieldname: "currency",
            label: __("Currency"),
            fieldtype: "Link",
            options: "Currency",
        },
        {
            fieldname: "sales_invoice",
            label: __("Sales Invoice"),
            fieldtype: "Link",
            options: "Sales Invoice",
        }
	],
    "formatter": function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Check if the row is a total row
        if (data && data.is_total) {
            value = `<b>${value}</b>`;
        }

        return value;
    }
};
