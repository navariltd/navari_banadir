# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
import erpnext
import copy
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
            self.compare_journals_by_amount()
        return self.columns, self.data

    def get_columns(self):
        columns = [
            {
                "label": "Reference Journal Posting Date",
                "fieldname": "reference_journal_posting_date",
                "fieldtype": "Date",
                "width": "140",
            },
            {
                "label": "Reference Company",
                "fieldname": "reference_company",
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
            # {
            #     "label": "Total Debit or Credit",
            #     "fieldname": "total_debit_or_credit",
            #     "fieldtype": "Currency",
            #     "precision": 2,
            #     "width": "200",
            # },
            {
                "label": "Reference Company Debit",
                "fieldname": "reference_company_debit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
            {
                "label": "Reference Company Credit",
                "fieldname": "reference_company_credit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
            {
                "label": "",
                "fieldname": "",
                "fieldtype": "Data",
                "width": "100",
            },
            {
                "label": "",
                "fieldname": "",
                "fieldtype": "Data",
                "width": "100",
            },
            {
                "label": "Party Journal Posting Date",
                "fieldname": "party_journal_posting_date",
                "fieldtype": "Date",
                "width": "140",
            },
            {
                "label": "Representative Company",
                "fieldname": "representative_company",
                "fieldtype": "Link",
                "options": "Company",
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
                "label": "Representative Company Debit",
                "fieldname": "representative_company_debit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
            {
                "label": "Representative Company Credit",
                "fieldname": "representative_company_credit",
                "fieldtype": "Currency",
                "precision": 2,
                "width": "200",
            },
            # {
            #     "label": "Total Credit or Debit",
            #     "fieldname": "total_credit_or_debit",
            #     "fieldtype": "Currency",
            #     "precision": 2,
            #     "width": "200",
            # },
        ]

        return columns

    def get_intercompany_journals(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

            # total_amount = (
            #     Case()
            #     .when(
            #         Journal_Entry_Account.debit_in_account_currency > 0,
            #         Journal_Entry_Account.debit_in_account_currency,
            #     )
            #     .else_(Journal_Entry_Account.credit_in_account_currency)
            #     .as_("total_debit_or_credit")
            #     if party_type == "Customer"
            #     else (
            #         Case()
            #         .when(
            #             Journal_Entry_Account.credit_in_account_currency > 0,
            #             Journal_Entry_Account.credit_in_account_currency,
            #         )
            #         .else_(Journal_Entry_Account.debit_in_account_currency)
            #         .as_("total_debit_or_credit")
            #     )
            # )

            query = (
                frappe.qb.from_(Journal_Entry_Account)
                .join(Journal_Entry)
                .on(Journal_Entry_Account.parent == Journal_Entry.name)
                .select(
                    Journal_Entry.company.as_("reference_company"),
                    Journal_Entry_Account.party.as_("representative_company"),
                    Journal_Entry.name.as_("reference_journal"),
                    Journal_Entry.posting_date.as_("reference_journal_posting_date"),
                    # total_amount,
                    Journal_Entry_Account.debit_in_account_currency.as_(
                        "reference_company_debit"
                    ),
                    Journal_Entry_Account.credit_in_account_currency.as_(
                        "reference_company_credit"
                    ),
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

            merged_reference_journals = {}

            for journal in journals:
                journal_item = journal["reference_journal"]
                if journal_item in merged_reference_journals:
                    merged_reference_journals[journal_item][
                        "reference_company_credit"
                    ] += journal["reference_company_credit"]
                    merged_reference_journals[journal_item][
                        "reference_company_debit"
                    ] += journal["refererence_company_debit"]
                else:
                    merged_reference_journals[journal_item] = {
                        "reference_company": journal["reference_company"],
                        "representative_company": journal["representative_company"],
                        "reference_journal": journal_item,
                        # "total_debit_or_credit": journal["total_debit_or_credit"],
                        "reference_company_debit": journal["reference_company_debit"],
                        "reference_company_credit": journal["reference_company_credit"],
                        "party_journal": journal["party_journal"],
                        "reference_journal_posting_date": journal[
                            "reference_journal_posting_date"
                        ],
                    }

            journals = list(merged_reference_journals.values())

            for journal in journals:
                if journal.get("party_journal"):
                    party_data = self.get_party_journals(journal=journal)
                    if party_data:
                        merged_journal = journal.copy()
                        merged_journal["party_journal_posting_date"] = party_data[
                            0
                        ].party_journal_posting_date
                        # merged_journal["total_credit_or_debit"] = party_data[
                        #     0
                        # ].total_credit_or_debit
                        merged_journal["representative_company_debit"] = party_data[
                            0
                        ].representative_company_debit
                        merged_journal["representative_company_credit"] = party_data[
                            0
                        ].representative_company_credit
                        self.data.append(merged_journal)
                else:
                    self.data.append(journal)

    def get_party_journals(self, journal):
        Journal_Entry = DocType("Journal Entry")
        Journal_Entry_Account = DocType("Journal Entry Account")
        party_type = (
            "Customer" if self.filters.get("party_type") == "Supplier" else "Supplier"
        )

        # total_amount = (
        #     Case()
        #     .when(
        #         Journal_Entry_Account.credit_in_account_currency > 0,
        #         Journal_Entry_Account.credit_in_account_currency,
        #     )
        #     .else_(Journal_Entry_Account.debit_in_account_currency)
        #     .as_("total_credit_or_debit")
        #     if party_type == "Supplier"
        #     else (
        #         Case()
        #         .when(
        #             Journal_Entry_Account.debit_in_account_currency > 0,
        #             Journal_Entry_Account.debit_in_account_currency,
        #         )
        #         .else_(Journal_Entry_Account.credit_in_account_currency)
        #         .as_("total_credit_or_debit")
        #     )
        # )

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == journal.get("party_journal"))
            .select(
                # total_amount,
                Journal_Entry_Account.debit_in_account_currency.as_(
                    "representative_company_debit"
                ),
                Journal_Entry_Account.credit_in_account_currency.as_(
                    "representative_company_credit"
                ),
                Journal_Entry.posting_date.as_("party_journal_posting_date"),
            )
            .where(Journal_Entry_Account.party_type == party_type)
            .where(Journal_Entry.company == journal.get("representative_company"))
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.voucher_type == "Inter Company Journal Entry")
                & (Journal_Entry.docstatus == 1)
            )
            .where(Journal_Entry.name == journal.get("party_journal"))
        )
        return query.run(as_dict=True)

    # def filter_by_to_company(self):
    #     Journal_Entry = DocType("Journal Entry")

    #     query = (
    #         frappe.qb.from_(Journal_Entry)
    #         .select(
    #             Journal_Entry.company.as_("from_company"),
    #             Journal_Entry.name.as_("journal"),
    #             Journal_Entry.inter_company_journal_entry_reference.as_(
    #                 "customer_journal"
    #             ),
    #             Journal_Entry.total_amount.as_("total_debit"),
    #             "posting_date",
    #         )
    #         .where(
    #             (Journal_Entry.posting_date >= self.from_date)
    #             & (Journal_Entry.posting_date <= self.to_date)
    #         )
    #         .where(
    #             (Journal_Entry.company == self.filters.get("from_company"))
    #             & (Journal_Entry.voucher_type == "Inter Company Journal Entry")
    #             & (Journal_Entry.docstatus == 1)
    #             & (Journal_Entry.inter_company_journal_entry_reference != "")
    #         )
    #     )

    #     journals = query.run(as_dict=True)

    #     for journal in journals:
    #         new_journal = (
    #             frappe.qb.from_(Journal_Entry)
    #             .select(
    #                 Journal_Entry.company.as_("to_company"),
    #                 Journal_Entry.total_amount.as_("total_credit"),
    #             )
    #             .where(
    #                 (Journal_Entry.name == journal.customer_journal)
    #                 & (Journal_Entry.company == self.filters.get("to_company"))
    #             )
    #             .run(as_dict=True)
    #         )

    #         if len(new_journal) > 0:
    #             merged_journal = journal.copy()
    #             merged_journal["to_company"] = new_journal[0].to_company
    #             merged_journal["total_credit"] = new_journal[0].total_credit
    #             self.data.append(merged_journal)

    # def get_journals(self, company_key, journal_key, amount_field):
    #     Journal_Entry = DocType("Journal Entry")
    #     Journal_Entry_Account = DocType("Journal Entry Account")

    #     query = (
    #         frappe.qb.from_(Journal_Entry_Account)
    #         .join(Journal_Entry)
    #         .on(Journal_Entry_Account.parent == Journal_Entry.name)
    #         .select(
    #             Journal_Entry_Account.parent.as_(journal_key),
    #             Journal_Entry.company.as_(company_key),
    #             Journal_Entry.total_amount.as_(amount_field),
    #         )
    #         .where(Journal_Entry_Account.party_type != "")
    #         .where(Journal_Entry.company == self.filters.get(company_key))
    #         .where(
    #             (Journal_Entry.posting_date >= self.from_date)
    #             & (Journal_Entry.posting_date <= self.to_date)
    #         )
    #         .where(Journal_Entry.docstatus == 1)
    #     )

    #     return query.run(as_dict=True)

    def compare_journals_by_amount(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

            # total_amount = (
            #     Case()
            #     .when(
            #         Journal_Entry_Account.debit_in_account_currency > 0,
            #         Journal_Entry_Account.debit_in_account_currency,
            #     )
            #     .else_(Journal_Entry_Account.credit_in_account_currency)
            #     .as_("total_debit_or_credit")
            #     if party_type == "Customer"
            #     else (
            #         Case()
            #         .when(
            #             Journal_Entry_Account.credit_in_account_currency > 0,
            #             Journal_Entry_Account.credit_in_account_currency,
            #         )
            #         .else_(Journal_Entry_Account.debit_in_account_currency)
            #         .as_("total_debit_or_credit")
            #     )
            # )

            query = (
                frappe.qb.from_(Journal_Entry_Account)
                .join(Journal_Entry)
                .on(Journal_Entry_Account.parent == Journal_Entry.name)
                .select(
                    Journal_Entry.company.as_("reference_company"),
                    Journal_Entry_Account.party.as_("representative_company"),
                    Journal_Entry.name.as_("reference_journal"),
                    Journal_Entry.posting_date.as_("reference_journal_posting_date"),
                    # total_amount,
                    Journal_Entry_Account.debit_in_account_currency.as_(
                        "reference_company_debit"
                    ),
                    Journal_Entry_Account.credit_in_account_currency.as_(
                        "reference_company_credit"
                    ),
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

            journals = query.run(as_dict=True)

            if self.filters.get("compare_by_amount"):
                party_type = "Supplier" if party_type == "Customer" else "Customer"

                # amount_journals = []

                # total_amount = (
                #     Case()
                #     .when(
                #         Journal_Entry_Account.credit_in_account_currency > 0,
                #         Journal_Entry_Account.credit_in_account_currency,
                #     )
                #     .else_(Journal_Entry_Account.debit_in_account_currency)
                #     .as_("total_credit_or_debit")
                #     if party_type == "Supplier"
                #     else (
                #         Case()
                #         .when(
                #             Journal_Entry_Account.debit_in_account_currency > 0,
                #             Journal_Entry_Account.debit_in_account_currency,
                #         )
                #         .else_(Journal_Entry_Account.credit_in_account_currency)
                #         .as_("total_credit_or_debit")
                #     )
                # )

                if party_type == "Customer":
                    amount_query = (
                        frappe.qb.from_(Journal_Entry_Account)
                        .join(Journal_Entry)
                        .on(Journal_Entry_Account.parent == Journal_Entry.name)
                        .select(
                            Journal_Entry.company.as_("company"),
                            # Journal_Entry_Account.party.as_("representative_company"),
                            Journal_Entry.name.as_("party_journal"),
                            Journal_Entry.posting_date.as_(
                                "party_journal_posting_date"
                            ),
                            # total_amount,
                            Journal_Entry_Account.debit_in_account_currency.as_(
                                "representative_company_debit"
                            ),
                            Journal_Entry_Account.credit_in_account_currency.as_(
                                "representative_company_credit"
                            ),
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
                            Journal_Entry.posting_date.as_(
                                "party_journal_posting_date"
                            ),
                            # total_amount,
                            Journal_Entry_Account.debit_in_account_currency.as_(
                                "representative_company_debit"
                            ),
                            Journal_Entry_Account.credit_in_account_currency.as_(
                                "representative_company_credit"
                            ),
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

            merged_reference_journals = {}
            merged_party_journals = {}

            for journal in journals:
                journal_item = journal["reference_journal"]
                if journal_item in merged_reference_journals:
                    # merged_reference_journals[journal_item][
                    #     "total_debit_or_credit"
                    # ] += journal["total_debit_or_credit"]
                    merged_reference_journals[journal_item][
                        "reference_company_credit"
                    ] += journal["reference_company_credit"]
                    merged_reference_journals[journal_item][
                        "reference_company_debit"
                    ] += journal["reference_company_debit"]
                else:
                    merged_reference_journals[journal_item] = {
                        "reference_company": journal["reference_company"],
                        "representative_company": journal["representative_company"],
                        "reference_journal": journal_item,
                        "reference_journal_posting_date": journal[
                            "reference_journal_posting_date"
                        ],
                        # "total_debit_or_credit": journal["total_debit_or_credit"],
                        "reference_company_credit": journal["reference_company_credit"],
                        "reference_company_debit": journal["reference_company_debit"],
                        "party_journal": journal["party_journal"],
                    }

            journals = list(merged_reference_journals.values())

            if self.amount_journals:
                for a in self.amount_journals:
                    journal_item = a["party_journal"]
                    if journal_item in merged_party_journals:
                        # merged_party_journals[journal_item][
                        #     "total_credit_or_debit"
                        # ] += a["total_credit_or_debit"]
                        merged_party_journals[journal_item][
                            "representative_company_credit"
                        ] += a["representative_company_credit"]
                        merged_party_journals[journal_item][
                            "representative_company_debit"
                        ] += a["representative_company_debit"]
                    else:
                        merged_party_journals[journal_item] = {
                            # "total_credit_or_debit": a["total_credit_or_debit"],
                            "party_journal": a["party_journal"],
                            "party_journal_posting_date": a[
                                "party_journal_posting_date"
                            ],
                            "representative_company_credit": a[
                                "representative_company_credit"
                            ],
                            "representative_company_debit": a[
                                "representative_company_debit"
                            ],
                        }
                self.amount_journals = list(merged_party_journals.values())

                for journal in journals:
                    matched = False
                    for amount_journal in self.amount_journals:
                        # if journal.get("total_debit_or_credit") == amount_journal.get(
                        #     "total_credit_or_debit"
                        # ):
                        #     pass

                        if journal.get("reference_company_debit") == amount_journal.get(
                            "representative_company_credit"
                        ) and (journal.get("reference_company_debit") > 0):
                            # merged_journal = journal.copy()
                            merged_journal = copy.deepcopy(journal)
                            # merged_journal["total_credit_or_debit"] = (
                            #     amount_journal.get("total_credit_or_debit")
                            # )
                            merged_journal["representative_company_credit"] = (
                                amount_journal.get("representative_company_credit")
                            )
                            merged_journal["representative_company_debit"] = (
                                amount_journal.get("representative_company_debit")
                            )
                            merged_journal["party_journal"] = amount_journal.get(
                                "party_journal"
                            )
                            merged_journal["party_journal_posting_date"] = (
                                amount_journal.get("party_journal_posting_date")
                            )
                            self.data.append(merged_journal)
                            matched = True
                            break
                    if not matched:
                        self.data.append(journal)


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
