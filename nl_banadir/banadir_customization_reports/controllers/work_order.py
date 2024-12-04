import frappe

import frappe

def before_save(doc, method=None):
    if not doc.custom_subcontractors:
        currency = frappe.db.get_value("Company", doc.company, "default_currency")

        if doc.production_item:
            item_code = doc.production_item 

            # Fetch sub-operations from Work Order Item Master
            sub_operations = frappe.get_all(
                "Work Order Item Master",  
                filters={"parent": item_code},  
                fields=["operations", "item", "rate", "amount"]
            )

            # Populate the custom_subcontractors table
            for operation in sub_operations:
                doc.append("custom_subcontractors", {
                    "operations": operation["operations"],
                    "rate": operation["rate"],
                    "amount": operation["amount"],
                    "item": operation["item"],
                    "currency": currency,
                })

def on_submit(doc, method=None):
    for operation in doc.custom_subcontractors:
        if (operation.status == "In Progress" or operation.status == "Completed") and operation.supplier is None:
            frappe.throw("Kindly enter the supplier in Sub-contractor table")

    