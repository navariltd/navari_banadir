frappe.ui.form.on("Purchase Order", {
    refresh: function (frm) {
      frm.add_custom_button(
        __("Production Plan"),
        function () {
          if (!frm.doc.custom_production_plan) {
            frappe.msgprint(__("Please select a Production Plan first."));
            return;
          }
  
          frappe.call({
            method: "nl_banadir.banadir_customization_reports.controllers.purchase_order.get_items_from_production_plan",
            args: {
              production_plan: frm.doc.custom_production_plan,
            },
            callback: function (response) {
              if (response.message) {
                const items = response.message;
                frm.clear_table("items");
                items.forEach((item) => {
                  const child = frm.add_child("items"); // Replace "items" with your child table fieldname
                  frappe.model.set_value(child.doctype, child.name, "item_code", "JOB WORK CHARGES");
                  frappe.model.set_value(child.doctype, child.name, "fg_item", item.item_code);
                  frappe.model.set_value(child.doctype, child.name, "fg_item_qty", 1);
                  frappe.model.set_value(child.doctype, child.name, "qty", item.quantity);
                  frappe.model.set_value(child.doctype, child.name, "custom_work_order", item.work_order);
                  frappe.model.set_value(child.doctype, child.name, "uom", "Pair");
                  frappe.model.set_value(child.doctype, child.name, "production_plan", frm.doc.custom_production_plan);
                });
  
                frm.refresh_field("items");
                frappe.msgprint(__("Items added from Production Plan."));
              }
            },
          });
        },
        __("Get Items From")
      );
    },
  });
  