# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
        {
            "label": "Expense Booked", 
            "fieldname": "expense_booked", 
            "fieldtype": "Currency"
        },
        {
            "label": "Landed Cost", 
            "fieldname": "landed_cost", 
            "fieldtype": "Link",
            "options": "Landed Cost Voucher"
        },
        {
            "label": "Invoice Number", 
            "fieldname": "invoice_number", 
            "fieldtype": "Link", 
            "options": "Purchase Invoice"
        },
        {
            "label": "Container No", 
            "fieldname": "container_no", 
            "fieldtype": "Data"
        },
        {
            "label": "BL Number", 
            "fieldname": "bl_number", 
            "fieldtype": "Data"
        },
        {
            "label": "Expense Account", 
            "fieldname": "expense_account", 
            "fieldtype": "Link", 
            "options": "Account"
        },
        {
            "label": "Description", 
            "fieldname": "description", 
            "fieldtype": "Data"
        },
        {
            "label": "Amount", 
            "fieldname": "amount", 
            "fieldtype": "Currency"
        },
        {
            "label": "Currency", 
            "fieldname": "currency", 
            "fieldtype": "Data"
        },
        {
            "label": "Exchange Rate", 
            "fieldname": "exchange_rate", 
            "fieldtype": "Float"
        }
    ]

def get_data(filters):
    # Define the DocTypes
    PurchaseInvoice = DocType("Purchase Invoice")
    LandedCostVoucher = DocType("Landed Cost Voucher")
    LandedCostPurchaseReceipt = DocType("Landed Cost Purchase Receipt")
    LandedCostTaxesAndCharges = DocType("Landed Cost Taxes and Charges")

    query = (
        frappe.qb.from_(LandedCostVoucher)
        .left_join(LandedCostPurchaseReceipt)
        .on(LandedCostVoucher.name == LandedCostPurchaseReceipt.parent)
        .left_join(PurchaseInvoice)
        .on(LandedCostPurchaseReceipt.receipt_document == PurchaseInvoice.name)
        .left_join(LandedCostTaxesAndCharges)
        .on(LandedCostVoucher.name == LandedCostTaxesAndCharges.parent)
        .select(
            LandedCostTaxesAndCharges.amount.as_("expense_booked"),
            LandedCostVoucher.name.as_("landed_cost"),
            PurchaseInvoice.name.as_("invoice_number"),
            PurchaseInvoice.custom_container_no.as_("container_no"),
            PurchaseInvoice.custom_bill_of_lading.as_("bl_number"),
            LandedCostTaxesAndCharges.expense_account.as_("expense_account"),
            LandedCostTaxesAndCharges.description.as_("description"),
            LandedCostTaxesAndCharges.amount.as_("amount"),
            PurchaseInvoice.currency.as_("currency"),
            PurchaseInvoice.conversion_rate.as_("exchange_rate")
        )
        .where(PurchaseInvoice.docstatus == 1)
    )

    # Fetch data
    data = query.run(as_dict=True)

    return data
