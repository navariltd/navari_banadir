# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

# import frappe

import frappe
from frappe import _, scrub
from frappe.utils import cint, flt

from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.utils import get_currency_precision, get_party_types_from_account_type
from erpnext.accounts.report.utils import convert


def execute(filters=None):
    args = {
        "account_type": "Receivable",
        "naming_by": ["Selling Settings", "cust_master_name"],
    }
    filters = filters or {}
    return AccountsReceivableSummary(filters).run(args)


class AccountsReceivableSummary(ReceivablePayableReport):
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.currency_conversion_rate = 1.0
        if self.filters.get("presentation_currency") and self.filters.get("exchange_date"):
            self.currency_conversion_rate = self.get_conversion_rate(
                self.filters.get("presentation_currency"),
                self.filters.get("exchange_date")
            )
        super().__init__(filters)


    def run(self, args):
        self.account_type = args.get("account_type")
        self.party_type = get_party_types_from_account_type(self.account_type)
        self.party_naming_by = frappe.db.get_value(args.get("naming_by")[0], None, args.get("naming_by")[1])
        self.get_columns()
        self.get_data(args)
        return self.columns, self.data

    def get_data(self, args):
        self.data = []
        self.receivables = ReceivablePayableReport(self.filters).run(args)[1]
        self.currency_precision = get_currency_precision() or 2

        self.get_party_total(args)

        party = None
        for party_type in self.party_type:
            if self.filters.get(scrub(party_type)):
                party = self.filters.get(scrub(party_type))

        party_advance_amount = (
            get_partywise_advanced_payment_amount(
                self.party_type,
                self.filters.report_date,
                self.filters.show_future_payments,
                self.filters.company,
                party=party,
            )
            or {}
        )

        if self.filters.show_gl_balance:
            gl_balance_map = get_gl_balance(self.filters.report_date, self.filters.company)

        for party, party_dict in self.party_total.items():
            if flt(party_dict.outstanding, self.currency_precision) == 0:
                continue

            row = frappe._dict()

            row.party = party
            if self.party_naming_by == "Naming Series":
                if self.account_type == "Payable":
                    doctype = "Supplier"
                    fieldname = "supplier_name"
                else:
                    doctype = "Customer"
                    fieldname = "customer_name"
                row.party_name = frappe.get_cached_value(doctype, party, fieldname)

            row.update(party_dict)

            
            # Advance against party
            row.advance = party_advance_amount.get(party, 0)

            # In AR/AP, advance shown in paid columns,
            # but in summary report advance shown in separate column
            row.paid -= row.advance

            if self.filters.show_gl_balance:
                row.gl_balance = gl_balance_map.get(party)
                row.diff = flt(row.outstanding) - flt(row.gl_balance)

            if self.filters.show_future_payments:
                row.remaining_balance = flt(row.outstanding) - flt(row.future_amount)

            self.data.append(row)

            # Helper function to find exchange rate
            def get_exchange_rate(from_currency, to_currency):

                if from_currency == to_currency:
                    return (1, None)
                
                # Try direct exchange rate
                conversion_rate = frappe.db.get_value(
                    "Currency Exchange",
                    {"from_currency": from_currency, "to_currency": to_currency},
                    ["exchange_rate", "date"],
                )

                if not conversion_rate:
                    # Try fetching the inverse exchange rate
                    conversion_rate = frappe.db.get_value(
                        "Currency Exchange",
                        {"from_currency": to_currency, "to_currency": from_currency},
                        ["exchange_rate", "date"],
                    )

                    if conversion_rate:
                        conversion_rate = (1 / conversion_rate[0], conversion_rate[1])

                return conversion_rate

            # Convert amounts to presentation currency
            if self.filters.get("presentation_currency"):
                
                from_currency = frappe.get_cached_value("Company", self.filters.company, "default_currency")
                
                to_currency = self.filters.get("presentation_currency")
                
                # Step 1: Try to get Direct or inverse conversion rate
                conversion_rate = get_exchange_rate(from_currency, to_currency)

                if not conversion_rate:

                    frappe.throw(
                        _("Exchange rate not found for {0} to {1}").format(
                            from_currency, to_currency
                        )
                    )

                else:
                    conversion_data = []
                    for value in conversion_rate:
                        conversion_data.append(value)
                    row.currency = self.filters.get("presentation_currency")
                    row.invoiced = convert(row.invoiced,  to_currency, from_currency, conversion_data[1])
                    row.paid = convert(row.paid,  to_currency, from_currency, conversion_data[1])
                    row.outstanding = convert(row.outstanding,  to_currency, from_currency, conversion_data[1])
                    row.advance = convert(row.advance,  to_currency, from_currency, conversion_data[1])
                    row.range1 = convert(row.range1,  to_currency, from_currency, conversion_data[1])
                    row.range2 = convert(row.range2,  to_currency, from_currency, conversion_data[1])
                    row.range3 = convert(row.range3,  to_currency, from_currency, conversion_data[1])
                    row.range4 = convert(row.range4,  to_currency, from_currency, conversion_data[1])
                    row.range5 = convert(row.range5,  to_currency, from_currency, conversion_data[1])
                    row.total_due = convert(row.total_due,  to_currency, from_currency, conversion_data[1])
                    row.future_amount = convert(row.future_amount,  to_currency, from_currency, conversion_data[1])
                    row.gl_balance = convert(row.gl_balance,  to_currency, from_currency, conversion_data[1])
                    row.diff = convert(row.diff,  to_currency, from_currency, conversion_data[1])
                    row.remaining_balance = convert(row.remaining_balance,  to_currency, from_currency, conversion_data[1])

            
    def get_party_total(self, args):
        self.party_total = frappe._dict()

        for d in self.receivables:
            self.init_party_total(d)

            # Add all amount columns
            for k in list(self.party_total[d.party]):
                if isinstance(self.party_total[d.party][k], float):
                    self.party_total[d.party][k] += d.get(k) or 0.0

            # set territory, customer_group, sales person etc
            self.set_party_details(d)

    def init_party_total(self, row):
        self.party_total.setdefault(
            row.party,
            frappe._dict(
                {
                    "invoiced": 0.0,
                    "paid": 0.0,
                    "credit_note": 0.0,
                    "outstanding": 0.0,
                    "range1": 0.0,
                    "range2": 0.0,
                    "range3": 0.0,
                    "range4": 0.0,
                    "range5": 0.0,
                    "total_due": 0.0,
                    "future_amount": 0.0,
                    "sales_person": [],
                    "party_type": row.party_type,
                }
            ),
        )

    def set_party_details(self, row):
        self.party_total[row.party].currency = row.currency

        for key in ("territory", "customer_group", "supplier_group"):
            if row.get(key):
                self.party_total[row.party][key] = row.get(key, "")
        if row.sales_person:
            self.party_total[row.party].sales_person.append(row.get("sales_person", ""))

        if self.filters.sales_partner:
            self.party_total[row.party]["default_sales_partner"] = row.get("default_sales_partner", "")

    def get_columns(self):
        self.columns = []
        self.add_column(
            label=_("Party Type"),
            fieldname="party_type",
            fieldtype="Data",
            width=100,
        )
        self.add_column(
            label=_("Party"),
            fieldname="party",
            fieldtype="Dynamic Link",
            options="party_type",
            width=180,
        )

        if self.party_naming_by == "Naming Series":
            self.add_column(
                label=_("Supplier Name") if self.account_type == "Payable" else _("Customer Name"),
                fieldname="party_name",
                fieldtype="Data",
            )

        credit_debit_label = "Credit Note" if self.account_type == "Receivable" else "Debit Note"

        self.add_column(_("Advance Amount"), fieldname="advance")
        self.add_column(_("Invoiced Amount"), fieldname="invoiced")
        self.add_column(_("Paid Amount"), fieldname="paid")
        self.add_column(_(credit_debit_label), fieldname="credit_note")
        self.add_column(_("Outstanding Amount"), fieldname="outstanding")

        if self.filters.show_gl_balance:
            self.add_column(_("GL Balance"), fieldname="gl_balance")
            self.add_column(_("Difference"), fieldname="diff")

        self.setup_ageing_columns()

        if self.filters.show_future_payments:
            self.add_column(label=_("Future Payment Amount"), fieldname="future_amount")
            self.add_column(label=_("Remaining Balance"), fieldname="remaining_balance")

        if self.account_type == "Receivable":
            self.add_column(
                label=_("Territory"), fieldname="territory", fieldtype="Link", options="Territory"
            )
            self.add_column(
                label=_("Customer Group"),
                fieldname="customer_group",
                fieldtype="Link",
                options="Customer Group",
            )
            if self.filters.show_sales_person:
                self.add_column(label=_("Sales Person"), fieldname="sales_person", fieldtype="Data")

            if self.filters.sales_partner:
                self.add_column(label=_("Sales Partner"), fieldname="default_sales_partner", fieldtype="Data")

        else:
            self.add_column(
                label=_("Supplier Group"),
                fieldname="supplier_group",
                fieldtype="Link",
                options="Supplier Group",
            )

        self.add_column(
            label=_("Currency"), fieldname="currency", fieldtype="Link", options="Currency", width=80
        )
    def setup_ageing_columns(self):
        for i, label in enumerate(
			[
				"0-{range1}".format(range1=self.filters["range1"]),
				"{range1}-{range2}".format(
					range1=cint(self.filters["range1"]) + 1, range2=self.filters["range2"]
				),
				"{range2}-{range3}".format(
					range2=cint(self.filters["range2"]) + 1, range3=self.filters["range3"]
				),
				"{range3}-{range4}".format(
					range3=cint(self.filters["range3"]) + 1, range4=self.filters["range4"]
				),
				"{range4}-{above}".format(range4=cint(self.filters["range4"]) + 1, above=_("Above")),
			]
		):
            self.add_column(label=label, fieldname="range" + str(i + 1))

		# Add column for total due amount
        self.add_column(label="Total Amount Due", fieldname="total_due")


def get_gl_balance(report_date, company):
	return frappe._dict(
		frappe.db.get_all(
			"GL Entry",
			fields=["party", "sum(debit -  credit)"],
			filters={"posting_date": ("<=", report_date), "is_cancelled": 0, "company": company},
			group_by="party",
			as_list=1,
		)
	)

