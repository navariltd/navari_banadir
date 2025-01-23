
frappe.ui.form.on("Purchase Order Item",{

    item_code: function(frm, cdt, cdn){
      
        var child = locals[cdt][cdn];
        if(child.custom_work_order){
        frappe.call({
            method: "nl_banadir.banadir_customization_reports.controllers.purchase_order.get_qty_from_first_work_order",
            args: {
                production_plan: frm.doc.custom_production_plan,
                work_order: child.custom_work_order,
            },
            callback: function(response){
                if(response.message){
                    frappe.model.set_value(cdt, cdn, "fg_item_qty", response.message.work_order_qty);
                    frappe.model.set_value(cdt, cdn, "fg_item", response.message.upper_stock_items);


                }
            }
        });
      }
    
    },
    custom_work_order: function(frm, cdt, cdn){
      
        var child = locals[cdt][cdn];
        frappe.call({
            method: "nl_banadir.banadir_customization_reports.controllers.purchase_order.get_qty_from_first_work_order",
            args: {
                production_plan: frm.doc.custom_production_plan,
                work_order: child.custom_work_order,
            },
            callback: function(response){
                if(response.message){
                    frappe.model.set_value(cdt, cdn, "fg_item_qty", response.message.work_order_qty);
                    frappe.model.set_value(cdt, cdn, "fg_item", response.message.upper_stock_items);


                }
            }
        });
      
    }
})


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
                  frappe.model.set_value(child.doctype, child.name, "fg_item_qty", item.fg_item_qty);
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
  
  