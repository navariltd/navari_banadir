import frappe

def create_todo_and_share(doc, party_doc, reference_type):
    emails = [user for user in party_doc.custom_account_managers]
    
    for email in emails:
        new_assign = frappe.get_doc({
            "doctype": "ToDo",
            "allocated_to": email.user,
            "reference_type": reference_type,
            "reference_name": doc.name,
            "description": f"New {reference_type.lower().replace(' ', '_')} created {doc.name}",
            "priority": "Medium",
            "date": doc.posting_date,
            "assigned_by": doc.owner
        }).insert(ignore_permissions=True)

    for email in emails:
        user = email.user
        if user:
            frappe.share.add_docshare(
                doc.doctype, doc.name, user, write=1, submit=1, share=1, flags={"ignore_share_permission": True}
            )

def sales_invoice_before_submit(doc, method=None):
    customer_doc = frappe.get_doc("Customer", doc.customer)
    create_todo_and_share(doc, customer_doc, "Sales Invoice")

def purchase_invoice_before_submit(doc, method=None):
    supplier_doc = frappe.get_doc("Supplier", doc.supplier)
    create_todo_and_share(doc, supplier_doc, "Purchase Invoice")

def payment_entry_before_submit(doc, method=None):
    if doc.party_type in ["Customer", "Supplier"]:
        party_doc = frappe.get_doc(doc.party_type, doc.party)
        create_todo_and_share(doc, party_doc, "Payment Entry")

def journal_entry_before_submit(doc, method=None):
    if doc.is_system_generated==0:
        for account in doc.accounts:
            if account.get("party_type") in ["Customer", "Supplier"]:
                party_doc = frappe.get_doc(account.get("party_type"), account.get("party"))
                create_todo_and_share(doc, party_doc, "Journal Entry")
