// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt


frappe.query_reports["Project Monthly Expense"] = $.extend({}, erpnext.financial_statements);

erpnext.utils.add_dimensions("Project Monthly Expense", 10);

frappe.query_reports["Project Monthly Expense"]["filters"].push({
	fieldname: "selected_view",
	label: __("Select View"),
	fieldtype: "Select",
	options: [
		{ value: "Report", label: __("Report View") },
		{ value: "Growth", label: __("Growth View") },
		{ value: "Margin", label: __("Margin View") },
	],
	default: "Report",
	reqd: 1,
    hidden: 1,
});

frappe.query_reports["Project Monthly Expense"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Project Monthly Expense"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Project Monthly Expense"].onload = function (report) {
    report.page.menu.find('[data-label="Financial"]').parent().remove();
    
    // Remove the Finance Book filter
    const financeBookFilter = report.get_filter("finance_book");
    if (financeBookFilter) {
        financeBookFilter.df.hidden = true;
        financeBookFilter.refresh();
    }
}