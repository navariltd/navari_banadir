# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from pypika import Criterion, Case

def execute(filters=None):
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"));
	return get_columns(), get_data(filters);

def get_columns():
	return [
		{
			'fieldname': 'account',
			'label': _('Account'),
			'fieldtype': 'Link',
			'options': 'Account',
			'width': 240
		},
		{
			'fieldname': 'cost_center',
			'label': _('Cost Center'),
			'fieldtype': 'Link',
			'options': 'Cost Center',
			'width': 180
		},
		{
			'fieldname': 'debit',
			'label': _('Debit'),
			'fieldtype': 'Currency',
			'width': 150
		},
		{
			'fieldname': 'credit',
			'label': _('Credit'),
			'fieldtype': 'Currency',
			'width': 140
		},
		{
			'fieldname': 'balance',
			'label': _('Balance'),
			'fieldtype': 'Currency',
			'width': 150
		}
	];

def get_data(filters):
	data = []
	company = filters.get('company')
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	from_account = filters.get('from_account')
	to_account = filters.get('to_account')
	cost_center = filters.get('cost_center')
	show_zero_values = filters.get('show_zero_values')

	root_account = from_account if from_account else frappe.db.get_all('Account', filters = { 'root_type': 'Expense', 'parent_account': '' }, pluck = 'name')[0];
	first_account_no = frappe.db.get_value('Account', root_account, 'account_number');
	last_account_no = frappe.db.get_value('Account', to_account, 'account_number') if to_account else None;
		
	def is_group(account_name):
		return frappe.db.get_value('Account', account_name, 'is_group');

	def get_list_of_account_names(list_of_fetched_account_names_starting_from_root):
		for account in list_of_fetched_account_names_starting_from_root:
			if is_group(account):
				insert_index = list_of_fetched_account_names_starting_from_root.index(account) + 1;
				child_accounts = None;
				if last_account_no:
					child_accounts = frappe.db.get_all('Account', 
						filters = { 'root_type': 'Expense', 'parent_account': account, 'account_number': ['<=', last_account_no] }, 
						or_filters = { 'root_type': 'Expense', 'parent_account': account, 'account_number': ['>=', first_account_no] },
						pluck = 'name'
					);
				else:
					child_accounts = frappe.db.get_all('Account', 
						filters = { 'root_type': 'Expense', 'parent_account': account, 'account_number': ['>=', first_account_no] }, 
						pluck = 'name'
					);
				list_of_fetched_account_names_starting_from_root[ insert_index:insert_index ] = child_accounts;

		return list_of_fetched_account_names_starting_from_root;

	list_of_account_names = get_list_of_account_names([root_account]);

	def append_accounts(account_name, indent, from_date, to_date):
		gl_entry = frappe.qb.DocType("GL Entry");
		account = frappe.qb.DocType("Account");

		def get_conditions():
			conditions = [gl_entry.docstatus == 1];

			if company:
				conditions.append(gl_entry.company == company);
			if cost_center:
				conditions.append(gl_entry.cost_center == cost_center);
		
			return conditions;

		conditions = get_conditions();
		conditions.append(gl_entry.account.like(f'{account_name}%'))
		conditions.append(gl_entry.posting_date[from_date:to_date])

		if is_group(account_name):
			parent = None if indent == 0 else frappe.db.get_value('Account', account_name, 'parent_account');

			data.append({ 'account': account_name, 'indent': indent, 'parent': parent, 'debit': 0, 'credit': 0, 'balance': 0 });
		else:
			sum_credit_in_account_currency = frappe.qb.functions("SUM", gl_entry.credit_in_account_currency).as_("credit")
			sum_debit_in_account_currency = frappe.qb.functions("SUM", gl_entry.debit_in_account_currency).as_("debit")
			sum_balance = frappe.qb.functions("SUM", gl_entry.debit_in_account_currency - gl_entry.credit_in_account_currency).as_("balance")

			query = frappe.qb.from_(gl_entry)\
				.inner_join(account)\
				.on(gl_entry.account == account.name)\
				.select(
					Case()
					.when(gl_entry.account.isnull(), account_name)
					.else_(gl_entry.account)
					.as_("account"),
					sum_credit_in_account_currency,
					sum_debit_in_account_currency,
					sum_balance,
					gl_entry.cost_center.as_("cost_center"),
					account.parent_account.as_("parent")
				).where(Criterion.all(conditions))
			
			gl_entry_record = query.run(as_dict=True);

			if gl_entry_record:
				gl_entry_record = gl_entry_record[0];
				gl_entry_record['indent'] = indent;
				
				data.append(gl_entry_record);

				# fill credit, debit and balance for all parent accounts on the tree.
				if indent > 0:
					child_row = gl_entry_record;
					parent_account = child_row['parent'];

					while parent_account:
						totals_row = list(filter(lambda x: x['account'] == parent_account, data));

						if totals_row:
							totals_row = totals_row[0];
							totals_row['debit']	+= child_row['debit'];
							totals_row['credit'] += child_row['credit'];
							totals_row['balance'] += child_row['balance'];

							parent_account = totals_row['parent'];

	for account_name in list_of_account_names:
		parent_account = frappe.db.get_value('Account', account_name, 'parent_account');

		parent_row = list(filter(lambda x: x['account'] == parent_account, data));

		indent = (parent_row[0]['indent']) + 1 if parent_row else 0;

		append_accounts(account_name, indent, from_date, to_date);

	if not show_zero_values:
		data = list(filter(lambda x: x['balance'], data));
	
	return data;

	