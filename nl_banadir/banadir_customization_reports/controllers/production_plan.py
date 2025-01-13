# Server script to synchronize custom_seq_id and continue from the last sequence in Production Plan Item
# Trigger: `on_save` of the Production Plan doctype
import frappe
from frappe.model.naming import make_autoname
from datetime import datetime

def sync_sequence(doc, method):
    """
    Synchronize custom_seq_id between po_items and sub_assembly_items,
    ensuring sequence continues from the last value in Production Plan Item.
    """
    last_seq_id = frappe.db.sql("""
        SELECT MAX(custom_seq_id) 
        FROM `tabProduction Plan Item`
    """)[0][0] or 0  # Default to 0 if no records exist

    current_seq_id = last_seq_id + 1
    
    if len(doc.po_items) != len(doc.sub_assembly_items):
        frappe.throw("The number of items in 'Assembly Items' and 'Sub Assembly Items' must be equal.")

    for idx in range(len(doc.po_items)):
        doc.po_items[idx].custom_seq_id = current_seq_id
        doc.sub_assembly_items[idx].custom_seq_id = current_seq_id
        # Update directly in the database using set_value
        frappe.db.set_value("Production Plan Item", doc.po_items[idx].name, "custom_seq_id", current_seq_id)
        frappe.db.set_value("Production Plan Sub Assembly Item", doc.sub_assembly_items[idx].name, "custom_seq_id", current_seq_id)

        current_seq_id += 1
        
def auto_name(doc, method=None):
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if not company_abbr:
        frappe.throw(f"Company abbreviation not found for {doc.company}")

    current_year = datetime.now().year

    if doc.doctype == "Production Plan":
        base_name = make_autoname(f"PP-{company_abbr}-.####")
        doc.name = f"{base_name}-{current_year}"
    elif doc.doctype == "Work Order":
        base_name = make_autoname(f"WO-{company_abbr}-.#####")
        doc.name = f"{base_name}-{current_year}"
    else:
        frappe.throw(f"Unsupported doctype: {doc.doctype}")
        
    if doc.doctype=="Work Order":
        if doc.production_plan_item:
            doc.custom_seq_id = get_seq_id(doc.production_plan_item, "Production Plan Item")
        elif doc.production_plan_sub_assembly_item:
            doc.custom_seq_id = get_seq_id(doc.production_plan_sub_assembly_item, "Production Plan Sub Assembly Item")

def get_seq_id(_item, doc):
    """
    Get the sequence ID for the given Production Plan Item.
    """
    seq_id = frappe.db.get_value(
        doc,
        _item,
        "custom_seq_id"
    )
    return seq_id

