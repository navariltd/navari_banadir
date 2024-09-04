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

	# Fetch columns using the get_columns function
	columns = get_columns(filters)
	
	data = fetch_data(filters)
	data=convert_to_presentation_currency(filters, data)
	return columns, data

def get_columns(filters):
	presentation_currency=filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	columns = []

	start_date = getdate(filters.get("from_date"))
	end_date = getdate(filters.get("to_date"))

	current_date = start_date
	while current_date <= end_date:
		# Format the date to get the month and year (e.g., "Aug 2024")
		month_name = formatdate(current_date, "MMM yyyy")
		columns.append({
			"label": f"{month_name} <strong>({presentation_currency})</strong>",
			"fieldname": month_name.lower().replace(" ", "_") + "_usd",
			"fieldtype": "Float",
			'precision':2,
			"width": 120
		})
		# Move to the next month
		current_date += relativedelta(months=1)
	columns += [
	{"label": f"<strong>Total Amount ({presentation_currency})</strong>", "fieldname": "total_amount_usd", "fieldtype": "Float","precision":2, "width": 120},
	]
	
	return columns

def fetch_data(filters):
	data = []
	start_date = getdate(filters.get("from_date"))
	end_date = getdate(filters.get("to_date"))
	company=filters.get("company")
	presentation_currency=filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)

	# Dictionary to store monthly sums of debit amounts
	monthly_totals = {}
	total_debit = 0  # Variable to track the total debit amount

	# Initialize the current_date to the start_date
	current_date = start_date

	while current_date <= end_date:
		month_start = current_date.replace(day=1)
		next_month_start = add_months(month_start, 1)
		# Query to sum the debit amounts for the current month
		month_name = formatdate(month_start, "MMM yyyy")
		debit_sum = frappe.db.sql("""
		SELECT COALESCE(SUM(debit), 0) FROM `tabGL Entry`
		WHERE company=%s AND posting_date >= %s AND posting_date < %s
		""", (company, month_start, next_month_start))

		# Calculate the sum and handle cases where no data is returned
		monthly_debit = debit_sum[0][0] if debit_sum and debit_sum[0][0] else 0
		monthly_totals[month_name] = monthly_debit

		total_debit += monthly_debit
		current_date = next_month_start

	# Create a single data row with the monthly sums and total
	row = {}
	for month, total in monthly_totals.items():
		key = month.lower().replace(" ", "_") + "_usd"
		row[key] = total

	# Add the total column at the end
	row["total_amount_usd"] = total_debit

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
			if field.endswith("_usd"):				
				entry[field] = convert(entry.get(field, 0), presentation_currency, company_currency, to_date)

	return data
