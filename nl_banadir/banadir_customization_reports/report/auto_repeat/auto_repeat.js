// Copyright (c) 2025, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Auto Repeat"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      options: "Company",
      reqd: 1,
    },
    {
      fieldname: "reference_doctype",
      label: __("Reference Document Type"),
      fieldtype: "Link",
      options: "DocType",
      reqd: 1,
      on_change: function () {
        frappe.query_report.set_filter_value("reference_document", null); // Clear previous value
      },
    },
    {
      fieldname: "reference_document",
      label: __("Reference Document"),
      fieldtype: "Dynamic Link",
      options: "reference_doctype",
      get_query: function () {
        const start_date = frappe.query_report.get_filter_value("start_date");
        const end_date = frappe.query_report.get_filter_value("end_date");

        return {
          filters: {
            docstatus: ["=", 1],
            // posting_date: ["between", [start_date, end_date]],
          },
        };
      },
    },
    {
      fieldname: "start_date",
      label: __("Start Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "end_date",
      label: __("End Date"),
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
  ],
};
