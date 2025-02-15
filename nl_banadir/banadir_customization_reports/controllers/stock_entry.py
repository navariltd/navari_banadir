
import frappe

def add_total_operation_cost(doc):
    operation_cost = get_operation_cost(doc.work_order)
    _account = frappe.get_doc("Company", doc.company)
    expense_account= _account.default_operating_cost_account
    if not expense_account:
        frappe.throw("Go to company and enter the respective default Operating Cost Account")
    
    if operation_cost:
        existing_entry = next(
            (entry for entry in doc.additional_costs if entry.description == "Operation Cost"), None
        )
        
        if not existing_entry:
            doc.append("additional_costs", {
                "expense_account": expense_account,
                "description": "Operation Cost",
                "amount": operation_cost,
                "base_amount":operation_cost
            })


def get_operation_cost(work_order):
    work_order_doc = frappe.get_doc("Work Order", work_order)
    operation_cost = work_order_doc.custom_total_operation_cost
    return operation_cost

def before_save(doc, method=None):
    if doc.work_order and doc.stock_entry_type=="Manufacture":
        add_total_operation_cost(doc)

@frappe.whitelist(allow_guest=False)
def get_default_stock_uom(item_code):
    item = frappe.get_doc("Item", item_code)
    if item.custom_default_stock_uom:
        return item.custom_default_stock_uom
    else:
        return item.stock_uom