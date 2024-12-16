app_name = "nl_banadir"
app_title = "Banadir Customization-Reports"
app_publisher = "Navari Ltd"
app_description = "Banadir Reports"
app_email = "mania@navari.co.ke"
app_license = "agpl-3.0"
# required_apps = []

# Includes in <head>
# ------------------

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                (
                    "Material Request-task",
                    "Employee-nhif_no",
                    "Employee-nssf_no",
                    "Employee-tax_id",
                    "Salary Component-p9a_tax_deduction_card_type",
                ),
            ]
        ],
    },
]

doc_events = {
	"Sales Invoice": {
		"before_submit": "nl_banadir.banadir_customization_reports.controllers.assign_and_share.sales_invoice_before_submit",
		
	},
 "Purchase Invoice": {
        "before_submit": "nl_banadir.banadir_customization_reports.controllers.assign_and_share.purchase_invoice_before_submit",
        
    },
    "Payment Entry": {
        "before_submit": "nl_banadir.banadir_customization_reports.controllers.assign_and_share.payment_entry_before_submit",
        
    },
    "Journal Entry": {
        "before_save":"nl_banadir.banadir_customization_reports.controllers.negative_cash.before_save",
        "before_submit": "nl_banadir.banadir_customization_reports.controllers.assign_and_share.journal_entry_before_submit",
},
    "Production Plan":{
        "autoname":"nl_banadir.banadir_customization_reports.controllers.production_plan.auto_name",
        "on_submit":"nl_banadir.banadir_customization_reports.controllers.production_plan.sync_sequence"
    },
     "Work Order":{
        "autoname":"nl_banadir.banadir_customization_reports.controllers.production_plan.auto_name",
        "before_save":"nl_banadir.banadir_customization_reports.controllers.work_order.before_save",
        "on_submit":"nl_banadir.banadir_customization_reports.controllers.work_order.on_submit",
        "on_update_after_submit":"nl_banadir.banadir_customization_reports.controllers.work_order.on_update",

    },
     "Stock Entry":{
         "before_save":"nl_banadir.banadir_customization_reports.controllers.stock_entry.before_save"
     }
}

# include js, css files in header of desk.html
# app_include_css = "/assets/nl_banadir/css/nl_banadir.css"
# app_include_js = "/assets/nl_banadir/js/nl_banadir.js"

# include js, css files in header of web template
# web_include_css = "/assets/nl_banadir/css/nl_banadir.css"
# web_include_js = "/assets/nl_banadir/js/nl_banadir.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "nl_banadir/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Work Order" : "public/js/work_order.js",
    "Purchase Order":"public/js/purchase_order.js",
    "Production Plan":"public/js/production_plan.js",
    }

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "nl_banadir/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "nl_banadir.utils.jinja_methods",
# 	"filters": "nl_banadir.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "nl_banadir.install.before_install"
# after_install = "nl_banadir.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "nl_banadir.uninstall.before_uninstall"
# after_uninstall = "nl_banadir.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "nl_banadir.utils.before_app_install"
# after_app_install = "nl_banadir.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "nl_banadir.utils.before_app_uninstall"
# after_app_uninstall = "nl_banadir.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "nl_banadir.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#     "Sales Invoice": "nl_banadir.banadir_customization_reports.controllers.user_permision.custom_has_permission"

# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"nl_banadir.tasks.all"
# 	],
# 	"daily": [
# 		"nl_banadir.tasks.daily"
# 	],
# 	"hourly": [
# 		"nl_banadir.tasks.hourly"
# 	],
# 	"weekly": [
# 		"nl_banadir.tasks.weekly"
# 	],
# 	"monthly": [
# 		"nl_banadir.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "nl_banadir.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "nl_banadir.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "nl_banadir.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["nl_banadir.utils.before_request"]
# after_request = ["nl_banadir.utils.after_request"]

# Job Events
# ----------
# before_job = ["nl_banadir.utils.before_job"]
# after_job = ["nl_banadir.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"nl_banadir.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

