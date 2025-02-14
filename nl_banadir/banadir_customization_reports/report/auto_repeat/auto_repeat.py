# Copyright (c) 2025, Navari Ltd and contributors
# For license information, please see license.txt

from typing import TypedDict

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.query_builder import DocType


class AutoRepeatFilter(TypedDict):
    company: str | None
    reference_doctype: str | None
    reference_document: str | None
    start_date: str
    end_date: str


def execute(filters: AutoRepeatFilter | None = None):
    return AutoRepeat(filters).run()


class AutoRepeat:
    def __init__(self, filters: AutoRepeatFilter | None) -> None:
        self.filters = filters
        self.start_date = getdate(filters.get("start_date"))
        self.end_date = getdate(filters.get("end_date"))
        self.data = []
        self.columns = []

    def run(self):
        if not self.columns:
            self.columns = self.get_columns()

        if self.filters:
            self.data = self.get_data()

        return self.columns, self.data

    def get_columns(self):
        columns = [
            {
                "label": "Company",
                "fieldname": "company",
                "fieldtype": "Link",
                "options": "Company",
                "width": "300",
            },
            {
                "label": "Auto Repeat Number",
                "fieldname": "auto_repeat",
                "fieldtype": "Link",
                "options": "Auto Repeat",
                "width": "200",
            },
            {
                "label": "Reference Document",
                "fieldname": "reference_document",
                "fieldtype": "Data",
                "width": "200",
            },
            # {
            #     "label": "Journal Entry",
            #     "fieldname": "journal_entry",
            #     "fieldtype": "Link",
            #     "options": "Journal Entry",
            #     "width": "200",
            # },
            {
                "label": "Start Date",
                "fieldname": "start_date",
                "fieldtype": "Date",
                "width": "200",
            },
            {
                "label": "End Date",
                "fieldname": "end_date",
                "fieldtype": "Date",
                "width": "200",
            },
            {
                "label": "Status",
                "fieldname": "status",
                "fieldtype": "Data",
                "width": "200",
            },
            {
                "label": "Frequency",
                "fieldname": "frequency",
                "fieldtype": "Data",
                "width": "200",
            },
            {
                "label": "Next Schedule Date",
                "fieldname": "next_schedule_date",
                "fieldtype": "Data",
                "width": "200",
            },
        ]
        return columns

    def get_data(self):
        ar_doctype = DocType("Auto Repeat")
        ref_doctype = DocType(self.filters.get("reference_doctype"))

        query = (
            frappe.qb.from_(ar_doctype)
            .join(ref_doctype)
            .on(ref_doctype.name == ar_doctype.reference_document)
            .select(
                ar_doctype.name.as_("auto_repeat"),
                ar_doctype.reference_document,
                ar_doctype.start_date,
                ar_doctype.end_date,
                ar_doctype.status,
                ar_doctype.frequency,
                ar_doctype.next_schedule_date,
                ref_doctype.company,
            )
        )

        if self.filters.get("company"):
            query = query.where(ref_doctype.company == self.filters.get("company"))

        if self.filters.get("reference_doctype"):
            query = query.where(
                ar_doctype.reference_doctype == self.filters.get("reference_doctype")
            )

        if self.filters.get("reference_document"):
            query = query.where(
                ar_doctype.reference_document == self.filters.get("reference_document")
            )

        query = query.where(
            (ar_doctype.docstatus < 2)
            & (ar_doctype.start_date >= self.start_date)
            & (ar_doctype.end_date <= self.end_date)
        )
        return query.run(as_dict=True)
