# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe

from frappe.utils import getdate, add_months, formatdate
from dateutil.relativedelta import relativedelta
from erpnext.accounts.report.utils import convert, get_rate_as_at


def execute(filters=None):
	# If filters are not provided, initialize them as an empty dictionary
	if not filters:
		filters = {}

	columns = get_columns(filters)
	
	data = fetch_data(filters)
	data=convert_to_presentation_currency(filters, data)
	return columns, data

def get_columns(filters):
	presentation_currency=filters.get("presentation_currency") or frappe.get_cached_value(
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
		# Format the date to get the month and year (e.g., "Aug 2024")
		month_name = formatdate(current_date, "MMM yyyy")
		columns.append({
			"label": f"{month_name} <strong>({presentation_currency})</strong>",
			"fieldname": month_name.lower().replace(" ", "_") + "_currency",
			"fieldtype": "Float",
			'precision':2,
			"width": 120
		})
		# Move to the next month
		current_date += relativedelta(months=1)
	columns += [
	{"label": f"<strong>Total Amount ({presentation_currency})</strong>", "fieldname": "total_amount_currency", "fieldtype": "Float","precision":2, "width": 120},
	]
	
	return columns

def fetch_data(filters):
    """Main function to fetch data based on filters."""
    start_date = getdate(filters.get("from_date"))
    end_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    account_filter = filters.get("account")

    account_monthly_totals, total_debits = calculate_totals_by_month(
        start_date, end_date, company, account_filter
    )

    # Prepare the final data rows
    data = prepare_final_data(account_monthly_totals, total_debits)

    return data


def calculate_totals_by_month(start_date, end_date, company, account_filter):
    """Calculates monthly totals for each account."""
    current_date = start_date
    account_monthly_totals = {}
    total_debits = {}

    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        next_month_start = add_months(month_start, 1)
        month_name = formatdate(month_start, "MMM yyyy")

        # Fetch debit sums for the current month
        debit_sums = fetch_monthly_debits(company, month_start, next_month_start, account_filter)

        # Update totals
        for entry in debit_sums:
            account = entry["account"]
            monthly_debit = entry["monthly_debit"]

            if account not in account_monthly_totals:
                account_monthly_totals[account] = {}
                total_debits[account] = 0

            account_monthly_totals[account][month_name] = monthly_debit
            total_debits[account] += monthly_debit

        current_date = next_month_start

    return account_monthly_totals, total_debits


def fetch_monthly_debits(company, month_start, next_month_start, account_filter):
    """Fetches monthly debit sums for the given month and account filter."""
    # Build query based on the account filter
    query = """
        SELECT account, COALESCE(SUM(debit), 0) as monthly_debit
        FROM `tabGL Entry`
        WHERE company=%s AND posting_date >= %s AND posting_date < %s
    """
    query_params = [company, month_start, next_month_start]

    # Apply account filter if it exists
    if account_filter:
        query += " AND account = %s"
        query_params.append(account_filter)

    query += " GROUP BY account"

    # Execute query and return results
    return frappe.db.sql(query, query_params, as_dict=True)


def prepare_final_data(account_monthly_totals, total_debits):
    """Prepares the final data to be returned."""
    data = []
    for account, monthly_totals in account_monthly_totals.items():
        row = {"account": account}
        for month, total in monthly_totals.items():
            key = month.lower().replace(" ", "_") + "_currency"
            row[key] = total
        row["total_amount_currency"] = total_debits[account]
        data.append(row)

    return data


def convert_to_presentation_currency(filters, data):
	company=filters.get("company")
	presentation_currency=presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	company_currency=frappe.get_cached_value('Company',company, 'default_currency')
	to_date = getdate(filters.get("to_date"))
	for entry in data:
		for field in entry.keys():
			if field.endswith("_currency"):				
				entry[field] = convert(entry.get(field, 0), presentation_currency, company_currency, to_date)

	return data
