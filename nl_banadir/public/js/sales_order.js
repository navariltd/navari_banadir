frappe.ui.form.on("Sales Order", {
    refresh: function (frm) {
        frm.add_custom_button(
            __("GL Payment Entry"),
            function () {
                if (!frm.doc.docstatus) {
                    frappe.msgprint(__("Please save the Sales Order before creating a payment entry."));
                    return;
                }

                frappe.call({
                    method: "nl_banadir.banadir_customization_reports.controllers.sales_order.create_payment_entry",
                    args: {
                        sales_order: "Sales Order", 
                        sales_order_name: frm.doc.name,
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.set_route("Form", "Payment Entry", r.message.name);
                        }
                    },
                    error: function (err) {
                        frappe.msgprint(__("An error occurred while creating the payment entry."));
                        console.error(err);
                    }
                });
            },
            __("Create")
        );
    },
});
