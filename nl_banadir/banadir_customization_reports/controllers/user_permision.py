import frappe



def disallow_user_access(user, doctype, docname):
    """
    Disallows the specified user from accessing the specified document.
    Removes any existing User Permission for this document.
    """
    # Check if a User Permission exists for the given user, doctype, and document
    user_perm = frappe.get_all(
        "User Permission",
        filters={
            "user": user,
            "allow": doctype,
            "for_value": docname
        },
        fields=["name"]
    )

    if user_perm:
        # Delete the existing User Permission(s)
        for perm in user_perm:
            frappe.delete_doc("User Permission", perm.name)

        frappe.clear_cache(user=user)
        frappe.msgprint(f"User {user} has been disallowed access to {doctype} {docname}.")

    else:
        frappe.msgprint(f"No existing access found for user {user} to disallow.")
        

def custom_has_permission(doc, ptype="read", user=None):
    user = user or frappe.session.user
    restricted_invoices = ["00001", "00002"]  
    if ptype == "read" and doc.name in restricted_invoices:
        return False
    
    # Default behavior
    return True
