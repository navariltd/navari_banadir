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
            "fieldtype": "Link", 
            "options": "Project", 
            "width": 200
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
                "fieldtype": "Link", 
                "options": "Project", 
                "width": 200
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

        if item_codes:
            for item_code in item_codes:
                purchased_qty = purchase_data.get(item_code, {}).get('purchased_qty', 0)
                purchase_rate = purchase_data.get(item_code, {}).get('rate', 0)
                purchased_amount = purchase_data.get(item_code, {}).get('purchased_amount', 0)
                uom = purchase_data.get(item_code, {}).get('uom', stock_data.get(item_code, {}).get('uom', ''))
                currency_symbol = purchase_data.get(item_code, {}).get('currency_symbol', '')

                consumed_qty = stock_data.get(item_code, {}).get('consumed_qty', 0)
                stock_rate = stock_data.get(item_code, {}).get('stock_rate', 0)
                consumed_amount = stock_data.get(item_code, {}).get('consumed_amount', 0)

                balance_qty = purchased_qty - consumed_qty

                # Add data row for this item
                data.append({
                    'project': project_name,
                    'item_code': item_code,
                    'uom': uom,
                    'purchased_qty': f"{purchased_qty:,.2f}",
                    'purchase_rate': f"{currency_symbol} {purchase_rate:,.2f}",
                    'purchased_amount': f"{currency_symbol} {purchased_amount:,.2f}",
                    'consumed_qty': consumed_qty,
                    'stock_rate': f"{currency_symbol} {stock_rate:,.2f}" if stock_rate is not None else f"{currency_symbol} 0.00",
                    'consumed_amount': f"{currency_symbol} {consumed_amount:,.2f}",
                    'balance_qty': f"{balance_qty:,.2f}" if balance_qty is not None else f"0.00",
                    'currency': currency_symbol
                })

                # Accumulate totals for the project
                total_purchased_qty += purchased_qty
                total_consumed_qty += consumed_qty
                total_purchased_amount += purchased_amount
                total_consumed_amount += consumed_amount

            # Add a summary row for the project
            balance_qty = total_purchased_qty - total_consumed_qty
            data.append({
                'project': f"Total for {project_name}",
                'item_code': "",
                'uom': "",
                'purchased_qty': f"<b>{total_purchased_qty:,.2f}</b>",
                'purchase_rate': "",
                'purchased_amount': f"<b> {currency_symbol} {total_purchased_amount:,.2f}</b>",
                'consumed_qty': f"<b>{total_consumed_qty:,.2f}</b>",
                'stock_rate': "",
                'consumed_amount': f"<b>{currency_symbol} {total_consumed_amount:,.2f}</b>",
                'balance_qty': f"<b>{balance_qty:,.2f}</b>",
                'currency': currency_symbol
            })
        else:
            # Add an empty row for the project if no purchase or stock data is found
            data.append({
                'project': project_name,
                'item_code': "",
                'uom': "",
                'purchased_qty': "",
                'purchase_rate': "",
                'purchased_amount': "",
                'consumed_qty': "",
                'stock_rate': "",
                'consumed_amount': "",
                'balance_qty': "",
                'currency': ""
            })


    return data

def get_currency(currency):
    return frappe.db.get_value("Currency", currency, "symbol") or ""
