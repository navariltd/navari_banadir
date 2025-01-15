from datetime import datetime
from frappe.model.naming import make_autoname
import frappe

def auto_name(doc, method=None):
    if doc.company=="Banadir Steel LTD":
        company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
        if not company_abbr:
            frappe.throw(f"Company abbreviation not found for {doc.company}")

        current_year = datetime.now().year

        base_name = make_autoname(f"{company_abbr}-.####")
        doc.name = f"{base_name}-{current_year}"
    