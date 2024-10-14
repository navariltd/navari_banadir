# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
from frappe.query_builder import DocType
from frappe.utils import getdate


class InterCompanyFilter(TypedDict):
    from_company: str | None
    to_company: str | None
    from_date: str
    to_date: str
    journal: str | None


def execute(filters: InterCompanyFilter | None = None):
    return InterCompanyPartiesMatchReport(filters).run()


class InterCompanyPartiesMatchReport:
    def __init__(self, filters: InterCompanyFilter | None) -> None:
        self.filters = filters
        self.from_date = getdate(filters.get("from_date"))
        self.to_date = getdate(filters.get("to_date"))

        self.data = []
        self.columns = []

    def run(self):
        if not self.columns:
            self.columns = self.get_columns()

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
                "label": "Total Credit",
                "fieldname": "total_credit",
                "fieldtype": "Currency",
                "width": "200",
            },
            {
                "label": "Total Debit",
                "fieldname": "total_debit",
                "fieldtype": "Currency",
                "width": "200",
            },
        ]

        return columns

    def fetch_data(self):
        Journal_Entry = DocType("Journal Entry")

        query = (
            frappe.qb.from_(Journal_Entry)
            .select(
                Journal_Entry.company.as_("from_company"),
                Journal_Entry.name.as_("journal"),
                "total_credit",
                "inter_company_journal_entry_reference",
                "posting_date",
            )
            .where(
                (Journal_Entry.inter_company_journal_entry_reference != "")
                & (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                & (Journal_Entry.docstatus == 1)
            )
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
        )

        # data = []
        journals = query.run(as_dict=True)

        print(journals)

        for journal in journals:
            new_journal = (
                frappe.qb.from_(Journal_Entry)
                .select(
                    Journal_Entry.company.as_("to_company"),
                    Journal_Entry.total_debit.as_("total_debit"),
                )
                .where(
                    Journal_Entry.name == journal.inter_company_journal_entry_reference
                )
                .run(as_dict=True)
            )
            journal.update(new_journal[0])
            self.data.append(journal)

        print(self.from_date)
        return self.data

    def get_journals(self, filters):
        J_Entry = DocType("Journal Entry")

        # query = frappe.qb.from_(J_Entry).
