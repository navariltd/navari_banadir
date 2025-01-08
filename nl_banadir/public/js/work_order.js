frappe.ui.form.on('Work Order', {
    refresh: function (frm) {
        if (frm.doc.custom_subcontractors) {
            frm.doc.custom_subcontractors.forEach(row => {
                const fields_to_update = ['status', 'item', 'rate', 'supplier', 'in_progress', 'completed_date'];
                if (row.invoice_created == 1) {
                    // Make specific fields readonly and disallow changes on submit
                    fields_to_update.forEach(field => {
                        frappe.meta.get_docfield('Work Order Operations Item', field, frm.doc.name).read_only = 1;
                        frappe.meta.get_docfield('Work Order Operations Item', field, frm.doc.name).allow_on_submit = 0;
                    });
                } else {
                    // Make fields editable and allow changes on submit
                    fields_to_update.forEach(field => {
                        frappe.meta.get_docfield('Work Order Operations Item', field, frm.doc.name).read_only = 0;
                        frappe.meta.get_docfield('Work Order Operations Item', field, frm.doc.name).allow_on_submit = 1;
                    });
                }
            });

            // Refresh the child table to apply changes
            frm.refresh_field('custom_subcontractors');
        }
    }
});


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
    },
   
});

