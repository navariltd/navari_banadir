// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Intercompany Journal Comparison By Amount"] = {
  filters: [
    {
      fieldname: "reference_company",
      label: __("Reference Company"),
      fieldtype: "Link",
      width: "80",
      options: "Company",
      reqd: 1,
    },
    {
      fieldname: "party_type",
      label: __("Party Type"),
      fieldtype: "Autocomplete",
      options: "Customer\nSupplier",
      on_change: function () {
        frappe.query_report.set_filter_value("party", "");
      },
    },
    {
      fieldname: "party",
      label: __("Party"),
      fieldtype: "MultiSelectList",
      get_data: function (txt) {
        if (!frappe.query_report.filters) return;

        let party_type = frappe.query_report.get_filter_value("party_type");
        if (!party_type) return;

        return frappe.db.get_link_options(party_type, txt);
      },
      on_change: function () {
        var party_type = frappe.query_report.get_filter_value("party_type");
        var parties = frappe.query_report.get_filter_value("party");

        if (!party_type || parties.length === 0 || parties.length > 1) {
          frappe.query_report.set_filter_value("party_name", "");
          frappe.query_report.set_filter_value("tax_id", "");
          return;
        } else {
          var party = parties[0];
          var fieldname = erpnext.utils.get_party_name(party_type) || "name";
          frappe.db.get_value(party_type, party, fieldname, function (value) {
            frappe.query_report.set_filter_value(
              "party_name",
              value[fieldname]
            );
          });

          if (party_type === "Customer" || party_type === "Supplier") {
            frappe.db.get_value(party_type, party, "tax_id", function (value) {
              frappe.query_report.set_filter_value("tax_id", value["tax_id"]);
            });
          }
        }
      },
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
    // {
    //   fieldname: "journal",
    //   label: __("Journal"),
    //   fieldtype: "Link",
    //   options: "Journal Entry",
    //   get_query: function () {
    //     return {
    //       filters: {
    //         voucher_type: "Inter Company Journal Entry",
    //       },
    //     };
    //   },
    // },
    {
      fieldname: "compare_by_amount",
      label: __("Compare By Amount"),
      fieldtype: "Check",
      default: 0,
      // on_change: function () {
      //   frappe.query_report.set_filter_value("compare_randomly", 0);
      // },
    },
    {
      fieldname: "compare_randomly",
      label: __("Compare Randomly"),
      fieldtype: "Check",
      default: 0,
      // on_change: function () {
      //   frappe.query_report.set_filter_value("compare_by_amount", 0);
      // },
    },
  ],
};
