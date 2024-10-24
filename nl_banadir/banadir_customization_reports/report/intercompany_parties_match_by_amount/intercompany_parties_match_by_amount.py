# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
import erpnext
from frappe.query_builder import DocType, Case
from frappe.utils import getdate
from erpnext.accounts.report.utils import convert


class InterCompanyFilter(TypedDict):
    reference_company: str | None
    party_type: str | None
    party: str | None
    from_date: str
    to_date: str
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
        self.amount_journals = []

    def run(self):
        if not self.columns:
            self.columns = self.get_columns()

        # if self.compare_by_amount:
        #     data = self.compare_journals_by_amount()
        # else:
        #     data = self.get_intercompany_journals()
        if (
            not self.filters.get("compare_by_amount")
            and self.filters.get("reference_company")
            and self.filters.get("party_type")
        ):
            self.get_intercompany_journals()

        if self.filters.get("compare_by_amount"):
            # self.data = []
            self.compare_journals_by_amount2()
        return self.columns, self.data

    def get_columns(self):
        columns = [
            {
                "label": "Reference Company",
                "fieldname": "reference_company",
                "fieldtype": "Link",
                "options": "Company",
                "width": "200",
            },
            {
                "label": "Representative Company",
                "fieldname": "representative_company",
                "fieldtype": "Link",
                "options": "Company",
                "width": "200",
            },
            {
                "label": "Reference Journal",
                "fieldname": "reference_journal",
                "fieldtype": "Link",
                "options": "Journal Entry",
                "width": "200",
            },
            {
                "label": "Party Journal",
                "fieldname": "party_journal",
                "fieldtype": "Link",
                "options": "Journal Entry",
                "width": "200",
            },
            {
                "label": "Total Debit or Credit",
                "fieldname": "total_debit_or_credit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
            {
                "label": "Total Credit or Debit",
                "fieldname": "total_credit_or_debit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
        ]

        return columns

    def get_intercompany_journals(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

            total_amount = (
                Case()
                .when(
                    Journal_Entry_Account.debit_in_account_currency > 0,
                    Journal_Entry_Account.debit_in_account_currency,
                )
                .else_(Journal_Entry_Account.credit_in_account_currency)
                .as_("total_debit_or_credit")
                if party_type == "Customer"
                else (
                    Case()
                    .when(
                        Journal_Entry_Account.credit_in_account_currency > 0,
                        Journal_Entry_Account.credit_in_account_currency,
                    )
                    .else_(Journal_Entry_Account.debit_in_account_currency)
                    .as_("total_debit_or_credit")
                )
            )

            query = (
                frappe.qb.from_(Journal_Entry_Account)
                .join(Journal_Entry)
                .on(Journal_Entry_Account.parent == Journal_Entry.name)
                .select(
                    Journal_Entry.company.as_("reference_company"),
                    Journal_Entry_Account.party.as_("representative_company"),
                    Journal_Entry.name.as_("reference_journal"),
                    total_amount,
                    Journal_Entry.inter_company_journal_entry_reference.as_(
                        "party_journal"
                    ),
                )
                .where(
                    Journal_Entry_Account.party_type == self.filters.get("party_type")
                )
                .where(Journal_Entry.company == self.filters.get("reference_company"))
                .where(
                    (Journal_Entry.posting_date >= self.from_date)
                    & (Journal_Entry.posting_date <= self.to_date)
                )
                .where(
                    (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                    & (Journal_Entry.docstatus == 1)
                )
            )

            if self.filters.get("party"):
                query = query.where(
                    Journal_Entry_Account.party == self.filters.get("party")[0]
                )

            # Loop through the data, if it has a party journal, get the value of the debit/credit
            journals = query.run(as_dict=True)

            for journal in journals:
                if journal.party_journal:
                    party_data = self.get_party_journals(journal=journal)
                    if party_data:
                        merged_journal = journal.copy()
                        merged_journal["total_credit_or_debit"] = party_data[
                            0
                        ].total_credit_or_debit
                        self.data.append(merged_journal)
                else:
                    self.data.append(journal)

    def get_party_journals(self, journal):
        Journal_Entry = DocType("Journal Entry")
        Journal_Entry_Account = DocType("Journal Entry Account")
        party_type = (
            "Customer" if self.filters.get("party_type") == "Supplier" else "Supplier"
        )

        total_amount = (
            Case()
            .when(
                Journal_Entry_Account.credit_in_account_currency > 0,
                Journal_Entry_Account.credit_in_account_currency,
            )
            .else_(Journal_Entry_Account.debit_in_account_currency)
            .as_("total_credit_or_debit")
            if party_type == "Supplier"
            else (
                Case()
                .when(
                    Journal_Entry_Account.debit_in_account_currency > 0,
                    Journal_Entry_Account.debit_in_account_currency,
                )
                .else_(Journal_Entry_Account.credit_in_account_currency)
                .as_("total_credit_or_debit")
            )
        )

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == journal.party_journal)
            .select(
                total_amount,
            )
            .where(Journal_Entry_Account.party_type == party_type)
            .where(Journal_Entry.company == journal.representative_company)
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                & (Journal_Entry.docstatus == 1)
            )
            .where(Journal_Entry.name == journal.party_journal)
        )
        return query.run(as_dict=True)

    # def get_intercompany_journals(self):
    #     # Journal_Entry = DocType("Journal Entry")

    #     # if self.filters.get("from_company"):

    #     #     query = (
    #     #         frappe.qb.from_(Journal_Entry)
    #     #         .select(
    #     #             Journal_Entry.company.as_("from_company"),
    #     #             Journal_Entry.name.as_("journal"),
    #     #             Journal_Entry.inter_company_journal_entry_reference.as_(
    #     #                 "customer_journal"
    #     #             ),
    #     #             "total_debit",
    #     #             "posting_date",
    #     #         )
    #     #         .where(
    #     #             (Journal_Entry.posting_date >= self.from_date)
    #     #             & (Journal_Entry.posting_date <= self.to_date)
    #     #         )
    #     #         .where(
    #     #             (Journal_Entry.company == self.filters.get("from_company"))
    #     #             & (Journal_Entry.voucher_type == "Inter Company Journal Entry")
    #     #             & (Journal_Entry.docstatus == 1)
    #     #         )
    #     #     )

    #     # journals = query.run(as_dict=True)

    #     # for journal in journals:

    #     #     if journal.customer_journal:

    #     #         new_journal = (
    #     #             frappe.qb.from_(Journal_Entry)
    #     #             .select(Journal_Entry.company.as_("to_company"), "total_credit")
    #     #             .where((Journal_Entry.name == journal.customer_journal))
    #     #             .run(as_dict=True)
    #     #         )

    #     #         journal.update(new_journal[0])
    #     #         self.data.append(journal)

    #     #     else:
    #     #         self.data.append(journal)

    #     if self.filters.get("from_company") and self.filters.get("to_company"):
    #         # Reset self.data
    #         self.data = []
    #         self.filter_by_to_company()

    #         # initial_data = self.convert_currency_fields(
    #         #     self.data, self.filters, "from_company", "total_debit"
    #         # )
    #         # final_data = self.convert_currency_fields(
    #         #     initial_data, self.filters, "to_company", "total_credit"
    #         # )

    #     return self.data

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
                Journal_Entry.total_amount.as_("total_debit"),
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
                .select(
                    Journal_Entry.company.as_("to_company"),
                    Journal_Entry.total_amount.as_("total_credit"),
                )
                .where(
                    (Journal_Entry.name == journal.customer_journal)
                    & (Journal_Entry.company == self.filters.get("to_company"))
                )
                .run(as_dict=True)
            )

            if len(new_journal) > 0:
                merged_journal = journal.copy()
                merged_journal["to_company"] = new_journal[0].to_company
                merged_journal["total_credit"] = new_journal[0].total_credit
                self.data.append(merged_journal)

    def get_journals(self, company_key, journal_key, amount_field):
        Journal_Entry = DocType("Journal Entry")
        Journal_Entry_Account = DocType("Journal Entry Account")

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == Journal_Entry.name)
            .select(
                Journal_Entry_Account.parent.as_(journal_key),
                Journal_Entry.company.as_(company_key),
                Journal_Entry.total_amount.as_(amount_field),
            )
            .where(Journal_Entry_Account.party_type != "")
            .where(Journal_Entry.company == self.filters.get(company_key))
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(Journal_Entry.docstatus == 1)
        )

        return query.run(as_dict=True)

    def compare_journals_by_amount(self):
        if self.filters.get("from_company") and self.filters.get("to_company"):

            from_company_journals = self.get_journals(
                "from_company", "journal", "total_debit"
            )

            to_company_journals = self.get_journals(
                "to_company", "customer_journal", "total_credit"
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

    def compare_journals_by_amount2(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

            total_amount = (
                Case()
                .when(
                    Journal_Entry_Account.debit_in_account_currency > 0,
                    Journal_Entry_Account.debit_in_account_currency,
                )
                .else_(Journal_Entry_Account.credit_in_account_currency)
                .as_("total_debit_or_credit")
                if party_type == "Customer"
                else (
                    Case()
                    .when(
                        Journal_Entry_Account.credit_in_account_currency > 0,
                        Journal_Entry_Account.credit_in_account_currency,
                    )
                    .else_(Journal_Entry_Account.debit_in_account_currency)
                    .as_("total_debit_or_credit")
                )
            )

            query = (
                frappe.qb.from_(Journal_Entry_Account)
                .join(Journal_Entry)
                .on(Journal_Entry_Account.parent == Journal_Entry.name)
                .select(
                    Journal_Entry.company.as_("reference_company"),
                    Journal_Entry_Account.party.as_("representative_company"),
                    Journal_Entry.name.as_("reference_journal"),
                    total_amount,
                    Journal_Entry.inter_company_journal_entry_reference.as_(
                        "party_journal"
                    ),
                )
                .where(
                    Journal_Entry_Account.party_type == self.filters.get("party_type")
                )
                .where(Journal_Entry.company == self.filters.get("reference_company"))
                .where(
                    (Journal_Entry.posting_date >= self.from_date)
                    & (Journal_Entry.posting_date <= self.to_date)
                )
                .where(
                    (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                    & (Journal_Entry.docstatus == 1)
                )
            )

            if self.filters.get("party"):
                query = query.where(
                    Journal_Entry_Account.party == self.filters.get("party")[0]
                )

            # Loop through the data, if it has a party journal, get the value of the debit/credit
            journals = query.run(as_dict=True)

            if self.filters.get("compare_by_amount"):
                party_type = "supplier" if party_type == "Customer" else "Customer"

                # amount_journals = []

                total_amount = (
                    Case()
                    .when(
                        Journal_Entry_Account.credit_in_account_currency > 0,
                        Journal_Entry_Account.credit_in_account_currency,
                    )
                    .else_(Journal_Entry_Account.debit_in_account_currency)
                    .as_("total_credit_or_debit")
                    if party_type == "Supplier"
                    else (
                        Case()
                        .when(
                            Journal_Entry_Account.debit_in_account_currency > 0,
                            Journal_Entry_Account.debit_in_account_currency,
                        )
                        .else_(Journal_Entry_Account.credit_in_account_currency)
                        .as_("total_credit_or_debit")
                    )
                )

                if party_type == "Customer":
                    amount_query = (
                        frappe.qb.from_(Journal_Entry_Account)
                        .join(Journal_Entry)
                        .on(Journal_Entry_Account.parent == Journal_Entry.name)
                        .select(
                            Journal_Entry.company.as_("company"),
                            # Journal_Entry_Account.party.as_("representative_company"),
                            Journal_Entry.name.as_("party_journal"),
                            total_amount,
                        )
                        .where(Journal_Entry_Account.party_type == party_type)
                        # .where(
                        #     Journal_Entry.company
                        #     == self.filters.get("reference_company")
                        # )
                        .where(
                            (Journal_Entry.posting_date >= self.from_date)
                            & (Journal_Entry.posting_date <= self.to_date)
                        )
                        .where(
                            (
                                Journal_Entry.voucher_type
                                != "Inter Company Journal Entry"
                            )
                            & (Journal_Entry.docstatus == 1)
                        )
                    )

                    self.amount_journals = amount_query.run(as_dict=True)
                else:
                    amount_query = (
                        frappe.qb.from_(Journal_Entry_Account)
                        .join(Journal_Entry)
                        .on(Journal_Entry_Account.parent == Journal_Entry.name)
                        .select(
                            Journal_Entry.company.as_("company"),
                            # Journal_Entry_Account.party.as_("representative_company"),
                            Journal_Entry.name.as_("party_journal"),
                            total_amount,
                        )
                        .where(Journal_Entry_Account.party_type == party_type)
                        # .where(
                        #     Journal_Entry.company
                        #     == self.filters.get("reference_company")
                        # )
                        .where(
                            (Journal_Entry.posting_date >= self.from_date)
                            & (Journal_Entry.posting_date <= self.to_date)
                        )
                        .where(
                            (
                                Journal_Entry.voucher_type
                                != "Inter Company Journal Entry"
                            )
                            & (Journal_Entry.docstatus == 1)
                        )
                    )

                    self.amount_journals = amount_query.run(as_dict=True)
            if self.amount_journals:
                for journal in journals:
                    for amount in self.amount_journals:
                        if (
                            journal.total_debit_or_credit
                            == amount.total_credit_or_debit
                        ):
                            # print("MATCH", amount)
                            merged_journal = journal.copy()
                            merged_journal["total_credit_or_debit"] = (
                                amount.total_credit_or_debit
                            )
                            merged_journal["party_journal"] = amount.party_journal
                            # print("JOURNALS", merged_journal)
                            self.data.append(merged_journal)


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
