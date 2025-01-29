frappe.ui.form.on('Payment Entry', {
    paid_from: function(frm) {
        if (frm.doc.paid_from) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Account',
                    name: frm.doc.paid_from
                },
                callback: function(response) {
                    let paid_from = response.message;
                    
                    if (paid_from && paid_from.account_type === 'Bank' && !frm.doc.reference_no) {
                        generate_unique_cheque_number(frm, paid_from.name);
                    }
                }
            });
        }
    }
});

function generate_unique_cheque_number(frm, account_name) {
    let reference_no = account_name.substring(0, 4).toUpperCase() + '-' + Math.random().toString(36).substring(2, 6).toUpperCase();
    
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Payment Entry',
            filters: { 'reference_no': reference_no },
            fields: ['reference_no']
        },
        callback: function(response) {
            if (response.message.length > 0) {
                generate_unique_cheque_number(frm);
            } else {
                frm.set_value('reference_no', reference_no);
                frm.set_value('reference_date', frappe.datetime.now_date());
            }
        }
    });
}
