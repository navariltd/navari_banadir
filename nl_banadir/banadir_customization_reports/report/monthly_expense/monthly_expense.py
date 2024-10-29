
import frappe
from frappe.utils import getdate, add_months, formatdate
from dateutil.relativedelta import relativedelta
from erpnext.accounts.report.utils import convert
from frappe.query_builder import DocType, functions as fn
# from nl_banadir.nl_banadir.banadir_customization_reports.report.utils import convert_to_party_currency, convert_currency_columns

def execute(filters=None):
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
		},
   {
		"label": "Parent Account",
		"fieldname": "parent_account",
		"fieldtype": "Link",
		"options": "Account",
	 },
   {
		"label":"Currency",
		"fieldname":"currency",
		"fieldtype":"Link",
		"options":"Currency",
  "hidden":1,
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
			"fieldtype": "Currency",
			'precision': 2,
			'options':"currency",
			"width": 120
		})
		current_date += relativedelta(months=1)
	columns += [
		{"label": f"<strong>Total ({presentation_currency})</strong>", "fieldname": "total_difference_currency", "fieldtype": "Float", "precision": 2, "width": 120},
	]

	return columns

def fetch_data(filters):
	start_date = getdate(filters.get("from_date"))
	end_date = getdate(filters.get("to_date"))
	company = filters.get("company")
	account_filter = filters.get("account")
	hide_account_filter=filters.get("hide_account")
	hide_parent_account_filter = filters.get('hide_parent_account')
	
	show_parent_accounts = filters.get("parent_accounts")
	currency= filters.get("currency") or frappe.get_cached_value("Company", company, "default_currency")

	# Fetch monthly differences for both debit and credit
	account_monthly_differences, total_differences = calculate_differences_by_month(
		start_date, end_date, company, account_filter, hide_account_filter, hide_parent_account_filter
	)

	if show_parent_accounts:
		# Fetch parent-child relationships and aggregate data for parent accounts
		data = aggregate_parent_accounts(account_monthly_differences, total_differences, company)
	else:
		data = prepare_final_data(account_monthly_differences, total_differences, filters)
	return data

def calculate_differences_by_month(start_date, end_date, company, account_filter, hide_account_filter, hide_parent_account_filter):
	current_date = start_date
	account_monthly_differences = {}
	total_differences = {}

	while current_date <= end_date:
		month_start = current_date.replace(day=1)
		next_month_start = add_months(month_start, 1)
		month_name = formatdate(month_start, "MMM yyyy")

		monthly_sums = fetch_monthly_sums(company, month_start, next_month_start, account_filter, hide_account_filter, hide_parent_account_filter)
		for entry in monthly_sums:
			account = entry["account"]
			parent_account = entry.get("parent_account")  
			monthly_difference = entry["monthly_debit"] - entry["monthly_credit"]

			# Initialize the account entry in the dictionary if it does not exist
			if account not in account_monthly_differences:
				account_monthly_differences[account] = {"parent_account": parent_account}  
				total_differences[account] = 0

			account_monthly_differences[account][month_name] = monthly_difference
			total_differences[account] += monthly_difference

		current_date = next_month_start
	return account_monthly_differences, total_differences

def fetch_monthly_sums(company, month_start, next_month_start, account_filter, hide_account, hide_parent_account):
	GL_Entry = DocType('GL Entry')
	Account = DocType('Account')

	query = (
		frappe.qb.from_(GL_Entry)
		.join(Account)
		.on(GL_Entry.account == Account.name)
		.select(
			GL_Entry.account,
			Account.parent_account.as_('parent_account'),
			fn.Coalesce(fn.Sum(GL_Entry.debit), 0).as_('monthly_debit'),
			fn.Coalesce(fn.Sum(GL_Entry.credit), 0).as_('monthly_credit')
		)
		.where(
			(GL_Entry.company == company)
			& (GL_Entry.posting_date >= month_start)
			& (GL_Entry.posting_date < next_month_start)
			& (Account.root_type == 'Expense')
			& (~Account.parent_account.like(f'Stock Expenses%'))
			& (~Account.parent_account.like(f'{hide_parent_account}'))
			& (~Account.name.like(f'{hide_account}'))
		)
		.groupby(GL_Entry.account)
	)

	if account_filter:
		query = query.where(GL_Entry.account == account_filter)

	data=query.run(as_dict=True)
	return data

def prepare_final_data(account_monthly_differences, total_differences, filters):
	data = []
	for account, monthly_differences in account_monthly_differences.items():
		row = {"account": account,
		 							"parent_account": monthly_differences.get("parent_account", ""),  # Include parent_account
          "currency": filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
}
		for month, difference in monthly_differences.items():
			key = month.lower().replace(" ", "_") + "_currency"
			row[key] = difference
		row["total_difference_currency"] = total_differences[account]
		data.append(row)
	return data

def aggregate_parent_accounts(account_monthly_differences, total_differences, company):
	for account, data in account_monthly_differences.items():
		if 'parent_account' in data:
			del data['parent_account']
	accounts = list(account_monthly_differences.keys()) 
	parent_child_map = frappe.get_all(
		"Account", 
		filters={"name": ["in", accounts], "company": company},
		fields=["name", "parent_account", "is_group"],
		as_list=True
	)
	
	# Convert fetched data into a dictionary
	parent_child_dict = {acc[0]: acc[1:] for acc in parent_child_map}
	
	parent_monthly_differences = {}
	parent_total_differences = {}

	for account, monthly_differences in account_monthly_differences.items():
		parent_account, is_group = parent_child_dict.get(account, (None, 0))

		if parent_account and not is_group:
			if parent_account not in parent_monthly_differences:
				parent_monthly_differences[parent_account] = {}
				parent_total_differences[parent_account] = 0

			for month, difference in monthly_differences.items():
				if month not in parent_monthly_differences[parent_account]:
					parent_monthly_differences[parent_account][month] = 0
				parent_monthly_differences[parent_account][month] += difference
				parent_total_differences[parent_account] += difference

	# Convert the aggregated parent account data into the final format
	aggregated_data = []
	for parent_account, monthly_differences in parent_monthly_differences.items():
		row = {"account": parent_account}
		for month, difference in monthly_differences.items():
			key = month.lower().replace(" ", "_") + "_currency"
			row[key] = difference
		row["total_difference_currency"] = parent_total_differences[parent_account]
		aggregated_data.append(row)

	return aggregated_data


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
