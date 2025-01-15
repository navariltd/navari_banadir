import frappe
from frappe import _, throw, get_doc, utils


@frappe.whitelist()
def create_payment_entry(sales_order_name):
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if not sales_order:
		frappe.throw(_("Sales Order not found"))

	payment_entry = frappe.new_doc("Payment Entry")
	payment_entry.payment_type = "Receive"
	payment_entry.party_type = "Customer"
	payment_entry.party = sales_order.customer
	payment_entry.company = sales_order.company
	payment_entry.posting_date = frappe.utils.nowdate()
	payment_entry.mode_of_payment = sales_order.custom_mode_of_payment
	payment_entry.paid_from = frappe.get_cached_value(
		"Company", sales_order.company, "default_receivable_account"
	)
	payment_entry.paid_from_account_currency = frappe.get_cached_value(
		"Account", payment_entry.paid_from, "account_currency"
	)
	payment_entry.paid_to = frappe.get_cached_value(
		"Company", sales_order.company, "default_cash_account"
	)
	payment_entry.paid_to_account_currency = frappe.get_cached_value(
		"Account", payment_entry.paid_to, "account_currency"
	)
	payment_entry.paid_amount = sales_order.grand_total
	payment_entry.received_amount = sales_order.grand_total

	payment_entry.append("references", {
		"reference_doctype": "Sales Order",
		"reference_name": sales_order_name,
		"total_amount": sales_order.grand_total,
		"outstanding_amount": sales_order.grand_total,
		"allocated_amount": sales_order.custom_paid_amount,
	})
    
	payment_entry.insert(ignore_permissions=True)
	payment_entry.submit()
	frappe.msgprint(_("Payment Entry {0} created successfully").format(payment_entry.name))
	return payment_entry.name
