

frappe.ui.form.on('Work Order Operations Item', {
    operations: function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, 'default_currency', (r) => {
                if (r && r.default_currency) {

                    frappe.model.set_value(cdt, cdn, 'currency', r.default_currency);
                }
            });
        } else {
            frappe.msgprint(__('Please select a company in the Work Order.'));
        }
    }
});
