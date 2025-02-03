import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabStock Ledger Entry`
        SET fiscal_year = 'India Mar24 To 23/01/2025'
        WHERE posting_date BETWEEN '2024-01-03' AND '2025-01-23'
        AND company = 'CITYWALK FOOTWEAR PVT LTD'
    """)
    frappe.db.commit()

