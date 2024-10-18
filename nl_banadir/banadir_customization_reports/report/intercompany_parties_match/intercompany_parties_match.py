# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
import erpnext
from frappe.query_builder import DocType
from frappe.utils import getdate
from erpnext.accounts.report.utils import convert


class InterCompanyFilter(TypedDict):
    from_company: str | None
    to_company: str | None
    from_date: str
    to_date: str
    journal: str | None
    compare_by_amount: bool


def execute(filters: InterCompanyFilter | None = None):
    return InterCompanyPartiesMatchReport(filters).run()


class InterCompanyPartiesMatchReport:
    def __init__(self, filters: InterCompanyFilter | None) -> None:
        self.filters = filters
        self.from_date = getdate(filters.get("from_date"))
        self.to_date = getdate(filters.get("to_date"))
        self.compare_by_amount = filters.get("compare_by_amount")
        self.data = []
        self.columns = []

    def run(self):
        if not self.columns:
            self.columns = self.get_columns()

        if self.compare_by_amount:
            data = self.compare_journals_by_amount()
        else:
            data = self.fetch_data()

        return self.columns, data

    def get_columns(self):
        columns = [
            {
                "label": "From Company",
                "fieldname": "from_company",
                "fieldtype": "Link",
                "options": "Company",
                "width": "200",
            },
            {
                "label": "To Company",
                "fieldname": "to_company",
                "fieldtype": "Link",
                "options": "Company",
                "width": "200",
            },
            {
                "label": "Journal",
                "fieldname": "journal",
                "fieldtype": "Link",
                "options": "Journal Entry",
                "width": "200",
            },
            {
                "label": "Customer Journal",
                "fieldname": "customer_journal",
                "fieldtype": "Link",
                "options": "Journal Entry",
                "width": "200",
            },
            {
                "label": "Total Debit",
                "fieldname": "total_debit",
                "fieldtype": "Float",
                "precision": 2,
                "width": "200",
            },
            {
                "label": "Total Credit",
                "fieldname": "total_credit",
                "fieldtype": "Float",
                "precision": 2,
                "width": "200",
            },
        ]

        return columns

    def fetch_data(self):
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("from_company"):

            query = (
                frappe.qb.from_(Journal_Entry)
                .select(
                    Journal_Entry.company.as_("from_company"),
                    Journal_Entry.name.as_("journal"),
                    Journal_Entry.inter_company_journal_entry_reference.as_(
                        "customer_journal"
                    ),
                    "total_debit",
                    "posting_date",
                )
                .where(
                    (Journal_Entry.posting_date >= self.from_date)
                    & (Journal_Entry.posting_date <= self.to_date)
                )
                .where(
                    (Journal_Entry.company == self.filters.get("from_company"))
                    & (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                    & (Journal_Entry.docstatus == 1)
                )
            )

        journals = query.run(as_dict=True)

        for journal in journals:

            if journal.customer_journal:

                new_journal = (
                    frappe.qb.from_(Journal_Entry)
                    .select(Journal_Entry.company.as_("to_company"), "total_credit")
                    .where((Journal_Entry.name == journal.customer_journal))
                    .run(as_dict=True)
                )

                journal.update(new_journal[0])
                self.data.append(journal)

            else:
                self.data.append(journal)

        if self.filters.get("from_company") and self.filters.get("to_company"):
            # Reset self.data
            self.data = []
            self.filter_by_to_company()

            initial_data = self.convert_currency_fields(
                self.data, self.filters, "from_company", "total_debit"
            )
            final_data = self.convert_currency_fields(
                initial_data, self.filters, "to_company", "total_credit"
            )

        return final_data

    def convert_currency_fields(self, data, filters, company_key, amount_field):
        date = filters.get("to_date") or frappe.utils.now()

        from_currency = frappe.get_cached_value(
            "Company", filters.get(company_key), "default_currency"
        )
        to_currency = filters.get("presentation_currency") or frappe.get_cached_value(
            "Company", filters.get(company_key), "default_currency"
        )

        for entry in data:
            entry[amount_field] = convert(
                entry.get(amount_field, 0), to_currency, from_currency, date
            )

        return data

    def filter_by_to_company(self):
        Journal_Entry = DocType("Journal Entry")

        query = (
            frappe.qb.from_(Journal_Entry)
            .select(
                Journal_Entry.company.as_("from_company"),
                Journal_Entry.name.as_("journal"),
                Journal_Entry.inter_company_journal_entry_reference.as_(
                    "customer_journal"
                ),
                "total_debit",
                "posting_date",
            )
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.company == self.filters.get("from_company"))
                & (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                & (Journal_Entry.docstatus == 1)
                & (Journal_Entry.inter_company_journal_entry_reference != "")
            )
        )

        journals = query.run(as_dict=True)

        for journal in journals:
            new_journal = (
                frappe.qb.from_(Journal_Entry)
                .select(Journal_Entry.company.as_("to_company"), "total_credit")
                .where(
                    (Journal_Entry.name == journal.customer_journal)
                    & (Journal_Entry.company == self.filters.get("to_company"))
                )
                .run(as_dict=True)
            )

            if len(new_journal) > 0:
                journal.update(new_journal[0])
                self.data.append(journal)

    def get_journals(self, company_key, journal_key, amount_field):
        Journal_Entry = DocType("Journal Entry")

        query = (
            frappe.qb.from_(Journal_Entry)
            .select(
                Journal_Entry.company.as_(company_key),
                Journal_Entry.name.as_(journal_key),
                amount_field,
            )
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.company == self.filters.get(company_key))
                & (Journal_Entry.docstatus == 1)
            )
        )

        return query.run(as_dict=True)

    def compare_journals_by_amount(self):
        if self.filters.get("from_company") and self.filters.get("to_company"):

            from_company_journals = self.get_journals(
                "from_company", "journal", "total_debit"
            )

            if from_company_journals:
                from_company_journals = self.convert_currency_fields(
                    from_company_journals, self.filters, "from_company", "total_debit"
                )

            to_company_journals = self.get_journals(
                "to_company", "customer_journal", "total_credit"
            )

            if to_company_journals:
                to_company_journals = self.convert_currency_fields(
                    to_company_journals, self.filters, "from_company", "total_debit"
                )

            for from_journal in from_company_journals:
                for to_journal in to_company_journals:
                    if from_journal.total_debit == to_journal.total_credit:
                        merged_journal = from_journal.copy()
                        merged_journal["to_company"] = to_journal.to_company
                        merged_journal["customer_journal"] = to_journal.customer_journal
                        merged_journal["total_credit"] = to_journal.total_credit
                        self.data.append(merged_journal)
            return self.data
