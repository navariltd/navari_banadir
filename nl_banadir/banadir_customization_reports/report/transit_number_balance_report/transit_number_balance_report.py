# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Sum, Round, GroupConcat, Coalesce, Avg
from frappe.utils import flt


def execute(filters: dict | None = None):
    columns = get_columns(filters)
    data = get_data(filters)

    return columns, data


def get_columns(filters: dict | None = None) -> list[dict]:
    columns = [
        {
            "fieldname": "transit_no_link", 
            "label": "Transit Number", 
            "fieldtype": "HTML", 
            "width": 200
        },
        {
            "fieldname": "name_link", 
            "label": "Invoice Name", 
            "fieldtype": "HTML", 
            "width": 250
        },
        {
            "fieldname": "item_code", 
            "label": "Item Code", 
            "fieldtype": "Link",
            "options": "Item",
            "width": 250
        },
        {
            "fieldname": "uom", 
            "label": "Item UOM", 
            "fieldtype": "Data", 
            "width": 120
        },
        {
            "fieldname": "qty_in", 
            "label": "Total Qty In", 
            "fieldtype": "Float", 
            "width": 120
        },
        {
            "fieldname": "qty_out", 
            "label": "Total Qty Out", 
            "fieldtype": "Float", 
            "width": 120
        },
        {
            "fieldname": "balance", 
            "label": "Balance", 
            "fieldtype": "Float", 
            "width": 120
        },
        {
            "fieldname": "purchase_invoice_amount",
            "label": "Purchase Invoice Amount",
            "fieldtype": "Currency",
            "width": 150,
            "options": "purchase_invoice_currency"
        },
        {
            "fieldname": "sales_invoice_amount",
            "label": "Sales Invoice Amount",
            "fieldtype": "Currency",
            "width": 150,
            "options": "sales_invoice_currency"
        },
        {
            "fieldname": "purchase_invoice_currency",
            "label": "Purchase Invoice Currency",
            "fieldtype": "Link",
            "options": "Currency",
            "hidden": 1
        },
        {
            "fieldname": "sales_invoice_currency",
            "label": "Sales Invoice Currency",
            "fieldtype": "Link",
            "options": "Currency",
            "hidden": 1
        }
    ]
    
    if filters.get("container_no"):
        columns.append({
            "fieldname": "container_no",
            "label": "Container No",
            "fieldtype": "Data"
        })
    
    return columns


def get_data(filters) -> list[list]:

    PurchaseInvoice = DocType("Purchase Invoice")
    TransitNumbers = DocType("Transit Numbers")
    PurchaseInvoiceItem = DocType("Purchase Invoice Item")
    SalesInvoiceItem = DocType("Sales Invoice Item")
    SalesInvoice = DocType("Sales Invoice")

    pii_agg = (
        frappe.qb.from_(PurchaseInvoiceItem)
        .select(
            PurchaseInvoiceItem.parent.as_("transit_no"),
            PurchaseInvoiceItem.item_code,
            PurchaseInvoiceItem.uom,
            Sum(PurchaseInvoiceItem.qty).as_("total_qty_in"),
            Avg(PurchaseInvoiceItem.amount).as_("avg_purchase_amount"),
        )
        .groupby(PurchaseInvoiceItem.parent, PurchaseInvoiceItem.item_code)
    )

    sii_agg = (
        frappe.qb.from_(SalesInvoiceItem)
        .select(
            SalesInvoiceItem.custom_purchase_invoice.as_("transit_no"),
            SalesInvoiceItem.item_code,
            Sum(SalesInvoiceItem.qty).as_("total_qty_out"),
            GroupConcat(SalesInvoiceItem.parent).as_("sales_invoices"),
            Avg(SalesInvoiceItem.amount).as_("avg_sales_amount"),
        )
        .groupby(SalesInvoiceItem.custom_purchase_invoice, SalesInvoiceItem.item_code)
    )

    query = (
        frappe.qb.from_(PurchaseInvoice)
        .join(TransitNumbers)
        .on(PurchaseInvoice.name == TransitNumbers.parent)
        .join(pii_agg)
        .on(TransitNumbers.transit_no == pii_agg.transit_no)
        .left_join(sii_agg)
        .on(
            (sii_agg.item_code == pii_agg.item_code)
            & (sii_agg.transit_no == TransitNumbers.transit_no)
        )
        .left_join(SalesInvoice)
        .on(SalesInvoice.name == sii_agg.sales_invoices)
        .select(
            TransitNumbers.transit_no.as_("transit_no"),
            pii_agg.item_code.as_("item_code"),
            pii_agg.uom.as_("uom"),
            Round(pii_agg.total_qty_in, 2).as_("qty_in"),
            Round(Coalesce(sii_agg.total_qty_out, 0), 2).as_("qty_out"),
            Round(
                pii_agg.total_qty_in - Coalesce(sii_agg.total_qty_out, 0), 2
            ).as_("balance"),
            Round(Coalesce(pii_agg.avg_purchase_amount, 0), 2).as_("purchase_invoice_amount"),
            Round(Coalesce(sii_agg.avg_sales_amount, 0), 2).as_("sales_invoice_amount"),
            sii_agg.sales_invoices.as_("sales_invoices"),  # Already grouped
            PurchaseInvoice.custom_container_no.as_("container_no"),
            PurchaseInvoice.currency.as_("purchase_invoice_currency"),
            SalesInvoice.currency.as_("sales_invoice_currency"),
        )
        .where(
            (PurchaseInvoice.custom_is_export_sale == 1)
            & (PurchaseInvoice.docstatus == 1)
        )
        .distinct()
        .orderby(TransitNumbers.transit_no, pii_agg.item_code)
    )


    if filters.get("from_date") and filters.get("to_date"):
        query = query.where(
            PurchaseInvoice.posting_date.between(filters["from_date"], filters["to_date"])
        )
    elif filters.get("from_date"):
        query = query.where(PurchaseInvoice.posting_date >= filters["from_date"])
    elif filters.get("to_date"):
        query = query.where(PurchaseInvoice.posting_date <= filters["to_date"])
    if filters.get("sales_invoice"):
        query = query.where(PurchaseInvoice.name == filters["sales_invoice"])
    if filters.get("currency"):
        query = query.where(PurchaseInvoice.currency == filters["currency"])
    if filters.get("company"):
        query = query.where(
            (PurchaseInvoice.company == filters["company"])
            & (TransitNumbers.company == filters["company"])
        )
    if filters.get("branch"):
        query = query.where(PurchaseInvoice.branch == filters["branch"])


    data = query.run(as_dict=True)

    if filters.get("alternative_uom"):
        data = convert_alternative_uom(data, filters)

    # Process the data and calculate totals for each transit number
    processed_data = []
    transit_totals = {}  # Dictionary to store totals for each transit number

    for row in data:
        # Create clickable HTML link for each transit number
        transit_no_link = f'<a href="/app/purchase-invoice/{row["transit_no"]}" target="_blank">{row["transit_no"]}</a>'
        
        # Create clickable HTML links for sales invoices
        if row.get('sales_invoices'):
            sales_invoice_links = ', '.join([
                f'<a href="/app/sales-invoice/{inv.strip()}" target="_blank">{inv.strip()}</a>' for inv in row['sales_invoices'].split(' ')
            ])
        else:
            sales_invoice_links = ""

        # Append the row data
        processed_data.append({
            "transit_no_link": transit_no_link,
            "name_link": sales_invoice_links,
            "item_code": row['item_code'],
            "uom": row['uom'],
            "qty_in": row['qty_in'],
            "qty_out": row['qty_out'],
            "balance": row['balance'],
            "container_no": row['container_no'],
            "purchase_invoice_amount": row['purchase_invoice_amount'],
            "sales_invoice_amount": row['sales_invoice_amount'],
            "purchase_invoice_currency": row['purchase_invoice_currency'],
            "sales_invoice_currency": row['sales_invoice_currency']
        })

        # Calculate totals for each transit number
        if row["transit_no"] not in transit_totals:
            transit_totals[row["transit_no"]] = {
                "qty_in": 0.0,
                "qty_out": 0.0,
                "balance": 0.0,
                "purchase_invoice_amount": 0.0,
                "sales_invoice_amount": 0.0,
                "purchase_invoice_currency": row['purchase_invoice_currency'],
                "sales_invoice_currency": row['sales_invoice_currency']
            }
        
        transit_totals[row["transit_no"]]["qty_in"] += row["qty_in"]
        transit_totals[row["transit_no"]]["qty_out"] += row["qty_out"]
        transit_totals[row["transit_no"]]["balance"] += row["balance"]
        transit_totals[row["transit_no"]]["purchase_invoice_amount"] += row["purchase_invoice_amount"]
        transit_totals[row["transit_no"]]["sales_invoice_amount"] += row["sales_invoice_amount"]

    # Append totals for each transit number after their respective items
    final_data = []
    last_transit_no = None

    for i, row in enumerate(processed_data):
        # Add the current row to the final data
        final_data.append(row)
        
        # Extract the current transit_no from the HTML link
        current_transit_no = row["transit_no_link"].split('>')[1].split('<')[0]

        # Check if we have reached the last row or the next row has a different transit_no
        if i == len(processed_data) - 1 or (processed_data[i + 1]["transit_no_link"].split('>')[1].split('<')[0] != current_transit_no):
            # We need to add the total row for the current transit_no
            totals = transit_totals[current_transit_no]
            final_data.append({
                "is_total_row": True,
                "transit_no_link": f"<b>Total for {current_transit_no}</b>",
                "name_link": "",
                "item_code": "",
                "uom": "",
                "qty_in": totals['qty_in'],
                "qty_out": totals['qty_out'],
                "balance": totals['balance'],
                "container_no": "",
                "purchase_invoice_amount": totals['purchase_invoice_amount'],
                "sales_invoice_amount": totals['sales_invoice_amount'],
                "purchase_invoice_currency": totals['purchase_invoice_currency'],
                "sales_invoice_currency": totals['sales_invoice_currency']
            })
            
    # Initialize grand total variables
    grand_totals = {"qty_in": 0.0, "qty_out": 0.0, "balance": 0.0, "purchase_invoice_amount": 0.0, "sales_invoice_amount": 0.0, "purchase_invoice_currency": "", "sales_invoice_currency": ""}

    # Calculate grand totals while processing transit totals
    for transit, totals in transit_totals.items():
        grand_totals["qty_in"] += totals["qty_in"]
        grand_totals["qty_out"] += totals["qty_out"]
        grand_totals["balance"] += totals["balance"]
        grand_totals["purchase_invoice_amount"] += totals["purchase_invoice_amount"]
        grand_totals["sales_invoice_amount"] += totals["sales_invoice_amount"]
        grand_totals["purchase_invoice_currency"] = totals["purchase_invoice_currency"]
        grand_totals["sales_invoice_currency"] = totals["sales_invoice_currency"]

    # Append the grand totals row to the final data
    final_data.append({
        "is_total_row": True,
        "transit_no_link": "<b>Grand Total</b>",
        "name_link": "",
        "item_code": "",
        "uom": "",
        "qty_in": grand_totals['qty_in'],
        "qty_out": grand_totals['qty_out'],
        "balance": grand_totals['balance'],
        "container_no": "",
        "purchase_invoice_amount": grand_totals['purchase_invoice_amount'],
        "sales_invoice_amount": grand_totals['sales_invoice_amount'],
        "purchase_invoice_currency": grand_totals['purchase_invoice_currency'],
        "sales_invoice_currency": grand_totals['sales_invoice_currency']
    })

    
    return final_data

def convert_alternative_uom(data, filters):
    alternative_uom = filters.get('alternative_uom')
    
    for row in data:
        item_code = row.get('item_code')
        
        if item_code:
            conversion_factor = get_conversion_factor(item_code, alternative_uom)
            
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    new_value = value / conversion_factor
                    row[key] = new_value 
    
    return data

def get_conversion_factor(item_code, alternative_uom):
    uom_conversion = frappe.db.get_value("UOM Conversion Detail", {"parent": item_code, "uom": alternative_uom}, "conversion_factor")
    return uom_conversion or 1
 