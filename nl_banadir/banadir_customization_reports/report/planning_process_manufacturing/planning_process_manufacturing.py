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
        {"label": "Item Name (Finished Goods)", "fieldname": "finished_goods_item", "fieldtype": "Link","options":"Item", "width": 200},
        {"label": "Item Name (Insole)", "fieldname": "insole_item","fieldtype": "Link","options":"Item", "width": 200},
        {"label": "Item Name (Upper)", "fieldname": "upper_item", "fieldtype": "Link","options":"Item", "width": 200},
        {"label": "Order/Pairs", "fieldname": "order_pairs", "fieldtype": "Int", "width": 100},
        {"label": "Date of Issue(In Progress)", "fieldname": "in_progress_date", "fieldtype": "Date", "width": 120},
        {"label": "Qty Issued", "fieldname": "qty_issued", "fieldtype": "float", "width": 120},

        {"label": "Date of Cutting", "fieldname": "date_of_cutting", "fieldtype": "Date", "width": 120},
        {"label": "Cutting Pairs", "fieldname": "cutting_pairs", "fieldtype": "Int", "width": 120},
        {"label": "Cutting Contractor", "fieldname": "cutting_contractor", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Balance to Cut", "fieldname": "balance_to_cut", "fieldtype": "Int", "width": 120},
        {"label": "Date of Printing & Embossing", "fieldname": "date_of_printing_embossing", "fieldtype": "Date", "width": 150},
        {"label": "Qty Issued(Printing)", "fieldname": "qty_issued_printing", "fieldtype": "float", "width": 120},
        {"label": "Printed & Embossed Pairs", "fieldname": "printed_embossed_pairs", "fieldtype": "Int", "width": 150},
        {"label": "Printing/Embossing Contractor", "fieldname": "printing_embossing_contractor", "fieldtype": "Link", "options": "Supplier", "width": 200},
        {"label": "Balance to Print/Emboss", "fieldname": "balance_to_print_emboss", "fieldtype": "Int", "width": 150},
        {"label": "Insole Stock", "fieldname": "insole_stock_qty", "fieldtype": "Float", "width": 120},
        {"label": "Issued Date to Subcontractor", "fieldname": "issued_date", "fieldtype": "Date", "width": 150},
        {"label": "Subcontractor Name", "fieldname": "subcontractor_name_po", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Quantity Issued", "fieldname": "quantity_issued", "fieldtype": "Int", "width": 120},
        {"label": "Received Quantity", "fieldname": "received_quantity", "fieldtype": "Int", "width": 120},
        {"label": "Balance Quantity", "fieldname": "balance_quantity", "fieldtype": "Int", "width": 120},
        {"label": "Upper Stock", "fieldname": "upper_stock", "fieldtype": "Int", "width": 120},
        {"label":"Qty Issued(Machine)", "fieldname":"qty_issued_machine", "fieldtype":"Int", "width":120},
        {"label":"Fresh Qty", "fieldname":"fresh_qty_issued", "fieldtype":"Int", "width":120},
                {"label":"B Qty", "fieldname":"b_qty_issued", "fieldtype":"Int", "width":120},

        {"label":"Rejected Qty", "fieldname":"rejected_qty_issued", "fieldtype":"Int", "width":120},
        {"label":"Balance(In Machine)", "fieldname":"balance_to_issue", "fieldtype":"Int", "width":120},
                {"label":"Stock Entry", "fieldname":"stock_entry", "fieldtype":"Link","options":"Stock Entry", "width":120},
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
            required_items.item_code AS upper_item,
            fg_work_order.qty AS order_pairs,
            cso.in_progress_date AS in_progress_date,
            (cso.qty_issued - cso.completed_qty) AS balance_to_cut,
            (csp.qty_issued - csp.completed_qty) AS balance_to_print_emboss,
            cso.completed_date AS date_of_cutting,
            cso.supplier AS cutting_contractor,
            cso.completed_qty AS cutting_pairs,
            csp.completed_date AS date_of_printing_embossing,
            csp.completed_qty AS printed_embossed_pairs,
            csp.supplier AS printing_embossing_contractor,
            csp.qty_issued AS qty_issued_printing,
            mp.qty_issued AS qty_issued_machine,
            # '' AS balance_to_print_emboss,
            '' AS insole_stock,
            '' AS issued_date,
            cso.qty_issued AS qty_issued,
            (cso.completed_qty - cso.qty_issued) AS balance_quantity,
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
             ON insole_work_order.name = cso.parent AND cso.operations = 'Cutting'
        LEFT JOIN
            `tabWork Order Operations Item` csp 
             ON insole_work_order.name = csp.parent AND csp.operations = 'Printing & Embosing'
        LEFT JOIN
        `tabWork Order Operations Item` mp 
            ON fg_work_order.name = mp.parent AND mp.operations = 'MOULDING & PACKING'
        LEFT JOIN
            `tabWork Order Item` required_items 
             ON fg_work_order.name = required_items.parent
             AND required_items.custom_item_group = 'UPPER STOCK'
        WHERE
            {condition_query}
    """
    result= frappe.db.sql(query, as_dict=True)
    main_data = [add_insole_stock_data(record) for record in result]
    [update_insole_stock_qty(record) for record in main_data]
    [update_stock_details(record) for record in main_data]
    return main_data

def add_insole_stock_data(record):
    """
    Fetch and add insole stock data to a given record based on its finished goods work order.

    :param record: Dictionary containing data of the main record.
    :return: Updated record with insole stock data.
    """
    finished_goods_work_order_no = record.get("finished_goods_work_order_no")
    
    if not finished_goods_work_order_no:
        return record

    purchase_order_data = frappe.db.sql(
        f"""
        SELECT
    poi.qty AS issued_qty,
    poi.fg_item AS insole_stock_item,
    po.name AS purchase_order,
    po.supplier AS subcontractor_name_po,
    po.transaction_date AS issued_date
FROM
    `tabPurchase Order Item` poi
JOIN
    `tabPurchase Order` po ON poi.parent = po.name
WHERE
    poi.custom_work_order = '{finished_goods_work_order_no}'
    AND po.docstatus = '1'

        """,
        as_dict=True,
    )
    if purchase_order_data:
        insole_data = purchase_order_data[0]
        subcontracting_order = frappe.db.get_value(
            "Subcontracting Order",
            {"purchase_order": insole_data["purchase_order"]},
            "name",
        )
        
        receipt = frappe.db.sql(
            f"""
            SELECT
                SUM(sci.qty) AS received_quantity,
                sci.item_code AS upper_stock
            FROM
                `tabSubcontracting Receipt Item` sci
            JOIN
                `tabSubcontracting Receipt` sr ON sci.parent = sr.name
            WHERE
                sci.subcontracting_order = '{subcontracting_order}'
            """,
            as_dict=True,
        )

        received_qty = receipt[0].received_quantity if receipt else 0
        balance_quantity = insole_data["issued_qty"] - received_qty

        upper_stock = received_qty - record.get("qty_issued_machine")
        record.update(
            {
                "quantity_issued": insole_data["issued_qty"],
                "issued_date": insole_data["issued_date"],
                "received_quantity": received_qty,
                "balance_quantity": balance_quantity,
                "subcontractor_name_po": insole_data["subcontractor_name_po"],
                "upper_stock": upper_stock,
            }
        )
    else:
        record.update(
            {
                "quantity_issued": 0,
                "received_quantity": 0,
                "balance_quantity": 0,
                "subcontractor_name_po": None,
                "upper_stock": None,
                "issued_date": None,
            }
        )
  
    record.update({
        "upper_item": update_upper_stock_item(finished_goods_work_order_no),
    })
    return record

def update_upper_stock_item(finished_goods_work_order_no):
    work_order=frappe.get_doc("Work Order",finished_goods_work_order_no)
    required_items = work_order.get("required_items")
    for item in required_items:
        item_doc = frappe.get_doc("Item", item.item_code)
        
        if item_doc.item_group == "UPPER STOCK":
            return item.item_code
    
    
def update_insole_stock_qty(record):
    printed_embossed_pairs = record.get("printed_embossed_pairs") or 0
    quantity_issued = record.get("quantity_issued") or 0

    if isinstance(printed_embossed_pairs, (int, float)) and isinstance(quantity_issued, (int, float)):
        record["insole_stock_qty"] = printed_embossed_pairs - quantity_issued
    else:
        raise ValueError("Fields 'printed_embossed_pairs' and 'quantity_issued' must be numeric.")
    

def update_stock_details(record):
    finished_goods_work_order = record.get("finished_goods_work_order_no")
    fresh_qty_issued = record.get("fresh_qty_issued") or 0
    qty_issued_machine = record.get("qty_issued_machine") or 0
    stock_entry = frappe.db.get_value("Stock Entry", {"work_order": finished_goods_work_order, "docstatus": 1}, "name")
    
    if not stock_entry:
        return record
    
    stock_entry_doc = frappe.get_doc("Stock Entry", stock_entry)
    stock_entry_items = stock_entry_doc.get("items")
    
    # Initialize variables to avoid UnboundLocalError
    rejected_qty_issued = 0
    is_finished_item_qty = 0
    b_qty_issued = 0
    
    for item in stock_entry_items:
        if item.item_group == "Rejection Items India":
            rejected_qty_issued += item.qty or 0
        if item.is_finished_item == 1:
            is_finished_item_qty = item.qty or 0
        if item.item_group == "B STOCK":
            b_qty_issued += item.qty
    
    record.update({
        "stock_entry": stock_entry,
        "rejected_qty_issued": rejected_qty_issued,
        "fresh_qty_issued":is_finished_item_qty,
        "b_qty_issued": b_qty_issued,
        "balance_to_issue": qty_issued_machine - (is_finished_item_qty + rejected_qty_issued),
    })
    return record
