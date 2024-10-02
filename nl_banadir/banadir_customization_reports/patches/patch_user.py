import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "User": [
            {
                "fieldname": "user_signature",
                "label": "Signature",
                "fieldtype": "Attach",
                "insert_after": "username",
            }
        ]
    }

    create_custom_fields(custom_fields)