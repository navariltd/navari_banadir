import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabGL Entry`
        SET fiscal_year = 'India Mar24 To 23/01/202'
        WHERE posting_date BETWEEN '2024-07-01' AND '2025-01-30'
        AND company = 'Banadir General Trading LTD (Conakry)'
    """)
    frappe.db.commit()

