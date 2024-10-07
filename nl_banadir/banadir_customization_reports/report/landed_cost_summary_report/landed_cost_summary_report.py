# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.query_builder import DocType

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
        {
            "label": "Invoice Number", 
            "fieldname": "invoice_number", 
            "fieldtype": "Link", 
            "options": "Purchase Invoice",
            "width": "220"
        },
        {
            "label": "Landed Cost", 
            "fieldname": "landed_cost", 
            "fieldtype": "Link",
            "options": "Landed Cost Voucher",
            "width": "220"
        },
        {
            "label": "Expense Account", 
            "fieldname": "expense_account", 
            "fieldtype": "Link", 
            "options": "Account",
            "width": "200"
        },
        {
            "label": "Expense Booked", 
            "fieldname": "expense_booked", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": "100"
        },
        {
            "label": "Amount", 
            "fieldname": "amount", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": "100"
        },
        {
            "label": "Currency", 
            "fieldname": "currency", 
            "fieldtype": "Link",
            "options": "Currency",
            "width": "70"
        },
        {
            "label": "Container No", 
            "fieldname": "container_no", 
            "fieldtype": "Data",
            "width": "140"
        },
        {
            "label": "BL Number", 
            "fieldname": "bl_number", 
            "fieldtype": "Data",
            "width": "140"
        },
        {
            "label": "Description", 
            "fieldname": "description", 
            "fieldtype": "Data"
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
        .join(PurchaseInvoice)
        .on(LandedCostPurchaseReceipt.receipt_document == PurchaseInvoice.name)
        .left_join(LandedCostTaxesAndCharges)
        .on(LandedCostVoucher.name == LandedCostTaxesAndCharges.parent)
        .select(
            LandedCostVoucher.name.as_("landed_cost"),
            PurchaseInvoice.name.as_("invoice_number"),
            LandedCostTaxesAndCharges.account_currency.as_("currency"),
            LandedCostTaxesAndCharges.expense_account.as_("expense_account"),
            PurchaseInvoice.custom_container_no.as_("container_no"),
            PurchaseInvoice.custom_bill_of_lading.as_("bl_number"),
            LandedCostTaxesAndCharges.amount.as_("amount"),
            LandedCostTaxesAndCharges.amount.as_("expense_booked"),
            LandedCostTaxesAndCharges.description.as_("description")
        )
        .where(PurchaseInvoice.docstatus == 1)
        .where(LandedCostVoucher.docstatus == 1)
        .groupby(LandedCostVoucher.name, PurchaseInvoice.name)
    )

    # Apply filters if provided
    if filters.get("company"):
        query = query.where(LandedCostVoucher.company == filters.get("company"))
    
    if filters.get("purchase_invoice"):
        query = query.where(PurchaseInvoice.name == filters.get("purchase_invoice"))

    # Fetch data
    data = query.run(as_dict=True)

    selected_currency = filters.get("currency")
    final_data = []
    totals_dict = {}


    for row in data:
        original_currency = row["currency"]
        original_expense_booked = row["expense_booked"]
        original_amount = row["amount"]

        # Convert currency if necessary
        if selected_currency and selected_currency != original_currency:
            row["expense_booked"] = convert_currency(original_expense_booked, original_currency, selected_currency, nowdate())
            row["amount"] = convert_currency(original_amount, original_currency, selected_currency, nowdate())
            row["currency"] = selected_currency

        # Add row to final data
        final_data.append(row)

        # Accumulate totals in the dictionary
        invoice_number = row["invoice_number"]
        if invoice_number not in totals_dict:
            totals_dict[invoice_number] = {
                "total_expense_booked": 0,
                "total_amount": 0,
                "currency": selected_currency if selected_currency else original_currency
            }

        totals_dict[invoice_number]["total_expense_booked"] += row["expense_booked"]
        totals_dict[invoice_number]["total_amount"] += row["amount"]

    # Add totals to final data
    for invoice_number, totals in totals_dict.items():
        total_row = {
            "invoice_number": f"Total - {invoice_number}",
            "expense_booked": totals["total_expense_booked"],
            "amount": totals["total_amount"],
            "currency": totals["currency"],
            "expense_account": "",
            "container_no": "",
            "bl_number": "",
            "landed_cost": "",
            "description": "",
            "is_total": True,
        }
        final_data.append(total_row)

    # Sort data by invoice number
    final_data = sorted(final_data, key=lambda x: x["invoice_number"][8:] if x["invoice_number"].startswith("Total - ") else x["invoice_number"])

    return final_data

def get_conversion_rate(from_currency, to_currency, date):

    if from_currency == to_currency:
        return (1, None)

    conversion_rate = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": from_currency, "to_currency": to_currency},
        ["exchange_rate", "date"]
    )

    if conversion_rate:
        return conversion_rate[0], conversion_rate[1]
    else:
        # Try fetching the inverse exchange rate
        inverse_conversion_rate = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": to_currency, "to_currency": from_currency},
            ["exchange_rate", "date"]
        )

        if inverse_conversion_rate:
            inverse_exchange_rate = inverse_conversion_rate[0]
            return 1 / inverse_exchange_rate, inverse_conversion_rate[1]
        else:
            frappe.throw(
                _("Exchange rate not found for {0} to {1}").format(
                    from_currency, to_currency
                )
            )

def convert_currency(amount, from_currency, to_currency, date):
    conversion_rate, conversion_date = get_conversion_rate(from_currency, to_currency, date)
    return amount * conversion_rate
