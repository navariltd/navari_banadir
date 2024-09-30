// Copyright (c) 2024, Navari Ltd and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Expense"] = {
"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"width": "100px",
			"reqd": 1
		},
		{
			"fieldname":"from_date",
			"label": __("Start Date"),
			"fieldtype": "Date",
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[1],
			"reqd": 1,
			"width": "100px"
		},
		{
			"fieldname":"to_date",
			"label": __("End Date"),
			"fieldtype": "Date",
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), true)[2],
			"reqd": 1,
			"width": "100px"
		},
		{
				"fieldname":"account",
				"label": __("Account"),
				"fieldtype": "Link",
				"options": "Account",
				get_query: () => {
					var company = frappe.query_report.get_filter_value("company");
					return {
					  filters: {
						company: company,
						is_group: 0,
					  },
					};
				  },
		},
		
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
			width: "80px",
			
		},
		{
			fieldname:"parent_accounts",
			label: __("Parent Accounts"),
			fieldtype: "Check",
			default: 0,
			reqd: 0,
		},
		
		{
			"fieldname":"show_zero_values",
			"label": __("Show Zero Values"),
			"fieldtype": "Check",
			"default": 0,
			"reqd": 0
		}
	]
};

