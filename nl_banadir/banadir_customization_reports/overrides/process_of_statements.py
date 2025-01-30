import frappe
from frappe.www.printview import get_letter_head, get_print_style
from frappe.utils.pdf import get_pdf
from frappe.utils import add_days, add_months, getdate, today

from erpnext import get_company_currency
from erpnext.accounts.party import get_party_account_currency
from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
    execute as get_ar_soa,
)
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from erpnext.accounts.doctype.process_statement_of_accounts.process_statement_of_accounts import (
    get_ar_filters,
    get_gl_filters,
    set_ageing,
    get_common_filters,
    get_context,
    get_recipients_and_cc,
)


def get_html(doc, filters, entry, col, res, ageing):
    base_template_path = "frappe/www/printview.html"
    template_path = (
        "nl_banadir/templates/process_statement_of_accounts.html"
        if doc.report == "General Ledger"
        else "nl_banadir/templates/process_statement_of_accounts_accounts_receivable.html"
    )

    if doc.letter_head:
        letter_head = get_letter_head(doc, 0)

    html = frappe.render_template(
        template_path,
        {
            "filters": filters,
            "data": res,
            "report": {"report_name": doc.report, "columns": col},
            "ageing": ageing[0] if (doc.include_ageing and ageing) else None,
            "letter_head": letter_head if doc.letter_head else None,
            "terms_and_conditions": (
                frappe.db.get_value(
                    "Terms and Conditions", doc.terms_and_conditions, "terms"
                )
                if doc.terms_and_conditions
                else None
            ),
        },
    )

    html = frappe.render_template(
        base_template_path,
        {
            "body": html,
            "css": get_print_style(),
            "title": "Statement For " + entry.customer,
        },
    )
    return html


def get_report_pdf(doc, consolidated=True):
    statement_dict = get_statement_dict(doc)
    if not bool(statement_dict):
        return False
    elif consolidated:
        delimiter = (
            '<div style="page-break-before: always;"></div>'
            if doc.include_break
            else ""
        )
        result = delimiter.join(list(statement_dict.values()))
        return get_pdf(result, {"orientation": doc.orientation})
    else:
        for customer, statement_html in statement_dict.items():
            statement_dict[customer] = get_pdf(
                statement_html, {"orientation": doc.orientation}
            )
        return statement_dict


def get_statement_dict(doc, get_statement_dict=False):
    statement_dict = {}
    ageing = ""

    for entry in doc.customers:
        if doc.include_ageing:
            ageing = set_ageing(doc, entry)

        tax_id = frappe.get_doc("Customer", entry.customer).tax_id
        presentation_currency = (
            get_party_account_currency("Customer", entry.customer, doc.company)
            or doc.currency
            or get_company_currency(doc.company)
        )

        filters = get_common_filters(doc)
        if doc.ignore_exchange_rate_revaluation_journals:
            filters.update({"ignore_err": True})

        if doc.ignore_cr_dr_notes:
            filters.update({"ignore_cr_dr_notes": True})

        if doc.report == "General Ledger":
            filters.update(get_gl_filters(doc, entry, tax_id, presentation_currency))
            col, res = get_soa(filters)
            for x in [0, -2, -1]:
                res[x]["account"] = res[x]["account"].replace("'", "")
            if len(res) == 3:
                continue
        else:
            filters.update(get_ar_filters(doc, entry))
            ar_res = get_ar_soa(filters)
            col, res = ar_res[0], ar_res[1]
            if not res:
                continue

        statement_dict[entry.customer] = (
            [res, ageing]
            if get_statement_dict
            else get_html(doc, filters, entry, col, res, ageing)
        )

    return statement_dict


@frappe.whitelist()
def download_statements(document_name):
    doc = frappe.get_doc("Process Statement Of Accounts", document_name)
    report = get_report_pdf(doc)
    if report:
        frappe.local.response.filename = doc.name + ".pdf"
        frappe.local.response.filecontent = report
        frappe.local.response.type = "download"


@frappe.whitelist()
def send_emails(document_name, from_scheduler=False, posting_date=None):
    doc = frappe.get_doc("Process Statement Of Accounts", document_name)
    report = get_report_pdf(doc, consolidated=False)

    if report:
        for customer, report_pdf in report.items():
            context = get_context(customer, doc)
            filename = frappe.render_template(doc.pdf_name, context)
            attachments = [{"fname": filename + ".pdf", "fcontent": report_pdf}]

            recipients, cc = get_recipients_and_cc(customer, doc)
            if not recipients:
                continue

            subject = frappe.render_template(doc.subject, context)
            message = frappe.render_template(doc.body, context)

            if doc.sender:
                sender_email = frappe.db.get_value(
                    "Email Account", doc.sender, "email_id"
                )
            else:
                sender_email = frappe.session.user

            frappe.enqueue(
                queue="short",
                method=frappe.sendmail,
                recipients=recipients,
                sender=sender_email,
                cc=cc,
                subject=subject,
                message=message,
                now=True,
                reference_doctype="Process Statement Of Accounts",
                reference_name=document_name,
                attachments=attachments,
                expose_recipients="header",
            )

        if doc.enable_auto_email and from_scheduler:
            new_to_date = getdate(posting_date or today())
            if doc.frequency == "Weekly":
                new_to_date = add_days(new_to_date, 7)
            else:
                new_to_date = add_months(
                    new_to_date, 1 if doc.frequency == "Monthly" else 3
                )
            new_from_date = add_months(new_to_date, -1 * doc.filter_duration)
            doc.add_comment(
                "Comment",
                "Emails sent on: " + frappe.utils.format_datetime(frappe.utils.now()),
            )
            if doc.report == "General Ledger":
                doc.db_set("to_date", new_to_date, commit=True)
                doc.db_set("from_date", new_from_date, commit=True)
            else:
                doc.db_set("posting_date", new_to_date, commit=True)
        return True
    else:
        return False
