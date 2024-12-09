// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance Summary"] = {
  filters: [
    {
      fieldname: "company",
      label: __("Company"),
      fieldtype: "Link",
      width: "80",
      options: "Company",
      default: frappe.defaults.get_default("company"),
      reqd: 1,
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
      fieldname: "item_group",
      label: __("Item Group"),
      fieldtype: "Link",
      width: "80",
      options: "Item Group",
    },
    {
      fieldname: "item_code",
      label: __("Item"),
      fieldtype: "Link",
      width: "80",
      options: "Item",
      hidden: 1,
      get_query: function () {
        return {
          query: "erpnext.controllers.queries.item_query",
        };
      },
    },
    {
      fieldname: "warehouse",
      label: __("Warehouse"),
      fieldtype: "Link",
      width: "80",
      options: "Warehouse",
      get_query: () => {
        let warehouse_type =
          frappe.query_report.get_filter_value("warehouse_type");
        let company = frappe.query_report.get_filter_value("company");

        return {
          filters: {
            ...(warehouse_type && { warehouse_type }),
            ...(company && { company }),
          },
        };
      },
    },
    {
      fieldname: "warehouse_type",
      label: __("Warehouse Type"),
      fieldtype: "Link",
      width: "80",
      options: "Warehouse Type",
      hidden: 1,
    },
    {
      fieldname: "valuation_field_type",
      label: __("Valuation Field Type"),
      fieldtype: "Select",
      width: "80",
      options: "Currency\nFloat",
      default: "Currency",
      hidden: 1,
    },
    {
      fieldname: "include_uom",
      label: __("Include UOM"),
      fieldtype: "Link",
      options: "UOM",
    },
    {
      fieldname: "show_variant_attributes",
      label: __("Show Variant Attributes"),
      fieldtype: "Check",
      hidden: 1,
    },
    {
      fieldname: "show_stock_ageing_data",
      label: __("Show Stock Ageing Data"),
      fieldtype: "Check",
      hidden: 1,
    },
    {
      fieldname: "ignore_closing_balance",
      label: __("Ignore Closing Balance"),
      fieldtype: "Check",
      default: 0,
      hidden: 1,
    },
    {
      fieldname: "remove_precision",
      label: __("Remove Precision"),
      fieldtype: "Check",
      default: 0,
    },
    {
      fieldname: "show_warehouse_totals",
      label: __("Show Warehouse Totals"),
      fieldtype: "Check",
      default: 0,
    },
  ],

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    if (data && data.is_total) {
      value = `<b>${value}</b>`;

    // Check if "remove_precision" filter is set to 1
    const remove_precision = frappe.query_report.get_filter_value("remove_precision");

    if (remove_precision === 1 && data && data.bal_qty > 0) {
        // Check if the column fieldname contains 'bal_qty'
        if (column.fieldname.includes("bal_qty")) {
            // Split the value into integer and decimal parts
            let [integerPart, decimalPart] = value.toString().split(".");
            // Add comma formatting to the integer part only
            integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            // Recombine integer and decimal parts
            value = decimalPart ? `${integerPart}.${decimalPart}` : integerPart;
        }

    }

    if (column.fieldname == "out_qty" && data && data.out_qty > 0) {
        value = "<span style='color:red'>" + value + "</span>";
    } else if (column.fieldname == "in_qty" && data && data.in_qty > 0) {
        value = "<span style='color:green'>" + value + "</span>";
    }

    return value;
},

};

erpnext.utils.add_inventory_dimensions("Stock Balance", 8);
