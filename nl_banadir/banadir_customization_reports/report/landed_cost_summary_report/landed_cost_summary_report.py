# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.query_builder import DocType
from frappe.query_builder.functions import IfNull
from erpnext.accounts.report.utils import convert

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data

def get_columns(filters=None):
    columns = [
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
            "width": "150"
        },
        {
            "label": "Amount", 
            "fieldname": "amount", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": "150"
        },
        {
            "label": "Currency", 
            "fieldname": "currency", 
            "fieldtype": "Link",
            "options": "Currency",
            "width": "100",
            "hidden": 1
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

    if filters.get("currency"):
        convert_currency = filters.get("currency")
        
        columns.insert(5, {
            "label": f"Amount ({convert_currency})",
            "fieldname": "amount_in_currency",
            "fieldtype": "Currency",
            "options": "selected_currency",
            "width": "150"

        })
        columns.insert(4, {
            "label": f"Expense Booked ({convert_currency})",
            "fieldname": "expense_booked_in_currency",
            "fieldtype": "Currency",
            "options": "selected_currency",
            "width": "170"
        })
        columns.insert(7, {
            "label": f"Exchange Rate",
            "fieldname": "exchange_rate",
            "fieldtype": "Float",
            "width": "150"
        })
     
        columns.append({
            "label": "Selected Currency",
            "fieldname": "selected_currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": "120",
            "hidden": 1
        })
        columns.append({
            "label": "Invoice Currency",
            "fieldname": "invoice_currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": "120",
            "hidden": 1
        })
        columns.append({
            "label": "Conversion Rate",
            "fieldname": "conversion_rate",
            "fieldtype": "Float",
            "width": "120",
            "hidden": 1
        })

    return columns

def get_data(filters):
    # Define the DocTypes
    Company = DocType("Company")
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
        .left_join(Company)
        .on(LandedCostVoucher.company == Company.name)
        .select(
            LandedCostVoucher.name.as_("landed_cost"),
            PurchaseInvoice.name.as_("invoice_number"),
            Company.default_currency.as_("currency"),
            PurchaseInvoice.posting_date.as_("posting_date"),
            PurchaseInvoice.currency.as_("invoice_currency"),
            PurchaseInvoice.conversion_rate.as_("conversion_rate"),
            LandedCostTaxesAndCharges.expense_account.as_("expense_account"),
            PurchaseInvoice.custom_container_no.as_("container_no"),
            PurchaseInvoice.custom_bill_of_lading.as_("bl_number"),
            LandedCostTaxesAndCharges.base_amount.as_("amount"),
            LandedCostTaxesAndCharges.base_amount.as_("expense_booked"),
            LandedCostTaxesAndCharges.description.as_("description")
        )
        .where(PurchaseInvoice.docstatus == 1)
        .where(LandedCostVoucher.docstatus == 1)
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
        date = row["posting_date"]

        # Accumulate totals in the dictionary
        invoice_number = row["invoice_number"]
        if invoice_number not in totals_dict:
            totals_dict[invoice_number] = {
                "total_expense_booked": 0,
                "total_amount": 0,
                "currency": original_currency,
            }

        totals_dict[invoice_number]["total_expense_booked"] += row["expense_booked"]
        totals_dict[invoice_number]["total_amount"] += row["amount"]

        # Convert currency if necessary
        if selected_currency:

            if original_currency != selected_currency and selected_currency == row["invoice_currency"]:

                exchange_rate = 1 / row["conversion_rate"] if row["conversion_rate"] > 1 else exchange_rate

                row["expense_booked_in_currency"] = original_expense_booked * exchange_rate
                row["amount_in_currency"] = original_amount * exchange_rate
                row["selected_currency"] = selected_currency

            else:

                row["expense_booked_in_currency"] = convert(original_expense_booked, selected_currency, original_currency, date)
                row["amount_in_currency"] = convert_currency(original_amount, original_currency, selected_currency, date)
                row["selected_currency"] = selected_currency
                exchange_rate, conversion_date = get_conversion_rate(original_currency, selected_currency, date)
            
            if original_currency != selected_currency and exchange_rate < 1:
                # Display the rate as USD -> CDF, not the inverse
                row["exchange_rate"] = 1 / exchange_rate
            else:
                row["exchange_rate"] = exchange_rate

            # row["exchange_date"] = conversion_date

            if "total_expense_booked_in_currency" not in totals_dict[invoice_number]:
                totals_dict[invoice_number]["total_expense_booked_in_currency"] = 0
            if "total_amount_in_currency" not in totals_dict[invoice_number]:
                totals_dict[invoice_number]["total_amount_in_currency"] = 0

            totals_dict[invoice_number]["total_expense_booked_in_currency"] += row["expense_booked_in_currency"]
            totals_dict[invoice_number]["total_amount_in_currency"] += row["amount_in_currency"]
        
        # Add row to final data
        final_data.append(row)

    # Add totals to final data
    grand_total_expense_booked = 0
    grand_total_amount = 0
    grand_total_expense_booked_in_currency = 0
    grand_total_amount_in_currency = 0

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

        if "total_expense_booked_in_currency" in totals != 0:
            total_row["expense_booked_in_currency"] = totals["total_expense_booked_in_currency"]
            grand_total_expense_booked_in_currency += totals["total_expense_booked_in_currency"]
    
        if "total_amount_in_currency" in totals != 0:
            total_row["amount_in_currency"] = totals["total_amount_in_currency"]
            grand_total_amount_in_currency += totals["total_amount_in_currency"]

        final_data.append(total_row)

        # Accumulate grand totals
        grand_total_expense_booked += totals["total_expense_booked"]
        grand_total_amount += totals["total_amount"]

    final_data.append({
        "invoice_number": "Total",
        "expense_booked": grand_total_expense_booked,
        "amount": grand_total_amount,
        "currency": totals["currency"],
        "expense_account": "",
        "container_no": "",
        "bl_number": "",
        "landed_cost": "",
        "description": "",
        "is_total": True,
        "expense_booked_in_currency": grand_total_expense_booked_in_currency,
        "amount_in_currency": grand_total_amount_in_currency
    })

    # Sort data by invoice number
    final_data = sorted(
        final_data,
        key=lambda x: (
            1 if x["invoice_number"] == "Total" else 0,
            x["invoice_number"][8:] if x["invoice_number"].startswith("Total - ") else x["invoice_number"]
        )
    )

    return final_data

def get_conversion_rate(from_currency, to_currency, date):

    if from_currency == to_currency:
        return 1, None
    
    conversion_rate = frappe.get_all(
        "Currency Exchange",
        filters={
            "from_currency": from_currency,
            "to_currency": to_currency,
            "date": ["<=", date]
        },
        fields=["exchange_rate", "date"],
        order_by="date desc",
        limit=1
    )

    if conversion_rate:
        return conversion_rate[0]["exchange_rate"], conversion_rate[0]["date"]
    else:
        # Try fetching the inverse exchange rate
        inverse_conversion_rate = frappe.get_all(
            "Currency Exchange",
            filters={
                "from_currency": to_currency,
                "to_currency": from_currency,
                "date": ["<=", date]
            },
            fields=["exchange_rate", "date"],
            order_by="date desc",
            limit=1
        )

        if inverse_conversion_rate:
            inverse_exchange_rate = inverse_conversion_rate[0]["exchange_rate"]
            return 1 / inverse_exchange_rate, inverse_conversion_rate[0]["date"]
        else:
            frappe.msgprint(
                _("Exchange rate not found for {0} to {1}").format(
                    from_currency, to_currency
                )
            )
            return 1, None

def convert_currency(amount, from_currency, to_currency, date):
    conversion_rate, conversion_date = get_conversion_rate(from_currency, to_currency, date)
    return amount * conversion_rate
