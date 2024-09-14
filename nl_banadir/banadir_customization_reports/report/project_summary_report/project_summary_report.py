import frappe
from frappe import _
from frappe.query_builder import DocType

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    columns = [
        {
            "label": _("Project"), 
            "fieldname": "project", 
            "fieldtype": "HTML", 
            "options": "Project", 
            "width": 200
        },
        {
            "label": _("Task Name"),
            "fieldname": "subject",
            "fieldtype": "Link",
            "options": "Task",
            "width": 200
        },
        {
            "label": _("Task Status"),
            "fieldname": "task_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": "Item Code", 
            "fieldname": "item_code", 
            "fieldtype": "Data", 
            "width": 200
        },
        {
            "label": "UOM", 
            "fieldname": "uom", 
            "fieldtype": "Link", 
            "options": "UOM", 
            "width": 100
        },
        {
            "label": "Currency", 
            "fieldname": "currency", 
            "fieldtype": "Link", 
            "options": "Currency", 
            "width": 100
        },
        {
            "label": "Purchased Qty", 
            "fieldname": "purchased_qty", 
            "fieldtype": "HTML", 
            "width": 100
        },
        {
            "label": "Consumed Qty", 
            "fieldname": "consumed_qty", 
            "fieldtype": "HTML", 
            "width": 100
        },
        {
            "label": "Balance", 
            "fieldname": "balance_qty", 
            "fieldtype": "HTML", 
            "width": 100
        },
        {
            "label": "Purchase Rate", 
            "fieldname": "purchase_rate", 
            "fieldtype": "HTML", 
            "width": 100
        },
        {
            "label": "Purchased Amount", 
            "fieldname": "purchased_amount", 
            "fieldtype": "HTML", 
            "width": 150
        },
        {
            "label": "Stock Rate", 
            "fieldname": "stock_rate",
            "fieldtype": "HTML", 
            "width": 100
        },
        {
            "label": "Consumed Amount", 
            "fieldname": "consumed_amount", 
            "fieldtype": "HTML", 
            "width": 150
        }
    ]

    if filters.get("purchased_only"):
        columns = [
            {
                "label": _("Project"), 
                "fieldname": "project", 
                "fieldtype": "HRML", 
                "options": "Project", 
                "width": 200
            },
            {
                "label": _("Task Name"),
                "fieldname": "subject",
                "fieldtype": "Link",
                "options": "Task",
                "width": 200
            },
            {
                "label": _("Task Status"),
                "fieldname": "task_status",
                "fieldtype": "HTML",
                "width": 100
            },
            {
                "label": "Item Code", 
                "fieldname": "item_code", 
                "fieldtype": "Data", 
                "width": 200
            },
            {
                "label": "UOM", 
                "fieldname": "uom", 
                "fieldtype": "Link", 
                "options": "UOM", 
                "width": 100
            },
            {
                "label": "Currency", 
                "fieldname": "currency", 
                "fieldtype": "Link", 
                "options": "Currency", 
                "width": 100
            },
            {
                "label": "Purchased Qty", 
                "fieldname": "purchased_qty", 
                "fieldtype": "HTML", 
                "width": 100
            },
            {
                "label": "Purchase Rate", 
                "fieldname": "purchase_rate", 
                "fieldtype": "HTML", 
                "width": 100
            },
            {
                "label": "Purchased Amount", 
                "fieldname": "purchased_amount", 
                "fieldtype": "HTML", 
                "width": 150
            }
        ]
    
    return columns

def get_purchase_invoice_items(project_name, company_filter=None):

    PurchaseInvoice = DocType("Purchase Invoice")
    PurchaseInvoiceItem = DocType("Purchase Invoice Item")
    
    # Build the query
    query = (
        frappe.qb.from_(PurchaseInvoiceItem)
        .inner_join(PurchaseInvoice)
        .on(PurchaseInvoiceItem.parent == PurchaseInvoice.name)
        .select(
            PurchaseInvoiceItem.item_code,
            PurchaseInvoiceItem.uom,
            PurchaseInvoiceItem.qty,
            PurchaseInvoiceItem.rate,
            PurchaseInvoiceItem.amount,
            PurchaseInvoice.currency,
        )
        .where(
            (PurchaseInvoice.project == project_name) &
            (PurchaseInvoice.docstatus == 1)
        )
    )
    
    # Add company filter conditionally
    if company_filter:
        query = query.where(PurchaseInvoice.company == company_filter)

    # Execute the query and return as a list of dictionaries
    purchase_invoice_items = query.run(as_dict=True)
    
    return purchase_invoice_items


def get_stock_entry_details(project_name, company_filter=None):
    StockEntry = DocType("Stock Entry")
    StockEntryDetail = DocType("Stock Entry Detail")

    # Build the query
    query = (
        frappe.qb.from_(StockEntryDetail)
        .inner_join(StockEntry)
        .on(StockEntryDetail.parent == StockEntry.name)
        .select(
            StockEntryDetail.item_code,
            StockEntryDetail.uom,
            StockEntryDetail.qty,
            StockEntryDetail.basic_rate.as_("rate"),
            StockEntryDetail.amount,
        )
        .where(
            (StockEntry.project == project_name) &
            (StockEntry.docstatus == 1) &
            (StockEntry.stock_entry_type == 'Material Transfer')
        )
    )
    
    # Add company filter conditionally
    if company_filter:
        query = query.where(StockEntry.company == company_filter)

    # Execute the query and return as a list of dictionaries
    stock_entry_details = query.run(as_dict=True)
    
    return stock_entry_details


def get_tasks(project_name):

    tasks = frappe.get_all(
        "Task",
        filters={"project": project_name},
        fields=["subject", "status"],
        order_by="subject asc"
    )

    return tasks

def get_data(filters):
    data = []

    project_filter = filters.get("project")
    company_filter = filters.get("company")

    if not project_filter:
        # Fetch all Projects
        projects = frappe.get_all("Project", fields=["name"])
    else:
        projects = frappe.get_all("Project", filters={"name": project_filter}, fields=["name"])
    
    for project in projects:
        project_name = project.name

        # Initialize data containers
        purchase_data = {}
        stock_data = {}
        tasks = get_tasks(project_name)

        # Fetch Purchase Invoice Items linked to the Project and Company
        purchase_invoice_items = get_purchase_invoice_items(project_name, company_filter)

        for pi in purchase_invoice_items:
            item_code = pi.item_code
            currency_symbol = get_currency(pi.currency)
            if item_code not in purchase_data:
                purchase_data[item_code] = {
                    'purchased_qty': 0, 
                    'rate': pi.rate, 
                    'purchased_amount': 0, 
                    'uom': pi.uom, 
                    'currency_symbol': currency_symbol
                }
            
            purchase_data[item_code]['purchased_qty'] += pi.qty
            purchase_data[item_code]['purchased_amount'] += pi.amount

        # Fetch Stock Entries of type Material Transfer linked to the Project and Company
        stock_entry_details = get_stock_entry_details(project_name, company_filter)

        for se in stock_entry_details:
            item_code = se.item_code
            if item_code not in stock_data:
                 stock_data[item_code] = {
                    'consumed_qty': 0, 
                    'stock_rate': se.rate, 
                    'consumed_amount': 0, 
                    'uom': se.uom
                 }

            stock_data[item_code]['consumed_qty'] += se.qty
            stock_data[item_code]['consumed_amount'] += se.amount

        # Initialize total variables for project summary
        total_purchased_qty = 0
        total_consumed_qty = 0
        total_purchased_amount = 0
        total_consumed_amount = 0

        # Combine Data
        item_codes = set(purchase_data.keys()).union(stock_data.keys())

        # Determine the maximum length to iterate
        max_length = max(len(item_codes), len(tasks))
        item_code_list = list(item_codes)
        
        for i in range(max_length):
            # Handle task data
            if i < len(tasks):
                subject = tasks[i].get("subject")
                task_status = tasks[i].get("status")
            else:
                subject, task_status = "", ""

            # Handle item data
            if i < len(item_code_list):
                item_code = item_code_list[i]
                purchased_qty = purchase_data.get(item_code, {}).get('purchased_qty', 0)
                purchase_rate = purchase_data.get(item_code, {}).get('rate', 0)
                purchased_amount = purchase_data.get(item_code, {}).get('purchased_amount', 0)
                uom = purchase_data.get(item_code, {}).get('uom', stock_data.get(item_code, {}).get('uom', ''))
                currency_symbol = purchase_data.get(item_code, {}).get('currency_symbol', '')

                consumed_qty = stock_data.get(item_code, {}).get('consumed_qty', 0)
                stock_rate = stock_data.get(item_code, {}).get('stock_rate', 0)
                consumed_amount = stock_data.get(item_code, {}).get('consumed_amount', 0)

                balance_qty = purchased_qty - consumed_qty
            else:
                # Empty item columns if there are more tasks than items
                item_code = ""
                purchased_qty = ""
                purchase_rate = ""
                purchased_amount = ""
                uom = ""
                currency_symbol = ""
                consumed_qty = ""
                stock_rate = ""
                consumed_amount = ""
                balance_qty = ""

            # Add data row with both task and item data
            data.append({
                'project': f"<a href='/app/project/{project_name}'>{project_name}</a>",
                'item_code': item_code,
                'uom': uom,
                'purchased_qty': f"{purchased_qty:,.2f}" if purchased_qty else "",
                'purchase_rate': f"{currency_symbol} {purchase_rate:,.2f}" if purchase_rate else "",
                'purchased_amount': f"{currency_symbol} {purchased_amount:,.2f}" if purchased_amount else "",
                'consumed_qty': f"{consumed_qty:,.2f}" if consumed_qty else "",
                'stock_rate': f"{currency_symbol} {stock_rate:,.2f}" if stock_rate else "",
                'consumed_amount': f"{currency_symbol} {consumed_amount:,.2f}" if consumed_amount else "",
                'balance_qty': f"{balance_qty:,.2f}" if balance_qty else "",
                'subject': subject,
                'task_status': task_status,
                'currency': currency_symbol
            })

            # Accumulate totals for the project
            if purchased_qty:
                total_purchased_qty += purchased_qty
            if consumed_qty:
                total_consumed_qty += consumed_qty
            if purchased_amount:
                total_purchased_amount += purchased_amount
            if consumed_amount:
                total_consumed_amount += consumed_amount

        # Add a summary row for the project
        balance_qty = total_purchased_qty - total_consumed_qty
        data.append({
            'project': f"<b><a href='/app/project/{project_name}'>Total for {project_name}</a></b>",
            'item_code': "",
            'uom': "",
            'purchased_qty': f"<b>{total_purchased_qty:,.2f}</b>",
            'purchase_rate': "",
            'purchased_amount': f"<b> {currency_symbol} {total_purchased_amount:,.2f}</b>",
            'consumed_qty': f"<b>{total_consumed_qty:,.2f}</b>",
            'stock_rate': "",
            'consumed_amount': f"<b>{currency_symbol} {total_consumed_amount:,.2f}</b>",
            'balance_qty': f"<b>{balance_qty:,.2f}</b>",
            'subject': "",
            'task_status': "",
            'currency': currency_symbol
        })

    return data

def get_currency(currency):
    return frappe.db.get_value("Currency", currency, "symbol") or ""
