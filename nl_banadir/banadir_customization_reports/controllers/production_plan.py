# Server script to synchronize custom_seq_id and continue from the last sequence in Production Plan Item
# Trigger: `on_save` of the Production Plan doctype
import frappe
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
        doc.sub_assembly_items[idx].seq_id = current_seq_id
        current_seq_id += 1


