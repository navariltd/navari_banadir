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
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Item Name (Finished Goods)", "fieldname": "finished_goods_item", "fieldtype": "Data", "width": 200},
        {"label": "Item Name (Insole)", "fieldname": "insole_item", "fieldtype": "Data", "width": 200},
        {"label": "Item Name (Upper)", "fieldname": "upper_item", "fieldtype": "Data", "width": 200},
        {"label": "Order/Pairs", "fieldname": "order_pairs", "fieldtype": "Int", "width": 100},
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

    condition_query = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            ppso.sales_order AS sales_order_no,
            pp.name AS production_plan_no,
            # ppi.work_order AS finished_goods_work_order_no,
            # psa.work_order AS insole_work_order,
            pp.status AS status,
            ppi.item_code AS finished_goods_item,
            psa.production_item  AS insole_item,
            psa.parent_item_code AS upper_item,
            pp.total_planned_qty AS order_pairs,
            '' AS date_of_cutting,
            '' AS cutting_pairs,
            '' AS cutting_contractor,
            '' AS balance_to_cut,
            '' AS date_of_printing_embossing,
            '' AS printed_embossed_pairs,
            '' AS printing_embossing_contractor,
            '' AS balance_to_print_emboss,
            '' AS insole_stock,
            '' AS issued_date,
            '' AS subcontractor_name,
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
            `tabProduction Plan Sub Assembly Item` psa ON pp.name = psa.parent
        WHERE
            {condition_query}
    """
    return frappe.db.sql(query, as_dict=True)
