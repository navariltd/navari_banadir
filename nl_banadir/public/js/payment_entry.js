frappe.ui.form.on('Payment Entry', {
    mode_of_payment: function(frm) {
        if (frm.doc.mode_of_payment) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Mode of Payment',
                    name: frm.doc.mode_of_payment
                },
                callback: function(response) {
                    let mode_of_payment = response.message;
                    
                    if (mode_of_payment && mode_of_payment.type === 'Bank' && !frm.doc.reference_no) {
                        generate_unique_cheque_number(frm);
                    }
                }
            });
        }
    }
});

function generate_unique_cheque_number(frm) {
    let reference_no = 'CHEQ-' + Math.random().toString(36).substring(2, 10).toUpperCase();
    
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
