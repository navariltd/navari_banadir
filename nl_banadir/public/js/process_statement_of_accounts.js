frappe.ui.form.on("Process Statement Of Accounts", {
  refresh(frm) {
    frm.add_custom_button(__("Custom Download"), function () {
      if (frm.is_dirty()) frappe.throw(__("Please save before proceeding."));
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
    });
  },
});
