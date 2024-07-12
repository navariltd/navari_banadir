# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

# import frappe


from nl_banadir.banadir_customization_reports.report.accounts_receivable_summary_multi_currency.accounts_receivable_summary_multi_currency import (
	AccountsReceivableSummary,
)


def execute(filters=None):
	args = {
		"account_type": "Payable",
		"naming_by": ["Buying Settings", "supp_master_name"],
	}
	return AccountsReceivableSummary(filters).run(args)