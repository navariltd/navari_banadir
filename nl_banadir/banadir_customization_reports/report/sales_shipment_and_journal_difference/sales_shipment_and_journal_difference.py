# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import Coalesce


def execute(filters: dict | None = None):
      
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	return [
        {
            "label": "Journal Entry", 
            "fieldname": "journal_entry", 
            "fieldtype": "Link", 
            "options": "Journal Entry", 
            "width": 150
        },
        {
            "label": "Sales Invoice", 
            "fieldname": "sales_invoice", 
            "fieldtype": "Link", 
            "options": "Sales Invoice", 
            "width": 150
        },
        {
            "label": "Sales Shipment",
            "fieldname": "sales_shipment",
            "fieldtype": "Link",
            "options": "Sales Shipment Cost",
            "width": 150    
        },
        {
            "label": "Journal Total", 
            "fieldname": "journal_total", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": "Shipment Total", 
            "fieldname": "shipment_total", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": "Difference", 
            "fieldname": "difference", 
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150
        },
        {
            "label": "Currency",
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 150,
            # "hidden": 1
        }
    ]


def get_data(filters: dict) -> list[dict]:
    data = []

    JournalEntry = DocType("Journal Entry")
    JournalEntryAccount = DocType("Journal Entry Account")
    SalesShipmentCost = DocType("Sales Shipment Cost")
    LandedCostSalesInvoice = DocType("Landed Cost Sales Invoice")

    query = (
        frappe.qb.from_(JournalEntry)
        .join(JournalEntryAccount)
        .on(JournalEntry.name == JournalEntryAccount.parent)
        .left_join(SalesShipmentCost)
        .on(SalesShipmentCost.name == JournalEntryAccount.custom_sales_shipment_ref)
        .select(
            JournalEntry.name.as_("journal_entry"),
            JournalEntry.total_debit.as_("journal_total"),
            JournalEntryAccount.custom_sales_shipment_ref.as_("sales_shipment"),
            SalesShipmentCost.sales_invoice.as_("sales_invoice")
        )
        .where(
            (JournalEntryAccount.custom_sales_shipment_ref.isnotnull())
        )
    )

    # Apply filters
    if filters.get("company"):
        query = query.where(JournalEntry.company == filters.get("company"))
    if filters.get("from_date"):
        query = query.where(JournalEntry.posting_date >= filters.get("from_date"))
    if filters.get("to_date"):
        query = query.where(JournalEntry.posting_date <= filters.get("to_date"))
    if filters.get("currency"):
        query = query.where(JournalEntryAccount.currency == filters.get("currency"))
    if filters.get("journal_entry"):
        query = query.where(JournalEntry.name == filters.get("journal_entry"))
    if filters.get("sales_invoice"):
        query = query.where(SalesShipmentCost.sales_invoice == filters.get("sales_invoice"))
    if filters.get("sales_shipment"):
        query = query.where(JournalEntryAccount.custom_sales_shipment_ref == filters.get("sales_shipment"))

    journal_entries = query.run(as_dict=True)


    for je in journal_entries:
        journal_total = je.journal_total or 0
        sales_shipment = je.sales_shipment
        sales_invoice = None
        currency = None

        # Fetch Sales Invoice from the child table of Sales Shipment Cost
        if sales_shipment:
            sales_invoice = frappe.db.get_value(
                "Landed Cost Sales Invoice",
                {"parent": sales_shipment},
                "receipt_document"
            )

            currency = frappe.db.get_value(
                "Sales Invoice",
                {"name": sales_invoice},
                "currency"
            )

        shipment_total = frappe.db.get_value(
            "Sales Shipment Cost", sales_shipment, "total_taxes_and_charges"
        ) or 0

        difference = journal_total - shipment_total

        data.append({
            "journal_entry": je.journal_entry,
            "sales_invoice": sales_invoice,
            "sales_shipment": sales_shipment,
            "journal_total": journal_total,
            "shipment_total": shipment_total,
            "difference": difference,
            "currency": currency
        })

    return data
