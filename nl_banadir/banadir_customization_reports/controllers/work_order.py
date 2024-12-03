import frappe

import frappe

def before_save(doc, method=None):
    doc.custom_subcontractors = []

    if doc.production_item:
        item_code = doc.production_item 

        # Fetch sub-operations for the item
        sub_operations = frappe.get_all(
            "Work Order Item Master",  
            filters={"parent": item_code},  
            fields=["operations","item", "rate", "amount"]
        )
        # Add sub-operations to the custom_subcontractors table
        for operation in sub_operations:
            doc.append("custom_subcontractors", {
                "operations": operation["operations"],
                "rate": operation["rate"],
                "amount": operation["amount"],
                "item": operation["item"],
            })

def on_submit(doc, method=None):
    for operation in doc.custom_subcontractors:
        if operation.supplier is None:
            frappe.throw("Kindly enter the supplier in Sub-contractor table")
    