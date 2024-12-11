// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Planning Process Manufacturing"] = {
    "filters": [
        {
            label: __("Production Plan"),
            fieldname: "production_plan",
            fieldtype: "Link",
            options: "Production Plan",
            // reqd: 1,  // Make it mandatory
        },
        {
            label: __("Sales Order"),
            fieldname: "sales_order",
            fieldtype: "Link",
            options: "Sales Order",
        },
        {
            label: __("Item Name (Finished Goods)"),
            fieldname: "finished_goods_item",
            fieldtype: "Link",
            options: "Item",
        },
		{
            label: __("Item Name (Insole)"),
            fieldname: "insole_item",
            fieldtype: "Link",
            options: "Item",
        },
        {
            label: __("From Date"),
            fieldname: "from_date",
            fieldtype: "Date",
        },
        {
            label: __("To Date"),
            fieldname: "to_date",
            fieldtype: "Date",
        }
    ]
};
