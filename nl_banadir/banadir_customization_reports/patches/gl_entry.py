import frappe

def execute():
    frappe.db.sql("""
        UPDATE `tabGL Entry`
        SET fiscal_year = '2024'
        WHERE posting_date BETWEEN '2025-01-01' AND '2025-01-23'
        AND company = 'CITYWALK FOOTWEAR PVT LTD'
    """)
    frappe.db.commit()

