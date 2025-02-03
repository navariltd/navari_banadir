# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    """ Main function for report execution. """
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    """ Returns the report column structure. """
    return [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 120},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "From Warehouse", "fieldname": "from_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "To Warehouse", "fieldname": "to_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "Transferred Qty", "fieldname": "qty", "fieldtype": "Float", "width": 120},
        {"label": "Current Qty in Destination", "fieldname": "current_qty", "fieldtype": "Float", "width": 150}
    ]

def get_conditions(filters):
    """ Generates SQL conditions dynamically based on filters. """
    conditions = ["se.docstatus = 1", "se.stock_entry_type = 'Material Transfer'"]
    values = {}

    if filters.get("from_date"):
        conditions.append("se.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("se.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("from_warehouse"):
        conditions.append("sed.s_warehouse = %(from_warehouse)s")
        values["from_warehouse"] = filters["from_warehouse"]

    if filters.get("to_warehouse"):
        conditions.append("sed.t_warehouse = %(to_warehouse)s")
        values["to_warehouse"] = filters["to_warehouse"]

    if filters.get("company"):
        conditions.append("se.company = %(company)s")
        values["company"] = filters["company"]

    return " AND ".join(conditions), values

def get_data(filters):
    """ Fetches data based on filters. """
    conditions, values = get_conditions(filters)

    query = f"""
        SELECT 
            se.posting_date, 
            se.name AS stock_entry, 
            sed.item_code, 
            sed.item_name, 
            sed.s_warehouse AS from_warehouse, 
            sed.t_warehouse AS to_warehouse, 
            sed.qty,
            (SELECT actual_qty FROM `tabBin` WHERE item_code = sed.item_code AND warehouse = sed.t_warehouse) AS current_qty
        FROM `tabStock Entry` se
        JOIN `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE {conditions}
        ORDER BY se.posting_date DESC
    """

    return frappe.db.sql(query, values, as_dict=True)
