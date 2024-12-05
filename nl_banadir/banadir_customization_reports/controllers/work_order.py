import frappe


from frappe.model.naming import make_autoname
from datetime import datetime

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


def generate_invoice_number(item_code, company_abbr):
    """
    Generate a custom invoice number in the format: item_code-company_abbreviation-series.
    """
    series = make_autoname(f"{company_abbr}-.####")
    return f"{item_code}-{series}"

def create_purchase_invoice(operation, company, currency, custom_work_order):
    """
    Create a Purchase Invoice for the given operation.
    """
    company_abbr = frappe.db.get_value("Company", company, "abbr")
    if not company_abbr:
        frappe.throw(f"Company abbreviation not found for {company}")

    # Generate the custom invoice number
    custom_invoice_no = generate_invoice_number(operation.operations, company_abbr)

    # Create a new Purchase Invoice
    purchase_invoice = frappe.new_doc("Purchase Invoice")
    purchase_invoice.currency = currency
    purchase_invoice.supplier = operation.supplier
    purchase_invoice.company = company
    # purchase_invoice.set_warehouse = "Store - CW"
    purchase_invoice.update_stock = 0
    purchase_invoice.custom_work_order = custom_work_order
    purchase_invoice.custom_invoice_no = custom_invoice_no

    purchase_invoice.append("items", {
        "item_code": operation.item,
        "qty": operation.completed_qty or 1,
        "rate": operation.rate,
        "amount": operation.amount
    })

    purchase_invoice.insert()
    purchase_invoice.submit()

    # Mark the operation as "invoice_created = 1"
    frappe.db.set_value(
        "Work Order Operations Item",
        operation.name,  
        "invoice_created",
        1
    )
    frappe.db.set_value(
        "Work Order Operations Item",
        operation.name,  
        "invoice",
        purchase_invoice.name
    )

    return purchase_invoice

def on_update(doc, method=None):
    """
    Main function to handle the creation of Purchase Invoices for completed operations.
    """
    for operation in doc.custom_subcontractors:
        operation_doc = frappe.get_doc("Work Order Operations Item", operation.get('name'))
        if (operation_doc.status == "In Progress" or operation_doc.status == "Completed") and operation_doc.supplier is None:
            frappe.throw("Kindly enter the supplier in Sub-contractor table")
        # Only consider operations with status "Completed" and invoice_created flag is 0
        if operation_doc.status == "Completed" and operation_doc.invoice_created == 0:
            if operation_doc.completed_qty > doc.qty:
                frappe.throw(
                    f"Completed quantity ({operation_doc.completed_qty}) for operation '{operation_doc.operations}' "
                    f"cannot exceed the quantity to manufacture ({doc.qty}) on this Work Order."
                )
            create_purchase_invoice(
                operation=operation_doc,
                company=doc.company,
                currency=operation_doc.currency,
                custom_work_order=doc.name
            )

            frappe.msgprint("Purchase Invoices successfully created for all suppliers with completed operations.")
    # doc.save()
    # doc.reload()
