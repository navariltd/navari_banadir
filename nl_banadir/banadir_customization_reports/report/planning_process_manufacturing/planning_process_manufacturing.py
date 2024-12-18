# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

import frappe

'''Since there is a need to have finished goods and insole on the same line, they must have a corelation
Hence the report cannot work if the corelation doesn't exit.
The remaining solution will be to to bypass creation of work order and create our own with the sequence so that they can map.
'''
def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Sales Order No", "fieldname": "sales_order_no", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": "Production Plan No", "fieldname": "production_plan_no", "fieldtype": "Link", "options": "Production Plan", "width": 150},
        {"label": "Finished Goods Work Order No", "fieldname": "finished_goods_work_order_no", "fieldtype": "Link", "options": "Work Order", "width": 200},
        {"label": "Insole Work Order", "fieldname": "insole_work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": "Sequence No (Finished Goods)", "fieldname": "sequence_no", "fieldtype": "Data", "width": 150},  # Added column for sequence number
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Item Name (Finished Goods)", "fieldname": "finished_goods_item", "fieldtype": "Data", "width": 200},
        {"label": "Item Name (Insole)", "fieldname": "insole_item", "fieldtype": "Data", "width": 200},
        {"label": "Item Name (Upper)", "fieldname": "upper_item", "fieldtype": "Data", "width": 200},
        {"label": "Order/Pairs", "fieldname": "order_pairs", "fieldtype": "Int", "width": 100},
        {"label": "Date of Issue(In Progress)", "fieldname": "in_progress_date", "fieldtype": "Date", "width": 120},
        {"label": "Qty Issued", "fieldname": "qty_issued", "fieldtype": "float", "width": 120},

        {"label": "Date of Cutting", "fieldname": "date_of_cutting", "fieldtype": "Date", "width": 120},
        {"label": "Cutting Pairs", "fieldname": "cutting_pairs", "fieldtype": "Int", "width": 120},
        {"label": "Cutting Contractor", "fieldname": "cutting_contractor", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Balance to Cut", "fieldname": "balance_to_cut", "fieldtype": "Int", "width": 120},
        {"label": "Date of Printing & Embossing", "fieldname": "date_of_printing_embossing", "fieldtype": "Date", "width": 150},
        {"label": "Printed & Embossed Pairs", "fieldname": "printed_embossed_pairs", "fieldtype": "Int", "width": 150},
        {"label": "Printing/Embossing Contractor", "fieldname": "printing_embossing_contractor", "fieldtype": "Link", "options": "Supplier", "width": 200},
        {"label": "Balance to Print/Emboss", "fieldname": "balance_to_print_emboss", "fieldtype": "Int", "width": 150},
        {"label": "Insole Stock", "fieldname": "insole_stock", "fieldtype": "Int", "width": 120},
        {"label": "Issued Date to Subcontractor", "fieldname": "issued_date", "fieldtype": "Date", "width": 150},
        {"label": "Subcontractor Name", "fieldname": "subcontractor_name", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Quantity Issued", "fieldname": "quantity_issued", "fieldtype": "Int", "width": 120},
        {"label": "Received Quantity", "fieldname": "received_quantity", "fieldtype": "Int", "width": 120},
        {"label": "Balance Quantity", "fieldname": "balance_quantity", "fieldtype": "Int", "width": 120},
        {"label": "Upper Stock", "fieldname": "upper_stock", "fieldtype": "Int", "width": 120},
    ]

def get_data(filters):
    conditions = []
    if filters.get("production_plan"):
        conditions.append(f"pp.name = '{filters['production_plan']}'")
    if filters.get("sales_order"):
        conditions.append(f"ppso.sales_order = '{filters['sales_order']}'")
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(f"pp.transaction_date BETWEEN '{filters['from_date']}' AND '{filters['to_date']}'")
    if filters.get("status"):
        conditions.append(f"pp.status = '{filters['status']}'")
    condition_query = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            ppso.sales_order AS sales_order_no,
            pp.name AS production_plan_no,
            fg_work_order.name AS finished_goods_work_order_no,
            insole_work_order.name AS insole_work_order,
            fg_work_order.custom_seq_id AS sequence_no,  # Fetch the custom_seq_id for finished goods work order
            pp.status AS status,
            ppi.item_code AS finished_goods_item,
            psa.production_item AS insole_item,
            psa.parent_item_code AS upper_item,
            pp.total_planned_qty AS order_pairs,
            cso.in_progress_date AS in_progress_date,
            cso.completed_date AS date_of_cutting,
            cso.supplier AS cutting_contractor,
            cso.completed_qty AS cutting_pairs,
            '' AS balance_to_cut,
            csp.completed_date AS date_of_printing_embossing,
            csp.completed_qty AS printed_embossed_pairs,
            csp.supplier AS printing_embossing_contractor,
            '' AS balance_to_print_emboss,
            '' AS insole_stock,
            '' AS issued_date,
            '' AS quantity_issued,
            '' AS received_quantity,
            '' AS balance_quantity,
            '' AS upper_stock
        FROM
            `tabProduction Plan` pp
        LEFT JOIN
            `tabProduction Plan Sales Order` ppso ON pp.name = ppso.parent
        LEFT JOIN
            `tabProduction Plan Item` ppi ON pp.name = ppi.parent
        LEFT JOIN
            `tabProduction Plan Sub Assembly Item` psa 
             ON pp.name = psa.parent AND ppi.custom_seq_id = psa.custom_seq_id
        LEFT JOIN
             `tabWork Order` fg_work_order ON fg_work_order.production_plan_item = ppi.name
        LEFT JOIN
            `tabWork Order` insole_work_order ON insole_work_order.production_plan_sub_assembly_item = psa.name
        LEFT JOIN
            `tabWork Order Operations Item` cso 
             ON fg_work_order.name = cso.parent AND cso.operations = 'Cutting'
        LEFT JOIN
            `tabWork Order Operations Item` csp 
             ON fg_work_order.name = csp.parent AND csp.operations = 'Printing & Embosing'
        WHERE
            {condition_query}
    """
    result= frappe.db.sql(query, as_dict=True)
    # frappe.throw(str(result))
    return result
