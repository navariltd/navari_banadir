
import frappe

def add_total_operation_cost(doc):
    operation_cost = get_operation_cost(doc.work_order)
    expense_account = frappe.get_doc("Company", doc.company).custom_default_operating_cost

    if operation_cost:
        existing_entry = next(
            (entry for entry in doc.additional_costs if entry.description == "Operation Cost"), None
        )
        
        if not existing_entry:
            doc.append("additional_costs", {
                "expense_account": expense_account,
                "description": "Operation Cost",
                "amount": operation_cost
            })


def get_operation_cost(work_order):
    work_order_doc = frappe.get_doc("Work Order", work_order)
    operation_cost = work_order_doc.custom_total_operation_cost
    return operation_cost

def before_save(doc, method=None):
    if doc.work_order:
        add_total_operation_cost(doc)
    