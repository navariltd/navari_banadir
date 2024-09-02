// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Total Stock Balance Summary"] = {
    filters: [
        {
            fieldname: "group_by",
            label: __("Group By"),
            fieldtype: "Select",
            width: "80",
            reqd: 1,
            options: ["Company"],
            default: "Company",
            hidden: 1  // Hides the filter from the UI
        },
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            width: "80",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
            depends_on: "eval: doc.group_by == 'Company'",
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            width: "80",
            options: "Item Group",
            reqd: 0,
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "Link",
            width: "80",
            options: "Warehouse",
            reqd: 0,
        },
        {
            fieldname: "current_date",
            label: __("Current Date"),
            fieldtype: "Date",
            default: frappe.datetime.now_date(),
            reqd: 0,
            on_change: function() {
                // Get the value of the current_date
                var currentDate = frappe.query_report.get_filter_value('current_date');
                if (currentDate) {
                    var nextDay = frappe.datetime.add_days(currentDate, 1);
                    frappe.query_report.set_filter_value('filter_date', nextDay);
                }
            }
        },
        {
            fieldname: "filter_date",
            label: __("Filter Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.now_date(), 1),  // Sets to one day ahead
            hidden: 1,
            reqd: 0,
        },
        {
            fieldname: "alternative_uom",
            label: __("Alternative UOM"),
            fieldtype: "Link",
            options: "UOM",
            width: "100",
            reqd: 0,
        },
    ],
};
