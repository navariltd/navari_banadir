
### Key Customizations and Enhancements

#### **1. Multicurrency Support**

Managing transactions across multiple currencies posed significant challenges. To address this:

-   We developed several reports tailored to identify and resolve multicurrency discrepancies.
-   Customizations were implemented across key doctypes such as **Journal Entry** and **Payment Entry** to ensure accurate currency conversion and consistency in financial records.
-   These adjustments provided clarity in transactions and streamlined operations for different companies using different currencies within same site.

#### **2. Purchase and Sales Invoice Linkage**

Enhancements were made to streamline workflows between purchase and sales invoices:

-   Items from purchase invoices can now be fetched into sales invoices, and vice versa.
-   The customization also tracks the remaining quantities to be fetched for future transactions, mirroring the functionality seen in stock entries for material transfers.
-   *These features are to be shipped to the app with plans for automated testing.*

#### **3 Shipping and Tracking Enhancements**

To facilitate tracking the shipping process:

-   New fields were added to the **Sales Invoice** doctype to monitor shipping progress.
-   Days are updated dynamically, and links to related purchase and sales invoices ensure comprehensive tracking.
-   This feature improves transparency in the logistics and fulfillment processes

#### **4. Sales Shipment Cost Doctype**

A new doctype, **Sales Shipment Cost**, was introduced:

-   This doctype manages the costs associated with sales invoices.
-   It updates the rates but ensures this action can only be performed while the sales invoice is in draft status, maintaining data integrity.

#### **5. Manufacturing and Subcontracting(Work In Progress)**

Customizations were made to enhance manufacturing workflows:
-   Support for both subcontracting and in-house manufacturing was implemented.
-   Subcontracting processes were enhanced to allow creating invoices for subcontracted work.


#### **6. Vehicle Management**

To improve tracking and documentation of vehicles:

-   The **Serial No** doctype was customized to include additional fields like **Engine Number**.
-   This allowed for more detailed tracking and reporting of vehicle-related data.

#### **7. Alternative UOM (Unit of Measurement)**
The need to manage quantities in alternative units like cartons and containers was a challenge:

-   Customizations were applied across various doctypes to accommodate these alternative UOMs.
-   This allowed users to enter and track quantities seamlessly in non-standard units, catering to industry-specific requirements.

#### **8. Invoice Numbering**

A requirement for unique invoice numbering per year and per company was implemented:

-   A customization ensures that each company's invoices follow a sequential numbering format, resetting annually.
-   This was crucial for internal tracking.

#### **9. Print Formats**

To cater to company-specific needs, we developed customized print formats:

-   **Footwear** and **Vehicle** companies received unique print formats tailored to their operational and branding requirements.

#### **10. Permissions and Access Restrictions**

To manage access control and restrictions effectively:

-   Duplicate doctypes were created to handle specific cases, such as allowing users to update dates without affecting core permissions.
-   This approach ensured strict adherence to access policies while allowing flexibility for certain user roles.


More Issues both epending and closed can be found [here](https://docs.google.com/spreadsheets/d/124VRwYit_65p1r9aLSUHhVUYZd_d0evd-U7O8koCH8U/edit?gid=1222425794#gid=1222425794)




#### License

agpl-3.0