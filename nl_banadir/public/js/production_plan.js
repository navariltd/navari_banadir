


frappe.ui.form.on("Production Plan", {
    refresh: function (frm) {
      frm.add_custom_button(
        __("Banadir Work Order"),
        function () {
          
  
          frappe.call({
            method: "nl_banadir.banadir_customization_reports.controllers.production_plan.make_work_order",
            args: {
              doc: frm.doc,
            },
            callback: function (response) {
              if (response.message) {
               frappe.msgprint("Created Work Orders");
              }
            },
          });
        },
        __("Create")
      );
    },
  });
  
  