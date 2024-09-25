# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from pypika import Order

import erpnext
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import (
	add_sub_total_row,
	add_total_row,
	apply_group_by_conditions,
	get_grand_total,
	get_group_by_and_display_fields,
	get_tax_accounts,
)
from erpnext.accounts.report.utils import get_query_columns, get_values_for_columns, convert, get_rate_as_at

def get_current_exchange_rate(from_currency, to_currency, date):
	if to_currency in ["CDF","KES","TZS","UGX", "NGN","ETB","GNF", "SDG","XAF","AED"]:
		currency_exchanges=frappe.get_all("Currency Exchange", filters={"from_currency": from_currency, "to_currency": to_currency}, fields=["exchange_rate"])
		if currency_exchanges:
			return currency_exchanges[0].exchange_rate
	else:
		exchange_rate = get_rate_as_at(date, from_currency, to_currency)
		if exchange_rate==1 and from_currency!=to_currency:
			pass
		return exchange_rate

def convert_as_per_current_exchange_rate(data, filters, from_currency, to_currency):
	date = frappe.utils.today()
	for entry in data:
		# In dollars
		old_rate_in_usd = entry['rate'] / entry['exchange_rate']
		old_rate_plus_landed_cost_in_usd = entry['rate_plus_landed_cost'] / entry['exchange_rate']
		old_landed_cost=entry['landed_cost_voucher_amount'] / entry['exchange_rate']
  
		current_rate_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_rate_in_usd
		current_rate_plus_landed_cost_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_rate_plus_landed_cost_in_usd
		current_rate_in_usd = convert(current_rate_chosen_currency, "USD", to_currency, date)
		current_rate_plus_landed_cost_in_usd = convert(current_rate_plus_landed_cost_chosen_currency, "USD", to_currency, date)
		current_landed_cost_chosen_currency=get_current_exchange_rate(from_currency, to_currency, date) * old_landed_cost
		current_landed_cost_in_usd=convert(current_landed_cost_chosen_currency, "USD", to_currency, date)

		if filters.get('presentation_currency') == 'USD':
			entry['current_rate'] = current_rate_in_usd
			entry['current_rate_plus_landed_cost'] = current_rate_plus_landed_cost_in_usd
			entry['current_landed_cost'] = current_landed_cost_in_usd
		else:
			entry['current_rate'] = current_rate_chosen_currency
			entry['current_rate_plus_landed_cost'] = current_rate_plus_landed_cost_chosen_currency
			entry['current_landed_cost'] = current_landed_cost_chosen_currency
		
		# Calculate current_total
		old_total_in_usd = entry['amount'] / entry['exchange_rate']
		current_total_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_total_in_usd
		current_total_in_usd = convert(current_total_chosen_currency, "USD", to_currency, date)
		
		if filters.get('presentation_currency') == 'USD':
			entry['current_total'] = current_total_in_usd
		else:
			entry['current_total'] = current_total_chosen_currency
		entry['current_exchange_rate'] = get_current_exchange_rate(from_currency, to_currency, date)
	return data


def execute(filters=None):
	return _execute(filters)


def _execute(filters=None, additional_table_columns=None):
	if not filters:
		filters = {}
	columns = get_columns(additional_table_columns, filters)
	company_currency = erpnext.get_company_currency(filters.company)
	item_list = get_items(filters, additional_table_columns)
	aii_account_map = get_aii_accounts()
	presentation_currency= filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
	

	po_pr_map = get_purchase_receipts_against_purchase_order(item_list)

	data = []
	total_row_map = {}
	skip_total_row = 0
	prev_group_by_value = ""
	tax_columns=[]

	if filters.get("group_by"):
		grand_total = get_grand_total(filters, "Purchase Invoice")

	for d in item_list:
		purchase_receipt = None
		if d.purchase_receipt:
			purchase_receipt = d.purchase_receipt
		elif d.po_detail:
			purchase_receipt = ", ".join(po_pr_map.get(d.po_detail, []))

		expense_account = (
			d.unrealized_profit_loss_account or d.expense_account or aii_account_map.get(d.company)
		)
		row = {
			"item_code": d.item_code,
			"item_name": d.pi_item_name if d.pi_item_name else d.i_item_name,
			"item_group": d.pi_item_group if d.pi_item_group else d.i_item_group,
			"description": d.description,
			"invoice": d.parent,
			"posting_date": d.posting_date,
			"supplier": d.supplier,
			"supplier_name": d.supplier_name,
			**get_values_for_columns(additional_table_columns, d),
			"credit_to": d.credit_to,
			"mode_of_payment": d.mode_of_payment,
			"project": d.project,
			"company": d.company,
			"purchase_order": d.purchase_order,
			"purchase_receipt": purchase_receipt,
			"expense_account": expense_account,
			"stock_qty": d.stock_qty,
			"stock_uom": d.stock_uom,
			"rate": d.base_net_amount / d.stock_qty if d.stock_qty else d.base_net_amount,
			"amount": d.base_net_amount,
			"exchange_rate": d.conversion_rate if d.conversion_rate !=1 else get_current_exchange_rate("USD", company_currency, d.posting_date),
			"landed_cost_voucher_amount": flt(d.landed_cost_voucher_amount/ d.stock_qty),
		"rate_plus_landed_cost": flt(d.base_net_amount / d.stock_qty) + flt(d.landed_cost_voucher_amount / d.stock_qty),
			}


		if filters.get("group_by"):
			row.update({"percent_gt": flt(row["total"] / grand_total) * 100})
			group_by_field, subtotal_display_field = get_group_by_and_display_fields(filters)
			data, prev_group_by_value = add_total_row(
				data,
				filters,
				prev_group_by_value,
				d,
				total_row_map,
				group_by_field,
				subtotal_display_field,
				grand_total,
				tax_columns,
			)
			add_sub_total_row(row, total_row_map, d.get(group_by_field, ""), tax_columns)

		data.append(row)
	if filters.get("group_by") and item_list:
		total_row = total_row_map.get(prev_group_by_value or d.get("item_name"))
		total_row["percent_gt"] = flt(total_row["total"] / grand_total * 100)
		data.append(total_row)
		data.append({})
		add_sub_total_row(total_row, total_row_map, "total_row", tax_columns)
		data.append(total_row_map.get("total_row"))
		skip_total_row = 1
	data=convert_as_per_current_exchange_rate(data,filters, "USD", presentation_currency)
	data=convert_currency_fields(data, filters)
	return columns, data, None, None, None, skip_total_row


def get_columns(additional_table_columns, filters):
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
		"Company", filters.company, "default_currency"
	)
	columns = []
 

	if filters.get("group_by") != ("Item"):
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 120,
				},
				{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
			]
		)

	if filters.get("group_by") not in ("Item", "Item Group"):
		columns.extend(
			[
				{
					"label": _("Item Group"),
					"fieldname": "item_group",
					"fieldtype": "Link",
					"options": "Item Group",
					"width": 120,
				}
			]
		)

	columns.extend(
		[
			{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 150},
			{
				"label": _("Invoice"),
				"fieldname": "invoice",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"width": 120,
			},
			{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		]
	)

	if filters.get("group_by") != "Supplier":
		columns.extend(
			[
				{
					"label": _("Supplier"),
					"fieldname": "supplier",
					"fieldtype": "Link",
					"options": "Supplier",
					"width": 120,
				},
				
			]
		)

	if additional_table_columns:
		columns += additional_table_columns

	columns += [
		{
			"label": _("Payable Account"),
			"fieldname": "credit_to",
			"fieldtype": "Link",
			"options": "Account",
			"width": 80,
		},
		{
			"label": _("Mode Of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Link",
			"options": "Mode of Payment",
			"width": 120,
		},
		{
			"label": _("Project"),
			"fieldname": "project",
			"fieldtype": "Link",
			"options": "Project",
			"width": 80,
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 80,
		},
		{
			"label": _("Purchase Order"),
			"fieldname": "purchase_order",
			"fieldtype": "Link",
			"options": "Purchase Order",
			"width": 100,
		},
		{
			"label": _("Purchase Receipt"),
			"fieldname": "purchase_receipt",
			"fieldtype": "Link",
			"options": "Purchase Receipt",
			"width": 100,
		},
		{
			"label": _("Expense Account"),
			"fieldname": "expense_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 100,
		},
		{"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 100},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
		"label": _("Exchange Rate"),
		"fieldname": "exchange_rate",
		"fieldtype": "Float",
		"width": 100,
		},
  {
	  "label":"Current Exchange Rate",
 		"fieldname":"current_exchange_rate",
		"fieldtype":"Float",
  
		"width":100,
   		
  },
		{
			"label": _(f"Rate({presentation_currency})"),
			"fieldname": "rate",
			"fieldtype": "Float",
   			"precision": 2,
			"width": 100,
		},
  {
"label": _(f"Current Rate ({presentation_currency})"),
		"fieldname": "current_rate",
		"fieldtype": "Float",
  			"precision": 2,
		"width": 100,
  },
  {
  "label": _(f"Landed Cost ({presentation_currency})"),
  "fieldname":"landed_cost_voucher_amount",
  "fieldtype":"Float",
  			"precision": 2,

  "width":100,
  },
  {
	"label": _(f"Current Landed Cost ({presentation_currency})"),
	"fieldname":"current_landed_cost",
	"fieldtype":"Float",
  			"precision": 2,
     "width":100,
  },
  {
	  "label":f"Rate + LC({presentation_currency})",
	  "fieldname":"rate_plus_landed_cost",
	  "fieldtype":"Float",
   			"precision": 2,

	"width":100,
 
  },
	{
	  "label":"Current Rate + LC({presentation_currency})",
	  "fieldname":"current_rate_plus_landed_cost",
	  "fieldtype":"Float",
   			"precision": 2,

	"width":100,
 
  },
		{
			"label": _(f"Amount ({presentation_currency})"),
			"fieldname": "amount",
			"fieldtype": "Float",
   			"precision": 2,

			"width": 100,
		},
	]
 
	columns.append(
		{
			"label": _(f"Current Total ({presentation_currency})"),
			"fieldname": "current_total",
			"fieldtype": "Float",
			"precision": 2,
		}
	)

	if filters.get("group_by"):
		columns.append(
			{"label": _("% Of Grand Total"), "fieldname": "percent_gt", "fieldtype": "Float", "width": 80}
		)
	return columns


def apply_conditions(query, pi, pii, filters):
	for opts in ("company", "supplier", "mode_of_payment"):
		if filters.get(opts):
			query = query.where(pi[opts] == filters[opts])

	if filters.get("from_date"):
		query = query.where(pi.posting_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(pi.posting_date <= filters.get("to_date"))

	if filters.get("item_code"):
		query = query.where(pii.item_code == filters.get("item_code"))

	if filters.get("item_group"):
		query = query.where(pii.item_group == filters.get("item_group"))

	if not filters.get("group_by"):
		query = query.orderby(pi.posting_date, order=Order.desc)
		query = query.orderby(pii.item_group, order=Order.desc)
	else:
		query = apply_group_by_conditions(query, pi, pii, filters)

	return query


def get_items(filters, additional_table_columns):
	doctype = "Purchase Invoice"
	pi = frappe.qb.DocType(doctype)
	pii = frappe.qb.DocType(f"{doctype} Item")
	Item = frappe.qb.DocType("Item")
	query = (
		frappe.qb.from_(pi)
		.join(pii)
		.on(pi.name == pii.parent)
		.left_join(Item)
		.on(pii.item_code == Item.name)
		.select(
			pii.name,
			pii.parent,
			pi.posting_date,
			pi.credit_to,
			pi.company,
			pi.supplier,
			pi.remarks,
			pi.base_net_total,
			pi.unrealized_profit_loss_account,
			pii.item_code,
			pii.description,
			pii.item_group,
			pii.item_name.as_("pi_item_name"),
			pii.item_group.as_("pi_item_group"),
			Item.item_name.as_("i_item_name"),
			Item.item_group.as_("i_item_group"),
			pii.landed_cost_voucher_amount,
			pii.project,
			pii.purchase_order,
			pii.purchase_receipt,
			pii.po_detail,
			pii.expense_account,
			pii.stock_qty,
			pii.stock_uom,
			pii.base_net_amount,
			pi.supplier_name,
			pi.mode_of_payment,
			pi.conversion_rate,
		)
		.where(pi.docstatus == 1)
		.where(pii.parenttype == doctype)
	)

	if filters.get("supplier"):
		query = query.where(pi.supplier == filters["supplier"])
	if filters.get("company"):
		query = query.where(pi.company == filters["company"])

	if additional_table_columns:
		for column in additional_table_columns:
			if column.get("_doctype"):
				table = frappe.qb.DocType(column.get("_doctype"))
				query = query.select(table[column.get("fieldname")])
			else:
				query = query.select(pi[column.get("fieldname")])

	query = apply_conditions(query, pi, pii, filters)

	return query.run(as_dict=True)


def get_aii_accounts():
	return dict(frappe.db.sql("select name, stock_received_but_not_billed from tabCompany"))


def get_purchase_receipts_against_purchase_order(item_list):
	po_pr_map = frappe._dict()
	po_item_rows = list(set(d.po_detail for d in item_list))

	if po_item_rows:
		purchase_receipts = frappe.db.sql(
			"""
			select parent, purchase_order_item
			from `tabPurchase Receipt Item`
			where docstatus=1 and purchase_order_item in (%s)
			group by purchase_order_item, parent
		"""
			% (", ".join(["%s"] * len(po_item_rows))),
			tuple(po_item_rows),
			as_dict=1,
		)

		for pr in purchase_receipts:
			po_pr_map.setdefault(pr.po_detail, []).append(pr.parent)

	return po_pr_map


def convert_currency_fields(data, filters):
		date=filters.get("to_date") or frappe.utils.now()
		to_currency=frappe.get_cached_value("Company", filters.company, "default_currency")
		from_currency=filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
		for entry in data:
			entry['rate'] = convert(entry.get('rate', 0), from_currency, to_currency, date)
			entry['amount'] = convert(entry.get('amount', 0), from_currency, to_currency, date)
			entry['landed_cost_voucher_amount'] = convert(entry.get('landed_cost_voucher_amount', 0), from_currency, to_currency, date)
			entry['rate_plus_landed_cost'] = convert(entry.get('rate_plus_landed_cost', 0), from_currency, to_currency, date)
			entry['total_tax']=convert(entry.get('total_tax',0), from_currency, to_currency, date)
			entry['total'] = convert(entry.get('total', 0), from_currency, to_currency, date)
			if filters.get('presentation_currency') != 'USD':
				entry['current_rate'] = convert(entry.get('current_rate', 0), from_currency, to_currency, date)
				entry['current_rate_plus_landed_cost'] = convert(entry.get('current_rate_plus_landed_cost', 0), from_currency, to_currency, date)
				entry['current_total'] = convert(entry.get('current_total', 0), from_currency, to_currency, date)
				

		return data