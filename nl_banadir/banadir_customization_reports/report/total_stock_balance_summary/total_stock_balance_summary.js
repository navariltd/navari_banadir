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
			fieldname: "current_date",
			label: __("Current Date"),
			fieldtype: "Date",
			default: frappe.datetime.now_date(),
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
