# Copyright (c) 2024, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
import erpnext
import copy
from frappe.query_builder import DocType, Case, Field
from frappe.utils import getdate
from erpnext.accounts.report.utils import convert

from collections import defaultdict


class InterCompanyFilter(TypedDict):
    reference_company: str | None
    party_type: str | None
    party: str | None
    from_date: str
    to_date: str
    compare_by_amount: bool
    compare_randomly: bool
    ignore_exchange_gain_or_loss: bool


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

        if (
            not self.filters.get("compare_by_amount")
            and self.filters.get("reference_company")
            and self.filters.get("party_type")
        ):
            self.get_intercompany_journals()

        if self.filters.get("compare_by_amount"):
            self.compare_journals_by_amount()

        if self.filters.get("party_type"):
            self.get_invoice_data()

        self.calculate_closing_balance()

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
                "label": "Reference Company Closing Balance",
                "fieldname": "reference_company_closing_balance",
                "fieldtype": "Currency",
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
            {
                "label": "Representative Company Closing Balance",
                "fieldname": "representative_company_closing_balance",
                "fieldtype": "Currency",
                "width": "100",
            },
        ]

        if self.filters.get("party_type") == "Customer":
            columns.insert(
                5,
                {
                    "label": "Sales Invoice",
                    "fieldname": "s_name",
                    "fieldtype": "Link",
                    "options": "Sales Invoice",
                    "width": "100",
                },
            )

            columns.insert(
                6,
                {
                    "label": "Sales Invoice Total",
                    "fieldname": "s_invoice_total",
                    "fieldtype": "Currency",
                    "width": "100",
                },
            )

            columns.insert(
                -1,
                {
                    "label": "Purchase Invoice Total",
                    "fieldname": "p_invoice_total",
                    "fieldtype": "Currency",
                    "width": "100",
                },
            )

            columns.insert(
                -2,
                {
                    "label": "Purchase Invoice",
                    "fieldname": "p_name",
                    "fieldtype": "Link",
                    "options": "Purchase Invoice",
                    "width": "100",
                },
            )

        if self.filters.get("party_type") == "Supplier":
            columns.insert(
                5,
                {
                    "label": "Purchase Invoice",
                    "fieldname": "p_name",
                    "fieldtype": "Link",
                    "options": "Purchase Invoice",
                    "width": "100",
                },
            )

            columns.insert(
                6,
                {
                    "label": "Purchase Invoice Total",
                    "fieldname": "p_invoice_total",
                    "fieldtype": "Currency",
                    "width": "100",
                },
            )

            columns.insert(
                -1,
                {
                    "label": "Sales Invoice Total",
                    "fieldname": "s_invoice_total",
                    "fieldtype": "Currency",
                    "width": "100",
                },
            )

            columns.insert(
                -2,
                {
                    "label": "Sales Invoice",
                    "fieldname": "s_name",
                    "fieldtype": "Link",
                    "options": "Sales Invoice",
                    "width": "100",
                },
            )
        return columns

    def get_intercompany_journals(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

            query = (
                frappe.qb.from_(Journal_Entry_Account)
                .join(Journal_Entry)
                .on(Journal_Entry_Account.parent == Journal_Entry.name)
                .select(
                    Journal_Entry.company.as_("reference_company"),
                    Journal_Entry_Account.party.as_("representative_company"),
                    Journal_Entry.name.as_("reference_journal"),
                    Journal_Entry.posting_date.as_("reference_journal_posting_date"),
                    Journal_Entry_Account.debit_in_account_currency.as_(
                        "reference_company_debit"
                    ),
                    Journal_Entry_Account.credit_in_account_currency.as_(
                        "reference_company_credit"
                    ),
                    Journal_Entry.inter_company_journal_entry_reference.as_(
                        "party_journal"
                    ),
                    Journal_Entry.voucher_type,
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
                    (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                    & (Journal_Entry.docstatus == 1)
                )
            )

            if self.filters.get("party"):
                query = query.where(
                    Journal_Entry_Account.party == self.filters.get("party")[0]
                )

            if self.filters.get("ignore_exchange_gain_or_loss"):
                query = query.where(
                    Journal_Entry.voucher_type != "Exchange Gain Or Loss"
                )
            # Loop through the data, if it has a party journal, get the value of the debit/credit
            journals = query.run(as_dict=True)

            merged_reference_journals = {}

            for journal in journals:
                journal_item = journal["reference_journal"]
                if journal.get("voucher_type") != "Opening Entry":
                    if journal_item in merged_reference_journals:
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
                            "reference_company_debit": journal[
                                "reference_company_debit"
                            ],
                            "reference_company_credit": journal[
                                "reference_company_credit"
                            ],
                            "party_journal": journal["party_journal"],
                            "reference_journal_posting_date": journal[
                                "reference_journal_posting_date"
                            ],
                            "reference_company_closing_balance": None,
                            "representative_company_closing_balance": None,
                        }

            journals = list(merged_reference_journals.values())

            for journal in journals:
                if journal.get("party_journal"):
                    party_data = self.get_party_journal(journal=journal)
                    if party_data:
                        merged_journal = journal.copy()
                        merged_journal["party_journal_posting_date"] = party_data[
                            0
                        ].party_journal_posting_date
                        merged_journal["representative_company_debit"] = party_data[
                            0
                        ].representative_company_debit
                        merged_journal["representative_company_credit"] = party_data[
                            0
                        ].representative_company_credit
                        self.data.append(merged_journal)
                else:
                    updated_item = {
                        "representative_company": None,
                        "representative_company_credit": None,
                        "representative_company_debit": None,
                    }
                    self.data.append({**journal, **updated_item})

            if self.filters.get("compare_randomly"):
                self.data = []
                self.filters.get("compare_by_amount") == False
                party_journals = self.get_journal_entries()
                opening_entries = self.get_reverse_opening_entries()

                if party_journals and not journals:
                    if opening_entries:
                        sorted_party_journals = self.sort_party_journals(
                            party_journals=party_journals,
                            opening_entries=opening_entries,
                        )
                        self.process_party_journals(sorted_party_journals)
                    else:
                        sorted_party_journals = self.sort_party_journals(
                            party_journals=party_journals
                        )
                        self.process_party_journals(sorted_party_journals)

                if journals and not party_journals:
                    if opening_entries:
                        for entry in opening_entries:
                            opening_entry = {
                                "is_opening": True,
                                "reference_journal_posting_date": entry.get(
                                    "party_journal_posting_date"
                                ),
                                "reference_company": entry.get(
                                    "representative_company"
                                ),
                                "reference_company_debit": entry.get(
                                    "representative_company_debit"
                                ),
                                "reference_company_credit": entry.get(
                                    "representative_company_credit"
                                ),
                                "reference_journal": entry.get("party_journal"),
                                "party_journal": None,
                                "representative_company": "Opening Entry",
                                "party_journal_posting_date": None,
                                "representative_company_debit": None,
                                "representative_company_credit": None,
                                "reference_company_closing_balance": None,
                                "representative_company_closing_balance": None,
                            }
                            journals.append({**entry, **opening_entry})
                    self.process_reference_journals(journals=journals)

                if journals and party_journals:
                    if opening_entries:
                        for entry in opening_entries:
                            party_journals.append(entry)

                    sorted_party_journals = sorted(
                        party_journals,
                        key=lambda x: x.get("voucher_type") != "Opening Entry",
                    )

                    updated_journals = []
                    matched_journals = []
                    i = 0

                    while i < len(journals):
                        item = journals[i]
                        if i < len(sorted_party_journals):
                            if (
                                sorted_party_journals[i].get("voucher_type")
                                == "Opening Entry"
                            ):
                                if sorted_party_journals[i].get("is_reverse"):
                                    opening_entry = {
                                        "is_opening": True,
                                        "reference_journal_posting_date": sorted_party_journals[
                                            i
                                        ].get(
                                            "party_journal_posting_date"
                                        ),
                                        "reference_company": sorted_party_journals[
                                            i
                                        ].get("representative_company"),
                                        "reference_company_debit": sorted_party_journals[
                                            i
                                        ].get(
                                            "representative_company_debit"
                                        ),
                                        "reference_company_credit": sorted_party_journals[
                                            i
                                        ].get(
                                            "representative_company_credit"
                                        ),
                                        "reference_journal": sorted_party_journals[
                                            i
                                        ].get("party_journal"),
                                        "party_journal": None,
                                        "representative_company": "Opening Entry",
                                        "party_journal_posting_date": None,
                                        "representative_company_debit": None,
                                        "representative_company_credit": None,
                                        "reference_company_closing_balance": None,
                                        "representative_company_closing_balance": None,
                                    }
                                    updated_journals.append({**opening_entry})
                                    matched_journals.append(sorted_party_journals[i])

                                else:
                                    opening_entry = {
                                        "is_opening": True,
                                        "reference_journal_posting_date": "",
                                        "reference_company": "Opening Entry",
                                        "reference_company_debit": None,
                                        "reference_company_credit": None,
                                        "representative_company": sorted_party_journals[
                                            i
                                        ].get("representative_company"),
                                        "reference_company_closing_balance": None,
                                        "representative_company_closing_balance": None,
                                    }
                                    updated_journals.append(
                                        {**sorted_party_journals[i], **opening_entry}
                                    )
                                    matched_journals.append(sorted_party_journals[i])
                                journals.append(item)
                            else:
                                updated_item = {**item, **sorted_party_journals[i]}
                                updated_journals.append(updated_item)
                                matched_journals.append(sorted_party_journals[i])
                        else:
                            updated_item = {
                                "highlight": True,
                                "representative_company": None,
                                "representative_company_debit": None,
                                "representative_company_credit": None,
                                "representative_company_closing_balance": None,
                                "representative_company_closing_balance": None,
                            }
                            updated_journals.append({**item, **updated_item})

                        i += 1

                    for item in sorted_party_journals:
                        if (
                            item not in matched_journals
                            and item.get("voucher_type") != "Opening Entry"
                        ):
                            updated_item = {
                                "highlight": True,
                                "reference_company_debit": None,
                                "reference_company_credit": None,
                                "reference_company_closing_balance": None,
                                "representative_company_closing_balance": None,
                            }
                            updated_journals.append({**item, **updated_item})

                    sorted_journals = sorted(
                        updated_journals,
                        key=lambda x: x.get("voucher_type") != "Opening Entry",
                    )
                    self.data = sorted_journals

    def process_reference_journals(self, journals):
        updated_journals = []
        for journal in journals:

            if journal.get("voucher_type") == "Opening Entry" and not journal.get(
                "is_reverse"
            ):
                opening_entry = {
                    "is_opening": True,
                    "voucher_type": "Opening Entry",
                    "reference_journal_posting_date": journal[
                        "reference_journal_posting_date"
                    ],
                    "reference_company": journal.get("reference_company"),
                    "reference_company_debit": journal.get("reference_company_debit"),
                    "reference_company_credit": journal.get("reference_company_credit"),
                    "reference_journal": journal.get("reference_journal"),
                    "party_journal": None,
                    "representative_company": "Opening Entry",
                    "party_journal_posting_date": None,
                    "representative_company_debit": None,
                    "representative_company_credit": None,
                    "reference_company_closing_balance": None,
                    "representative_company_closing_balance": None,
                }
                updated_journals.append({**opening_entry})

            if journal.get("is_reverse"):
                updated_journals.append(journal)

        for journal in journals:
            if journal.get("voucher_type") != "Opening Entry":
                updated_item = {
                    "representative_company": None,
                    "representative_company_credit": None,
                    "representative_company_debit": None,
                }
                updated_journals.append({**journal, **updated_item})

        sorted_journals = sorted(
            updated_journals,
            key=lambda x: x.get("voucher_type") != "Opening Entry",
        )

        self.data = sorted_journals

    def process_party_journals(self, journals):
        updated_journals = []
        for journal in journals:
            if journal.get("voucher_type") == "Opening Entry":
                if journal.get("is_reverse"):
                    opening_entry = {
                        "is_opening": True,
                        "reference_journal_posting_date": journal.get(
                            "party_journal_posting_date"
                        ),
                        "reference_company": journal.get("representative_company"),
                        "reference_company_debit": journal.get(
                            "representative_company_debit"
                        ),
                        "reference_company_credit": journal.get(
                            "representative_company_credit"
                        ),
                        "reference_journal": journal.get("party_journal"),
                        "party_journal": None,
                        "representative_company": "Opening Entry",
                        "party_journal_posting_date": None,
                        "representative_company_debit": None,
                        "representative_company_credit": None,
                        "reference_company_closing_balance": None,
                        "representative_company_closing_balance": None,
                    }
                    updated_journals.append({**opening_entry})

                else:
                    opening_entry = {
                        "is_opening": True,
                        "reference_journal_posting_date": "",
                        "reference_company": "Opening Entry",
                        "reference_company_debit": None,
                        "reference_company_credit": None,
                        "representative_company": journal.get("representative_company"),
                        "reference_company_closing_balance": None,
                        "representative_company_closing_balance": None,
                    }
                    updated_journals.append({**journal, **opening_entry})
            else:
                updated_item = {
                    "reference_company_debit": None,
                    "reference_company_credit": None,
                    "reference_company_closing_balance": None,
                }
                updated_journals.append({**journal, **updated_item})

        self.data = updated_journals

    def sort_party_journals(self, party_journals, opening_entries=[]):
        party_journals = party_journals
        if opening_entries:
            for entry in opening_entries:
                party_journals.append(entry)

        sorted_party_journals = sorted(
            party_journals,
            key=lambda x: x.get("voucher_type") != "Opening Entry",
        )

        return sorted_party_journals

    def get_journal_entries(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")
        party_type = (
            "Customer" if self.filters.get("party_type") == "Supplier" else "Supplier"
        )

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == Journal_Entry.name)
            .select(
                Journal_Entry.name.as_("party_journal"),
                Journal_Entry_Account.debit_in_account_currency.as_(
                    "representative_company_debit"
                ),
                Journal_Entry_Account.credit_in_account_currency.as_(
                    "representative_company_credit"
                ),
                Journal_Entry.posting_date.as_("party_journal_posting_date"),
                Journal_Entry.voucher_type,
                Journal_Entry.company.as_("representative_company"),
            )
            .where(Journal_Entry_Account.party_type == party_type)
            .where(Journal_Entry_Account.party == self.filters.get("reference_company"))
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                & (Journal_Entry.docstatus == 1)
            )
        )

        if self.filters.get("party"):
            query = query.where(Journal_Entry.company == self.filters.get("party")[0])

        if self.filters.get("ignore_exchange_gain_or_loss"):
            query = query.where(Journal_Entry.voucher_type != "Exchange Gain Or Loss")

        data = query.run(as_dict=True)

        merged_journals = {}

        for d in data:
            item = d["party_journal"]
            if item in merged_journals:
                merged_journals[item]["representative_company_debit"] += d[
                    "representative_company_debit"
                ]
                merged_journals[item]["representative_company_credit"] += d[
                    "representative_company_credit"
                ]

            else:
                merged_journals[item] = {**d}

        return list(merged_journals.values())

    def get_party_journal(self, journal):
        Journal_Entry = DocType("Journal Entry")
        Journal_Entry_Account = DocType("Journal Entry Account")
        party_type = (
            "Customer" if self.filters.get("party_type") == "Supplier" else "Supplier"
        )

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == journal.get("party_journal"))
            .select(
                Journal_Entry_Account.debit_in_account_currency.as_(
                    "representative_company_debit"
                ),
                Journal_Entry_Account.credit_in_account_currency.as_(
                    "representative_company_credit"
                ),
                Journal_Entry.posting_date.as_("party_journal_posting_date"),
            )
            .where(Journal_Entry_Account.party_type == party_type)
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                & (Journal_Entry.docstatus == 1)
            )
            .where(Journal_Entry.name == journal.get("party_journal"))
        )

        if self.filters.get("party"):
            query = query.where(Journal_Entry.company == self.filters.get("party")[0])

        if self.filters.get("ignore_exchange_gain_or_loss"):
            query = query.where(Journal_Entry.voucher_type != "Exchange Gain Or Loss")

        return query.run(as_dict=True)

    def compare_journals_by_amount(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")

        if self.filters.get("reference_company") and self.filters.get("party_type"):
            party_type = self.filters.get("party_type")

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
                    Journal_Entry.voucher_type,
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
                    (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                    & (Journal_Entry.docstatus == 1)
                )
            )

            if self.filters.get("party"):
                query = query.where(
                    Journal_Entry_Account.party == self.filters.get("party")[0]
                )

            if self.filters.get("ignore_exchange_gain_or_loss"):
                query = query.where(
                    Journal_Entry.voucher_type != "Exchange Gain Or Loss"
                )

            journals = query.run(as_dict=True)

            if self.filters.get("compare_by_amount"):
                party_type = "Supplier" if party_type == "Customer" else "Customer"

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
                            Journal_Entry.voucher_type,
                        )
                        .where(Journal_Entry_Account.party_type == party_type)
                        .where(
                            Journal_Entry_Account.party
                            == self.filters.get("reference_company")
                        )
                        .where(
                            (Journal_Entry.posting_date >= self.from_date)
                            & (Journal_Entry.posting_date <= self.to_date)
                        )
                        .where(
                            (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                            & (Journal_Entry.docstatus == 1)
                        )
                    )

                    if self.filters.get("party"):
                        amount_query = amount_query.where(
                            Journal_Entry.company == self.filters.get("party")[0]
                        )

                    if self.filters.get("ignore_exchange_gain_or_loss"):
                        amount_query = amount_query.where(
                            Journal_Entry.voucher_type != "Exchange Gain Or Loss"
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
                            Journal_Entry.voucher_type,
                        )
                        .where(Journal_Entry_Account.party_type == party_type)
                        .where(
                            Journal_Entry_Account.party
                            == self.filters.get("reference_company")
                        )
                        .where(
                            (Journal_Entry.posting_date >= self.from_date)
                            & (Journal_Entry.posting_date <= self.to_date)
                        )
                        .where(
                            (Journal_Entry.voucher_type != "Exchange Rate Revaluation")
                            & (Journal_Entry.docstatus == 1)
                        )
                    )

                    if self.filters.get("party"):
                        amount_query = amount_query.where(
                            Journal_Entry.company == self.filters.get("party")[0]
                        )

                    if self.filters.get("ignore_exchange_gain_or_loss"):
                        amount_query = amount_query.where(
                            Journal_Entry.voucher_type != "Exchange Gain Or Loss"
                        )

                    self.amount_journals = amount_query.run(as_dict=True)

            merged_reference_journals = {}
            merged_party_journals = {}

            if journals:
                for journal in journals:
                    journal_item = journal["reference_journal"]
                    if journal_item in merged_reference_journals:
                        merged_reference_journals[journal_item][
                            "reference_company_credit"
                        ] += journal["reference_company_credit"]
                        merged_reference_journals[journal_item][
                            "reference_company_debit"
                        ] += journal["reference_company_debit"]
                    else:
                        merged_reference_journals[journal_item] = {
                            "voucher_type": journal["voucher_type"],
                            "reference_company": journal["reference_company"],
                            "representative_company": journal["representative_company"],
                            "reference_journal": journal_item,
                            "reference_journal_posting_date": journal[
                                "reference_journal_posting_date"
                            ],
                            "reference_company_credit": journal[
                                "reference_company_credit"
                            ],
                            "reference_company_debit": journal[
                                "reference_company_debit"
                            ],
                            "reference_company_closing_balance": None,
                            "representative_company_closing_balance": None,
                        }

                journals = list(merged_reference_journals.values())

            if self.amount_journals:
                for a in self.amount_journals:
                    journal_item = a["party_journal"]
                    if journal_item in merged_party_journals:
                        merged_party_journals[journal_item][
                            "representative_company_credit"
                        ] += a["representative_company_credit"]
                        merged_party_journals[journal_item][
                            "representative_company_debit"
                        ] += a["representative_company_debit"]
                    else:
                        merged_party_journals[journal_item] = {
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
                            "representative_company": a["company"],
                            "voucher_type": a["voucher_type"],
                            "reference_company_closing_balance": None,
                            "representative_company_closing_balance": None,
                        }
                self.amount_journals = list(merged_party_journals.values())

            if journals and not self.amount_journals:
                self.process_reference_journals(journals=journals)

            if self.amount_journals and not journals:
                self.process_party_journals(self.amount_journals)

            matched_amount_journals = []

            if journals and self.amount_journals:
                for journal in journals:

                    if journal.get("voucher_type") == "Opening Entry":
                        opening_entry = {
                            "is_opening": True,
                            "voucher_type": "Opening Entry",
                            "reference_journal_posting_date": journal[
                                "reference_journal_posting_date"
                            ],
                            "reference_company": journal.get("reference_company"),
                            "reference_company_debit": journal.get(
                                "reference_company_debit"
                            ),
                            "reference_company_credit": journal.get(
                                "reference_company_credit"
                            ),
                            "reference_journal": journal.get("reference_journal"),
                            "party_journal": None,
                            "representative_company": "Opening Entry",
                            "party_journal_posting_date": None,
                            "representative_company_debit": None,
                            "representative_company_credit": None,
                            "reference_company_closing_balance": None,
                            "representative_company_closing_balance": None,
                        }
                        self.data.append({**opening_entry})

                    matched = False
                    for amount_journal in self.amount_journals:
                        if (
                            journal.get("voucher_type") != "Opening Entry"
                            and amount_journal.get("voucher_type") != "Opening Entry"
                        ):
                            if (
                                (journal.get("reference_company_debit") > 0)
                                and (
                                    journal.get("reference_company_debit")
                                    == amount_journal.get(
                                        "representative_company_credit"
                                    )
                                )
                            ) or (
                                (journal.get("reference_company_credit") > 0)
                                and (
                                    journal.get("reference_company_credit")
                                    == amount_journal.get(
                                        "representative_company_debit"
                                    )
                                )
                            ):
                                if amount_journal not in matched_amount_journals:
                                    merged_journal = copy.deepcopy(journal)
                                    merged_journal["representative_company_credit"] = (
                                        amount_journal.get(
                                            "representative_company_credit"
                                        )
                                    )
                                    merged_journal["representative_company_debit"] = (
                                        amount_journal.get(
                                            "representative_company_debit"
                                        )
                                    )
                                    merged_journal["party_journal"] = (
                                        amount_journal.get("party_journal")
                                    )
                                    merged_journal["party_journal_posting_date"] = (
                                        amount_journal.get("party_journal_posting_date")
                                    )
                                    self.data.append(merged_journal)
                                    matched_amount_journals.append(amount_journal)
                                    matched = True
                                    break

                        if amount_journal.get("voucher_type") == "Opening Entry":

                            updated_journal = {}
                            opening_entry = {
                                "is_opening": True,
                                "reference_journal_posting_date": "",
                                "reference_company": "Opening Entry",
                                "reference_company_debit": None,
                                "reference_company_credit": None,
                                "representative_company": amount_journal.get("company"),
                                "reference_company_closing_balance": None,
                                "representative_company_closing_balance": None,
                            }

                            updated_journal = {**amount_journal, **opening_entry}

                            if updated_journal not in self.data:
                                self.data.append(updated_journal)

                    if not matched:
                        if journal.get("voucher_type") != "Opening Entry":
                            updated_data = {
                                "highlight": True,
                                "representative_company": None,
                                "representative_company_debit": None,
                                "representative_company_credit": None,
                            }
                            self.data.append({**journal, **updated_data})

                for item in self.amount_journals:
                    if (
                        item not in matched_amount_journals
                        and item.get("voucher_type") != "Opening Entry"
                    ):
                        updated_data = {
                            "highlight": True,
                            "reference_company_debit": None,
                            "reference_company_credit": None,
                        }

                        self.data.append({**item, **updated_data})

                    if not journals and item.get("voucher_type") == "Opening Entry":
                        opening_entry = {
                            "is_opening": True,
                            "reference_journal_posting_date": "",
                            "reference_company": "Opening Entry",
                            "reference_company_debit": None,
                            "reference_company_credit": None,
                            "representative_company": item.get("company"),
                            "reference_company_closing_balance": None,
                            "representative_company_closing_balance": None,
                        }
                        self.data.append({**item, **opening_entry})

                sorted_data = sorted(
                    self.data, key=lambda x: x.get("voucher_type") != "Opening Entry"
                )
                self.data = sorted_data

    def calculate_closing_balance(self):
        r_company_closing_balance = 0
        p_company_closing_balance = 0

        if self.data:
            for d in self.data:
                r_debit = d.get("reference_company_debit") or 0
                r_credit = d.get("reference_company_credit") or 0

                r_total = r_debit - r_credit
                r_company_closing_balance += r_total

                p_debit = d.get("representative_company_debit") or 0
                p_credit = d.get("representative_company_credit") or 0

                p_total = p_debit - p_credit
                p_company_closing_balance += p_total

            total_row = {
                "reference_journal_posting_date": "",
                "reference_company": "Reference Company Closing Balance",
                "reference_journal": "",
                "reference_company_debit": None,
                "reference_company_credit": None,
                "reference_company_closing_balance": r_company_closing_balance,
                "": "",
                "party_journal_posting_date": "",
                "representative_company": "Representative Company Closing Balance",
                "party_journal": "",
                "representative_company_debit": None,
                "representative_company_credit": None,
                "representative_company_closing_balance": p_company_closing_balance,
                "is_total": True,
            }
            self.data.append(total_row)

    def get_reverse_opening_entries(self):
        Journal_Entry_Account = DocType("Journal Entry Account")
        Journal_Entry = DocType("Journal Entry")
        party_type = self.filters.get("party_type")

        query = (
            frappe.qb.from_(Journal_Entry_Account)
            .join(Journal_Entry)
            .on(Journal_Entry_Account.parent == Journal_Entry.name)
            .select(
                Journal_Entry.name.as_("party_journal"),
                Journal_Entry_Account.debit_in_account_currency.as_(
                    "representative_company_debit"
                ),
                Journal_Entry_Account.credit_in_account_currency.as_(
                    "representative_company_credit"
                ),
                Journal_Entry.posting_date.as_("party_journal_posting_date"),
                Journal_Entry.voucher_type,
                Journal_Entry.company.as_("representative_company"),
            )
            .where(Journal_Entry_Account.party_type == party_type)
            .where(Journal_Entry.company == self.filters.get("reference_company"))
            .where(
                (Journal_Entry.posting_date >= self.from_date)
                & (Journal_Entry.posting_date <= self.to_date)
            )
            .where(
                (Journal_Entry.voucher_type == "Opening Entry")
                & (Journal_Entry.docstatus == 1)
            )
        )

        data = query.run(as_dict=True)

        merged_journals = {}

        for d in data:
            item = d["party_journal"]
            if item in merged_journals:
                merged_journals[item]["representative_company_debit"] += d[
                    "representative_company_debit"
                ]
                merged_journals[item]["representative_company_credit"] += d[
                    "representative_company_credit"
                ]

            else:

                merged_journals[item] = {**d, "is_reverse": True}

        return list(merged_journals.values())

    def invoice_query(self, invoice_doctype, invoice_type):
        # Ensure the invoice_type is lowercased for comparisons
        invoice_type = invoice_type.lower()

        company_field = Field("company").as_(
            "s_company" if invoice_type == "sales" else "p_company"
        )

        total_field = Field("grand_total").as_(
            "p_invoice_total" if invoice_type == "purchase" else "s_invoice_total"
        )

        party_field = (
            Field("supplier") if invoice_type == "purchase" else Field("customer")
        )

        voucher = Field("name").as_("s_name" if invoice_type == "sales" else "p_name")

        # Build the query using Frappe Query Builder
        query = frappe.qb.from_(invoice_doctype).select(
            company_field, total_field, party_field, voucher
        )

        if invoice_type == "sales" and self.filters.get("party_type") == "Customer":
            query = query.where(
                invoice_doctype.company == self.filters.get("reference_company")
            )

            if self.filters.get("party"):
                query = query.where(
                    invoice_doctype.customer == self.filters.get("party")[0]
                )

        if invoice_type == "purchase" and self.filters.get("party_type") == "Customer":
            query = query.where(
                invoice_doctype.supplier == self.filters.get("reference_company")
            )

            if self.filters.get("party"):
                query = query.where(
                    invoice_doctype.company == self.filters.get("party")[0]
                )

        if invoice_type == "sales" and self.filters.get("party_type") == "Supplier":
            query = query.where(
                invoice_doctype.customer == self.filters.get("reference_company")
            )

            if self.filters.get("party"):
                query = query.where(
                    invoice_doctype.company == self.filters.get("party")[0]
                )

        if invoice_type == "purchase" and self.filters.get("party_type") == "Supplier":
            query = query.where(
                invoice_doctype.company == self.filters.get("reference_company")
            )

            if self.filters.get("party"):
                query = query.where(
                    invoice_doctype.supplier == self.filters.get("party")[0]
                )

        return query.where(
            (invoice_doctype.posting_date >= self.from_date)
            & (invoice_doctype.posting_date <= self.to_date)
        ).run(as_dict=True)

    def get_invoice_data(self):
        SI_DOCTYPE = DocType("Sales Invoice")
        PI_DOCTYPE = DocType("Purchase Invoice")

        s_invoices = self.invoice_query(SI_DOCTYPE, "sales")
        p_invoices = self.invoice_query(PI_DOCTYPE, "purchase")

        combined_invoices = self.get_combined_dicts_with_missing_values(
            s_invoices, p_invoices
        )

        opening_entries_and_totals = self.get_opening_entries_and_totals(self.data)

        filtered_list = self.exclude_opening_entries_and_totals(self.data)
        updated_data = self.get_combined_dicts_with_missing_values(
            filtered_list, combined_invoices
        )

        for entry in opening_entries_and_totals:
            updated_data.append(entry)

        self.data = updated_data

    def get_combined_dicts_with_missing_values(self, list_a, list_b):
        combined = []
        max_length = max(len(list_a), len(list_b))

        list_a = list_a + ([{}] * (max_length - len(list_a)))
        list_b = list_b + ([{}] * (max_length - len(list_b)))

        for i in range(max_length):
            keys_a = list_a[i].keys() if len(list_a) > 0 else {}
            keys_b = list_b[i].keys() if len(list_b) > 0 else {}
            new_dict = {key: list_a[i].get(key) for key in keys_a}
            new_dict.update({key: list_b[i].get(key) for key in keys_b})
            combined.append(new_dict)

        return combined

    def exclude_opening_entries_and_totals(self, dict_list):
        return [d for d in dict_list if "is_opening" not in d and "is_total" not in d]

    def get_opening_entries_and_totals(self, dict_list):
        return [d for d in dict_list if "is_opening" in d or "is_total" in d]


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
