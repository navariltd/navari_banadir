frappe.ui.form.on("Process Statement Of Accounts", {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button(
        "Send Emails",
        function () {
          if (frm.is_dirty())
            frappe.throw(__("Please save before proceeding."));
          frappe.call({
            method:
              "nl_banadir.banadir_customization_reports.overrides.process_of_statements.send_emails",
            args: {
              document_name: frm.doc.name,
            },
            callback: function (r) {
              if (r && r.message) {
                frappe.show_alert({
                  message: __("Emails Queued"),
                  indicator: "blue",
                });
              } else {
                frappe.msgprint(__("No Records for these settings."));
              }
            },
          });
        },
        __("No Remarks")
      );
      frm.add_custom_button(
        __("Download"),
        function () {
          if (frm.is_dirty())
            frappe.throw(__("Please save before proceeding."));
          let url = frappe.urllib.get_full_url(
            "/api/method/nl_banadir.banadir_customization_reports.overrides.process_of_statements.download_statements?" +
              "document_name=" +
              encodeURIComponent(frm.doc.name)
          );
          $.ajax({
            url: url,
            type: "GET",
            success: function (result) {
              if (jQuery.isEmptyObject(result)) {
                frappe.msgprint(__("No Records for these settings."));
              } else {
                window.location = url;
              }
            },
          });
        },
        __("No Remarks")
      );
    }
  },
});
