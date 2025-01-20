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
		# Check if 'rate' and 'exchange_rate' keys exist in the entry
		if 'rate' in entry and 'exchange_rate' in entry:
			# In dollars
			old_rate_in_usd = entry['rate'] / entry['exchange_rate']
			old_rate_plus_landed_cost_in_usd = entry['rate_plus_landed_cost'] / entry['exchange_rate']
			old_landed_cost = entry['landed_cost_voucher_amount'] / entry['exchange_rate']

			current_rate_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_rate_in_usd
			current_rate_plus_landed_cost_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_rate_plus_landed_cost_in_usd
			current_rate_in_usd = convert(current_rate_chosen_currency, "USD", to_currency, date)
			current_rate_plus_landed_cost_in_usd = convert(current_rate_plus_landed_cost_chosen_currency, "USD", to_currency, date)
			current_landed_cost_chosen_currency = get_current_exchange_rate(from_currency, to_currency, date) * old_landed_cost
			current_landed_cost_in_usd = convert(current_landed_cost_chosen_currency, "USD", to_currency, date)

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

# def get_container_no
def _execute(filters=None, additional_table_columns=None):
	if not filters:
		filters = {}
	columns = get_columns(additional_table_columns, filters)
	company_currency = erpnext.get_company_currency(filters.company)
	item_list = get_items(filters, additional_table_columns)
	aii_account_map = get_aii_accounts()
	presentation_currency= filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
	# frappe.throw(str(presentation_currency))
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
			"container_no": d.custom_container_no,
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
		"amount_plus_landed_cost": d.base_net_amount + flt(d.landed_cost_voucher_amount),
			"total_landed_cost": d.landed_cost_voucher_amount,
		"currency":presentation_currency,
			}
		row["stock_qty"] = flt(row["stock_qty"]) if row["stock_qty"] else 0
		total_tax = 0
		for tax in tax_columns:
			item_tax = itemised_tax.get(d.name, {}).get(tax, {})
			row.update(
				{
					scrubbed_tax_fields[tax + " Rate"]: item_tax.get("tax_rate", 0),
					scrubbed_tax_fields[tax + " Amount"]: item_tax.get("tax_amount", 0),
				}
			)
			total_tax += flt(item_tax.get("tax_amount"))

		row.update(
			{"total_tax": total_tax, "total": d.base_net_amount + total_tax, "currency": presentation_currency}
		)


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
	# frappe.throw(str(data))
	if filters.get("group_by") and item_list:
		total_row = total_row_map.get(prev_group_by_value or d.get("item_name"))
		total_row["percent_gt"] = flt(total_row["total"] / grand_total * 100)
		# total_row[""]
		data.append(total_row)
		data.append({})
		add_sub_total_row(total_row, total_row_map, "total_row", tax_columns)
		# data.append(total_row_map.get("total_row"))
		skip_total_row = 1

	data=append_opening_qty(data, filters)
	data=convert_as_per_current_exchange_rate(data, filters, "USD", presentation_currency)
	data=convert_currency_fields(data, filters)
	data=convert_alternative_uom(data, filters)
	data=append_total_row(data)

	return columns, data, None, None, None, skip_total_row
	
def get_columns(additional_table_columns, filters):
    presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value(
        "Company", filters.company, "default_currency"
    )
    columns = []
    
    if filters.get("group_by") != "Item":
        columns.extend(
            [
                {
                    "label": _("Item Code"),
                    "fieldname": "item_code",
                    "fieldtype": "Link",
                    "options": "Item",
                    "width": 120,
                    "hidden": 1 if filters.get("hide_column") else 0,
                },
                {
                    "label": _("Currency"),
                    "fieldname": "currency",
                    "fieldtype": "Link",
                    "options": "Currency",
                    "width": 80,
                    "hidden": 1,
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
            {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "hidden": 1 if filters.get("hide_column") else 0, "width": 150},
            {
                "label": _("Invoice"),
                "fieldname": "invoice",
                "fieldtype": "Link",
                "options": "Purchase Invoice",
                "width": 120,
            },
            {
                "label": _("Container No"),
                "fieldname": "container_no",
                "fieldtype": "Data",
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
                    "hidden": 1 if filters.get("hide_column") else 0,
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
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Mode Of Payment"),
            "fieldname": "mode_of_payment",
            "fieldtype": "Link",
            "options": "Mode of Payment",
            "width": 120,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Project"),
            "fieldname": "project",
            "fieldtype": "Link",
            "options": "Project",
            "width": 80,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 80,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Purchase Order"),
            "fieldname": "purchase_order",
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Purchase Receipt"),
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _("Expense Account"),
            "fieldname": "expense_account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {"label": _("Opening Stock"), "fieldname": "opening_stock_qty", "fieldtype": "Float", "width": 100, "hidden": 1},
        {"label": _("Stock Qty"), "fieldname": "stock_qty", "fieldtype": "Float", "width": 100},
        {
            "label": _("Stock UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
    ]

    # Add the Alternative UOM column after Stock UOM
    if filters.get("alternative_uom"):
        columns.append(
            {
                "label": _("<span style='color:red'>Alternative UOM</span>"),
                "fieldname": "uom",
                "fieldtype": "Link",
                "options": "UOM",
                "width": 100,
                "hidden": 1 if filters.get("hide_column") else 0,
            }
        )

    columns += [
        {
            "label": _("Exchange Rate"),
            "fieldname": "exchange_rate",
            "fieldtype": "Float",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": "Current Exchange Rate",
            "fieldname": "current_exchange_rate",
            "fieldtype": "Float",
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _(f"Rate ({presentation_currency})"),
            "fieldname": "rate",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _(f"Current Rate ({presentation_currency})"),
            "fieldname": "current_rate",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _(f"Landed Cost ({presentation_currency})"),
            "fieldname": "landed_cost_voucher_amount",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _(f"Current Landed Cost ({presentation_currency})"),
            "fieldname": "current_landed_cost",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": f"Rate + LC({presentation_currency})",
            "fieldname": "rate_plus_landed_cost",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": "Current Rate + LC({presentation_currency})",
            "fieldname": "current_rate_plus_landed_cost",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
            "hidden": 1 if filters.get("hide_column") else 0,
        },
        {
            "label": _(f"Amount ({presentation_currency})"),
            "fieldname": "amount",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
        },
        {
            "label": _(f"Total LC ({presentation_currency})"),
            "fieldname": "total_landed_cost",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
        },
        {
            "label": _(f"Amount + LC ({presentation_currency})"),
            "fieldname": "amount_plus_landed_cost",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "width": 100,
        },
    ]

    columns.append(
        {
            "label": _(f"Current Total ({presentation_currency})"),
            "fieldname": "current_total",
            "fieldtype": "Float",
            "precision": 2,  # Ensure precision is set to 2
            "hidden": 1 if filters.get("hide_column") else 0,
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
			pi.custom_container_no,
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
			entry["amount_plus_landed_cost"] = convert(entry.get("amount_plus_landed_cost", 0), from_currency, to_currency, date)
			entry["total_landed_cost"] = convert(entry.get("total_landed_cost", 0), from_currency, to_currency, date)
			if filters.get('presentation_currency') != 'USD':
				entry['current_rate'] = convert(entry.get('current_rate', 0), from_currency, to_currency, date)
				entry['current_rate_plus_landed_cost'] = convert(entry.get('current_rate_plus_landed_cost', 0), from_currency, to_currency, date)
				entry['current_total'] = convert(entry.get('current_total', 0), from_currency, to_currency, date)
				entry['current_landed_cost'] = convert(entry.get('current_landed_cost', 0), from_currency, to_currency, date)
				
		return data

def get_opening_stock_qty(filters):
	conditions = []
	if filters.get("company"):
		conditions.append("sle.company=%(company)s")
	if filters.get("item_code"):
		conditions.append("sle.item_code=%(item_code)s")
	if filters.get("from_date"):
		conditions.append("sle.posting_date >= %(from_date)s")
	if filters.get("warehouse"):
		conditions.append("sle.warehouse=%(warehouse)s")
	condition_str = " AND ".join(conditions)

	query = f"""
		SELECT
			sle.item_code,
			sle.warehouse,
			MIN(CONCAT(sle.posting_date, ' ', sle.posting_time)) AS first_transaction_time,
			(
				SELECT (qty_after_transaction - actual_qty)
				FROM `tabStock Ledger Entry` sub_sle
				WHERE sub_sle.item_code = sle.item_code
				  AND sub_sle.warehouse = sle.warehouse
				  AND CONCAT(sub_sle.posting_date, ' ', sub_sle.posting_time) = MIN(CONCAT(sle.posting_date, ' ', sle.posting_time))
				  AND {condition_str}
				LIMIT 1
			) AS opening_qty
		FROM
			`tabStock Ledger Entry` sle
		WHERE
			{condition_str}
		GROUP BY
			sle.item_code, sle.warehouse
	"""
	opening_stock_data = frappe.db.sql(query, filters, as_dict=True)
	opening_stock_map = {
		d["item_code"]: d["opening_qty"]
		for d in opening_stock_data
	}
	
	return opening_stock_map
	
def append_opening_qty(data, filters):
	opening_stock_map=get_opening_stock_qty(filters)
	for row in data:
		opening_qty=opening_stock_map.get(row.get("item_code"), 0)
		row["opening_stock_qty"]=opening_qty
	return data




def get_conversion_factor(item_code, alternative_uom):
	uom_conversion = frappe.db.get_value("UOM Conversion Detail", {"parent": item_code, "uom": alternative_uom}, "conversion_factor")
	return uom_conversion or 1

'''Bad implementation because we need to consider a warehouse, incase there is a change, use below code'''
# opening_stock_map = (d["item_code"],d["warehouse"]):d["opening_qty"]

def convert_alternative_uom(data, filters):
	presentation_currency = filters.get("presentation_currency") or frappe.get_cached_value("Company", filters.company, "default_currency")
	alternative_uom = filters.get('alternative_uom')
	item_codes = {row.get('item_code') for row in data if row.get('item_code')}
	item_exists_map = {item['item_code']: True for item in frappe.get_all('Item', filters={'item_code': ['in', list(item_codes)]}, fields=['item_code'])}
	for row in data:
		item_code = row.get('item_code')
		if item_code:
			
			if item_exists_map.get(item_code):
				conversion_factor = get_conversion_factor(item_code, alternative_uom)
				row["uom"] = alternative_uom

				for key in ['stock_qty', 'opening_stock_qty']:
					if key in row:
						value = row[key]
						if isinstance(value, (int, float)): 
							new_value = value / conversion_factor
							row[key] = new_value 
			else:
				data = invoice_details(item_code, row, data, presentation_currency)
				
	return data

def invoice_details(item_code, row, data, presentation_currency):
	invoice_code = item_code 
	stock_qty=0
	current_total = 0
	current_rate = 0
	current_rate_plus_landed_cost = 0
	current_landed_cost = 0
	rate_plus_landed_cost = 0
	landed_cost = 0
	amount_plus_landed_cost = 0
	total_landed_cost = 0

	if invoice_code:
		for d in data:
			if item_code==d.get("invoice"):
				
				stock_qty += d.get('stock_qty', 0)
				current_total += d.get("current_total")
				current_rate += d.get("current_rate")
				current_rate_plus_landed_cost += d.get("rate_plus_landed_cost")
				current_landed_cost += d.get("landed_cost_voucher_amount")
				rate_plus_landed_cost += d.get("rate_plus_landed_cost")
				landed_cost += d.get("landed_cost_voucher_amount")
				amount_plus_landed_cost += d.get("amount_plus_landed_cost")
				total_landed_cost += d.get("total_landed_cost")
	row["currency"] = presentation_currency
	row['stock_qty'] = stock_qty
	row["current_total"] = current_total
	row["current_rate"] = current_rate
	row["current_rate_plus_landed_cost"] = current_rate_plus_landed_cost
	row["current_landed_cost"] = current_landed_cost
	row["rate_plus_landed_cost"] = rate_plus_landed_cost
	row["landed_cost_voucher_amount"] = landed_cost
	row["amount_plus_landed_cost"] = amount_plus_landed_cost
	row["total_landed_cost"] = total_landed_cost
 
	return data

def append_total_row(data):
    if not data:
        return data

    total_row = {key: 0 for key in data[0].keys() if isinstance(data[0][key], (int, float))}
    total_row["bold"] = 1  

    for row in data:
        if not item_exists(row.get('item_code')):
            continue

        for key, value in row.items():
            if isinstance(value, (int, float)): 
                total_row[key] = total_row.get(key, 0) + value
            elif isinstance(value, str) and value.startswith('$'): 
                try:
                    total_row[key] = total_row.get(key, 0) + float(value.strip('$'))
                except ValueError:
                    total_row[key] = total_row.get(key, 0)  

    total_row["item_code"] = "Totals"
    data.append(total_row)
    return data


def item_exists(item_code):
    """Check if the given item_code exists in the Item doctype."""
    if not item_code:
        return False

    # Check existence of the item in the database
    return frappe.db.exists("Item", item_code)