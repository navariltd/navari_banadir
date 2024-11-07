import frappe
from erpnext.accounts.utils import get_balance_on
from frappe.utils import today

def before_save(doc, method=None):
    if doc.voucher_type in ["Cash Entry","Bank Entry","Journal Entry"]:
        company_currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
        for account in doc.accounts:
            account_type = frappe.get_cached_value('Account', account.account, 'account_type')

            # Check if account type is Cash or Bank
            if account_type in ["Cash", "Bank"]:
                account_balance = abs(get_balance_on(account.account, date=today()))

                # Convert balance if the account currency is different from company currency
                if account.account_currency != company_currency:
                    account_balance = float(account_balance) * float(account.exchange_rate)

                # Check if a credit transaction is happening and validate balance
                if account.credit is not None and account.credit > 0:
                    difference_balance = account_balance - account.credit
                    if difference_balance < 0.0:
                        frappe.throw(f"Transaction can't be completed for account {account.account}. Your cash/bank balance is {account_balance} 😊")
