// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt


frappe.query_reports["Expense Report"] = {
	"filters": [
		// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		// {
		// 	fieldname: "finance_book",
		// 	label: __("Finance Book"),
		// 	fieldtype: "Link",
		// 	options: "Finance Book",
		// },
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year", "Date Range"],
			default: ["Fiscal Year"],
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display(
					"from_fiscal_year",
					filter_based_on === "Date Range"
				);
				frappe.query_report.toggle_filter_display("to_fiscal_year", filter_based_on === "Date Range");
				frappe.query_report.toggle_filter_display(
					"period_start_date",
					filter_based_on === "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"period_end_date",
					filter_based_on === "Fiscal Year"
				);

				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				{ value: "Quarterly", label: __("Quarterly") },
				{ value: "Half-Yearly", label: __("Half-Yearly") },
				{ value: "Yearly", label: __("Yearly") },
			],
			default: "Yearly",
			reqd: 1,
		},
		
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Cost Center", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
		{
			fieldname: "project",
			label: __("Project"),
			fieldtype: "MultiSelectList",
			get_data: function (txt) {
				return frappe.db.get_link_options("Project", txt, {
					company: frappe.query_report.get_filter_value("company"),
				});
			},
		},
	
	]};

erpnext.utils.add_dimensions("Expense Report", 10);

// frappe.query_reports["Expense Report"]["filters"].push({
// 	fieldname: "selected_view",
// 	label: __("Select View"),
// 	fieldtype: "Select",
// 	options: [
// 		{ value: "Report", label: __("Report View") },
// 		{ value: "Growth", label: __("Growth View") },
// 		{ value: "Margin", label: __("Margin View") },
// 	],
// 	default: "Report",
// 	reqd: 1,
//     read_only: 1,
// });

frappe.query_reports["Expense Report"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
    hidden: 1,
});

frappe.query_reports["Expense Report"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
    hidden: 1,
});
