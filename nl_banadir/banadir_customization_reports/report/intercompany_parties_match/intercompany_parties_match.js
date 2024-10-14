// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Intercompany Parties Match"] = {
  filters: [
    {
      fieldname: "from_company",
      label: __("From Company"),
      fieldtype: "Link",
      width: "80",
      options: "Company",
      reqd: 1,
      //   default: frappe.defaults.get_default("company"),
    },
    {
      fieldname: "to_company",
      label: __("To Company"),
      fieldtype: "Link",
      width: "80",
      options: "Company",
      //   default: frappe.defaults.get_default("company"),
    },
    {
      fieldname: "from_date",
      label: __("From Date"),
      fieldtype: "Date",
      width: "80",
      reqd: 1,
      default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
    },
    {
      fieldname: "to_date",
      label: __("To Date"),
      fieldtype: "Date",
      width: "80",
      reqd: 1,
      default: frappe.datetime.get_today(),
    },
    {
      fieldname: "journal",
      label: __("Journal"),
      fieldtype: "Link",
      options: "Journal Entry",
      get_query: function () {
        return {
          filters: {
            voucher_type: "Inter Company Journal Entry",
          },
        };
      },
    },
  ],
};
