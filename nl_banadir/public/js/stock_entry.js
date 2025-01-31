frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        let child_row = locals[cdt][cdn];  
        if (child_row.item_code) {
            frappe.call({
                method: 'nl_banadir.banadir_customization_reports.controllers.stock_entry.get_default_stock_uom',
                args: {
                    item_code: child_row.item_code
                },
                callback: function(r) {
                    if (!r.exc) {
                        frappe.model.set_value(cdt, cdn, 'uom', r.message);
                    }
                }
            });
        }
    }
});
