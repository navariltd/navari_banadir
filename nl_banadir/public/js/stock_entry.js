frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
        let child_row = locals[cdt][cdn];  // Get the current child row
        if (child_row.item_code) {
            // Call the server-side function to get the default UOM
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
