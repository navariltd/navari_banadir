# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe

from frappe.utils import getdate, add_months, formatdate
from dateutil.relativedelta import relativedelta
from erpnext.accounts.report.utils import convert

def execute(filters=None):
	# If filters are not provided, initialize them as an empty dictionary
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data = fetch_data(filters)
	data = convert_to_presentation_currency(filters, data)
	return columns, data

def get_columns(filters):
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	columns = [
		{
			"label": "Account",
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		}
	]

	start_date = getdate(filters.get("from_date"))
	end_date = getdate(filters.get("to_date"))

	current_date = start_date
	while current_date <= end_date:
		month_name = formatdate(current_date, "MMM yyyy")
		columns.append({
			"label": f"{month_name} <strong>({presentation_currency})</strong>",
			"fieldname": month_name.lower().replace(" ", "_") + "_currency",
			"fieldtype": "Float",
			'precision': 2,
			"width": 120
		})
		# Move to the next month
		current_date += relativedelta(months=1)
	columns += [
		{"label": f"<strong>Total Difference ({presentation_currency})</strong>", "fieldname": "total_difference_currency", "fieldtype": "Float", "precision": 2, "width": 120},
	]
	
	return columns

def fetch_data(filters):
	"""Main function to fetch data based on filters."""
	start_date = getdate(filters.get("from_date"))
	end_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	account_filter = filters.get("account")

	# Fetching monthly differences for both debit and credit
	account_monthly_differences, total_differences = calculate_differences_by_month(
		start_date, end_date, company, account_filter
	)

	# Prepare the final data rows
	data = prepare_final_data(account_monthly_differences, total_differences)

	return data


def calculate_differences_by_month(start_date, end_date, company, account_filter):
	"""Calculates monthly differences (Debit - Credit) for each account."""
	current_date = start_date
	account_monthly_differences = {}
	total_differences = {}

	while current_date <= end_date:
		month_start = current_date.replace(day=1)
		next_month_start = add_months(month_start, 1)
		month_name = formatdate(month_start, "MMM yyyy")

		# Fetch debit and credit sums for the current month
		monthly_sums = fetch_monthly_sums(company, month_start, next_month_start, account_filter)

		# Update differences
		for entry in monthly_sums:
			account = entry["account"]
			monthly_difference = entry["monthly_debit"] - entry["monthly_credit"]

			if account not in account_monthly_differences:
				account_monthly_differences[account] = {}
				total_differences[account] = 0

			account_monthly_differences[account][month_name] = monthly_difference
			total_differences[account] += monthly_difference

		current_date = next_month_start

	return account_monthly_differences, total_differences

from frappe.query_builder import DocType, functions as fn
from pypika.terms import Criterion

def fetch_monthly_sums(company, month_start, next_month_start, account_filter):
    # Define the relevant DocTypes
    GL_Entry = DocType('GL Entry')
    Account = DocType('Account')

    # Build the base query using Query Builder
    query = (
        frappe.qb.from_(GL_Entry)
        .join(Account)
        .on(GL_Entry.account == Account.name)
        .select(
            GL_Entry.account,
            fn.Coalesce(fn.Sum(GL_Entry.debit), 0).as_('monthly_debit'),
            fn.Coalesce(fn.Sum(GL_Entry.credit), 0).as_('monthly_credit')
        )
        .where(
            (GL_Entry.company == company)
            & (GL_Entry.posting_date >= month_start)
            & (GL_Entry.posting_date < next_month_start)
            & (Account.root_type == 'Expense')
        )
        .groupby(GL_Entry.account)
    )

    # Add account filter if provided
    if account_filter:
        query = query.where(GL_Entry.account == account_filter)

    # Execute the query and return the results
    return query.run(as_dict=True)


def prepare_final_data(account_monthly_differences, total_differences):
	"""Prepares the final data to be returned."""
	data = []
	for account, monthly_differences in account_monthly_differences.items():
		row = {"account": account}
		for month, difference in monthly_differences.items():
			key = month.lower().replace(" ", "_") + "_currency"
			row[key] = difference
		row["total_difference_currency"] = total_differences[account]
		data.append(row)

	return data
#
def convert_to_presentation_currency(filters, data):
	company = filters.get("company")
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	company_currency = frappe.get_cached_value('Company', company, 'default_currency')
	to_date = getdate(filters.get("to_date"))
	for entry in data:
		for field in entry.keys():
			if field.endswith("_currency"):
				entry[field] = convert(entry.get(field, 0), presentation_currency, company_currency, to_date)

	return data
