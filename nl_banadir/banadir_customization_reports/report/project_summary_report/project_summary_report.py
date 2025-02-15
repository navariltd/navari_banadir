import frappe
from frappe import _
from frappe.query_builder import DocType
from erpnext.accounts.report.utils import convert
import frappe.utils


'''Since there is a need to have finished goods and insole on the same line, they must have a corelation
Hence the report cannot work if the corelation doesn't exit.
The remaining solution will be to to bypass creation of work order and create our own with the sequence so that they can map.
'''
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
            "label": "Item Code", 
            "fieldname": "item_code", 
            "fieldtype": "Link",
            "options": "Item",
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
                "label": "Item Code", 
                "fieldname": "item_code", 
                "fieldtype": "Link",
                "options": "Item",
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
    
    if filters.get("task_status"):
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
                "fieldname": "name",
                "fieldtype": "Link",
                "options": "Task",
                "width": 200
            },
            {
                "label": _("Task Status"),
                "fieldname": "task_status",
                "fieldtype": "HTML",
                "width": 130
            },
            {
                "label": _("Date"),
                "fieldname": "comment_date",
                "fieldtype": "Date",
                "width": 130
            },
            {
                "label": _("Comment"),
                "fieldname": "last_comment",
                "fieldtype": "HTML",
                "width": 300
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
    
    if company_filter:
        query = query.where(PurchaseInvoice.company == company_filter)

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
    
    if company_filter:
        query = query.where(StockEntry.company == company_filter)

    stock_entry_details = query.run(as_dict=True)
    
    return stock_entry_details


def get_tasks(company, project_name):

    tasks = frappe.get_all(
        "Task",
        filters={"project": project_name, "company": company},
        fields=["name", "subject", "status"],
        order_by="name asc"
    )

    task_order = [
        "FLOORING PLAN",
        "BUILDING MEASUREMENT",
        "2D PLAN",
        "FINALISE 2D PLAN",
        "3D PLAN",
        "APPROVAL 3D PLAN",
        "LIST OF MATERIALS",
        "PROCUREMENT PLAN",
        "DISPATCH PROCESS",
        "CONSTRUCTION DRAWING"
    ]

    def get_task_position(task_name):
        if task_name in task_order:
            return task_order.index(task_name)
        else:
            return len(task_order)
        
    tasks.sort(key=lambda task: get_task_position(task.name))

    # Fetch the last comment from the comments child table
    for task in tasks:
        last_comment = frappe.db.get_value(
            "Task Comments",
            filters={"parent": task.name},
            fieldname=["date", "comment"],
            order_by="date desc", 
            as_dict=True
        )
        task["last_comment"] = last_comment if last_comment else {}
    return tasks

def format_task_status(status):
    if status == "Open":
        return f"<span class='label' style='background-color: #d9edf7; color: #31708f; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    elif status == "Awaiting Approval":
        return f"<span class='label' style='background-color: #f2dede; color: #a94442; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    elif status == "Pending":
        return f"<span class='label' style='background-color: #f2dede; color: #a94442; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    elif status == "Completed":
        return f"<span class='label' style='background-color: #dff0d8; color: #3c763d; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    elif status == "On Hold":
        return f"<span class='label' style='background-color: #f5deb3; color: #8b4513; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    elif status == "On Process":
        return f"<span class='label' style='background-color: #fcf8e3; color: #f0ad4e; padding: 3px 12px; border-radius: 30px;'>{status}</span>"
    else:
        return f"<span class='label label-warning'>{status}</span>"

def get_conversion_rate(from_currency, to_currency, date):

    if from_currency == to_currency:
        return (1, None)

    conversion_rate = frappe.db.get_value(
        "Currency Exchange",
        {"from_currency": from_currency, "to_currency": to_currency},
        ["exchange_rate", "date"]
    )

    if conversion_rate:
        return conversion_rate[0], conversion_rate[1]
    else:
        # Try fetching the inverse exchange rate
        inverse_conversion_rate = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": to_currency, "to_currency": from_currency},
            ["exchange_rate", "date"]
        )

        if inverse_conversion_rate:
            inverse_exchange_rate = inverse_conversion_rate[0]
            return 1 / inverse_exchange_rate, inverse_conversion_rate[1]
        else:
            frappe.throw(
                _("Exchange rate not found for {0} to {1}").format(
                    from_currency, to_currency
                )
            )

def convert_currency(amount, from_currency, to_currency, date):
    conversion_rate, conversion_date = get_conversion_rate(from_currency, to_currency, date)
    return amount * conversion_rate

def get_data(filters):
    data = []

    currency_filter = filters.get("currency")
    project_filter = filters.get("project")
    company_filter = filters.get("company")
    task_filter = filters.get("task")

    if task_filter:
        # Fetch the project associated with the selected task
        task_doc = frappe.get_doc("Task", task_filter)
        project_filter = task_doc.project if task_doc.project else None

    if not project_filter:
        # Fetch all Projects if no project filter
        projects = frappe.get_all("Project", fields=["name"])
    else:
        projects = frappe.get_all("Project", filters={"name": project_filter}, fields=["name"])
    
    for project in projects:
        project_name = project.name

        # Initialize data containers
        purchase_data = {}
        stock_data = {}
        tasks = get_tasks(company_filter, project_name)

        purchase_invoice_items = get_purchase_invoice_items(project_name, company_filter)

        stock_entry_details = get_stock_entry_details(project_name, company_filter)

        if not purchase_invoice_items and not stock_entry_details and not tasks:
            continue
        
        
        for pi in purchase_invoice_items:
            item_code = pi.item_code
            currency_symbol = get_currency(pi.currency)

            if currency_filter and currency_filter != pi.currency:
                
                transaction_date = pi.posting_date if pi.posting_date else frappe.utils.nowdate()

                pi.rate = convert_currency(pi.rate, pi.currency, currency_filter, transaction_date)
                pi.amount = convert_currency(pi.amount, pi.currency, currency_filter, transaction_date)

                currency_symbol = get_currency(currency_filter)

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


        for se in stock_entry_details:
            item_code = se.item_code

            if currency_filter and currency_filter != se.currency:

                transaction_date = se.posting_date if se.posting_date else frappe.utils.nowdate()

                se.rate = convert_currency(se.rate, se.currency, currency_filter, transaction_date)
                se.amount = convert_currency(se.amount, se.currency, currency_filter, transaction_date)

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
                name = tasks[i].get("name")
                task_status = tasks[i].get("status")
                comment_date = tasks[i].get("last_comment", {}).get("date", "")
                last_comment = tasks[i].get("last_comment", {}).get("comment", "")
            else:
                name, task_status, comment_date, last_comment = "", "", "", ""

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
                'name': name,
                'task_status': f"{format_task_status(task_status)}" if task_status else "",
                'comment_date': comment_date,
                'last_comment': last_comment,
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
            'name': "",
            'task_status': "",
            'comment_date': "",
            'last_comment': "",
            'currency': currency_symbol
        })

    return data

def get_currency(currency):
    return frappe.db.get_value("Currency", currency, "symbol") or ""
