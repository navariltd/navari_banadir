import frappe
from frappe.model.naming import make_autoname
from datetime import datetime

def auto_name(doc, method=None):
    company_abbr = frappe.db.get_value("Company", doc.company, "abbr")
    if not company_abbr:
        frappe.throw(f"Company abbreviation not found for {doc.company}")

    current_year = datetime.now().year

    if doc.company == "GL GENERAL TRADING Mogadishu":
        base_name = make_autoname(f"{company_abbr}-.####")
        doc.name = f"{base_name}"
   
  