import frappe

@frappe.whitelist()
def get_items_from_production_plan(production_plan):
    """
    Fetch items and quantities from all Work Orders associated with the given Production Plan.
    """
    work_orders = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan},
        fields=["name", "production_item", "qty"]
    )

    items = []
    for work_order in work_orders:
        items.append({
            "item_code": work_order.production_item,
            "quantity": work_order.qty,
            "work_order": work_order.name,
            "fg_item_qty": work_order.qty,
        })
    frappe.response['message'] = items
    return items

'''I am against this method: how will we know 
the specific work order to get the quantity from?'''

# @frappe.whitelist()
# def get_qty_from_first_work_order(production_plan):
#     """
#     Fetch items and quantities from the first Work Order associated with the given Production Plan.
#     """
#     work_order = frappe.get_all(
#         "Work Order",
#         filters={"production_plan": production_plan},
#         fields=["name", "production_item", "qty"],
#         order_by="creation",
#         limit_page_length=1
#     )

#     if work_order:
#         frappe.response["message"]=work_order[0].qty
#     else:
#         return None
    
@frappe.whitelist()
def get_qty_from_first_work_order(production_plan):
    """
    Fetch items and quantities from the first Work Order associated with the given Production Plan.
    Additionally, fetch items from the 'required_materials' child table where 'custom_item_group' is 'UPPER STOCK'.
    """
    # Get the first Work Order associated with the Production Plan
    work_order = frappe.get_all(
        "Work Order",
        filters={"production_plan": production_plan},
        fields=["name", "production_item", "qty"],
        order_by="creation",
        limit_page_length=1
    )
    
    if work_order:
        # Initialize response with the quantity from the first Work Order
        response = {
            "work_order_qty": work_order[0].qty,
            "upper_stock_items": []
        }
        
        # Get the child table items where 'custom_item_group' is 'UPPER STOCK'
        required_materials = frappe.get_all(
            "Work Order Item",
            filters={
                "parent": work_order[0].name,
                "custom_item_group": "UPPER STOCK"
            },
            fields=["item_code"]
        )
        
        # Extract item codes and add them to the response
        if required_materials:
            response["upper_stock_items"] = required_materials[0]["item_code"]
        # Set the response message
        frappe.response["message"] = response


