import frappe
from erpnext.accounts.utils import get_balance_on
from frappe.utils import today

def before_save(doc, method=None):
    for account in doc.accounts:
        # Check if the word "cash" is in the account field (case-insensitive)
        if "cash" in account.account.lower():
            account_balance = abs(get_balance_on(account.account, date=today()))
            if account.debit is not None and account.debit > 0:
                difference_balance = account_balance - account.debit
                if difference_balance <= 0:
                    frappe.throw(f"Transaction can't be completed for account {account.account}. Check your cash balance.")

            # If a credit amount is provided, calculate balance after credit
            elif account.credit is not None and account.credit > 0:
                difference_balance = account_balance - account.credit
                if difference_balance <= 0:
                    frappe.throw(f"Transaction can't be completed for account {account.account}. Check your cash balance.")
