import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabStock Ledger Entry`
        SET fiscal_year = 'conakry 2024'
        WHERE posting_date BETWEEN '2024-07-01' AND '2025-01-30'
        AND company = 'Banadir General Trading LTD (Conakry)'
    """)
    frappe.db.commit()

