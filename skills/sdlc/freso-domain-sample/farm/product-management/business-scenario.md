# Knowledge Base: Product Management System - E-Commerce Agricultural Platform

## 1. General Description
* **Purpose**: This function allows Admin users to search, view, create, and update product information in the system.
* **Function Type**: Web application (Admin Portal).
* **Target Users**: System Administrators, Content Operations, and Product Managers.
* **Applicable Channel**: Agricultural E-commerce Platform, Backend Administration Console.

### Preconditions
* **User Authentication**: The user must be logged into an Admin account with valid session permissions for the product management module.
* **Data Integrity Requirement**: Any product added or updated must map to valid category identifiers existing within the system database (`b2b_categories`).

---

## 2. Interface and Screen Elements
* **Product Listing Grid**: Displays a structured data table containing comprehensive product details with standard layout pagination (limiting display to 20 items per page block).

### Control Elements Specification
* **Search and Filter Panel**:
  * **Product Name Input**: Text field allowing alphanumeric entry to query records by exact match or partial string matching against product titles.
  * **Category Dropdown**: A selectable selector fetching hierarchical listing data dynamically from the categories data table to filter rows.
  * **Status Filter Selector**: Dropdown component supporting values: "All", "On Sale", "Off Sale", and "Draft".
* **Data Action Buttons**:
  * **"Create Product" Button**: Positioned at the top action bar. Clicking initializes an empty product creation form layout.
  * **"Edit" Icon Link**: Embedded within each data row item. Triggers the update view with existing record elements pre-populated.
  * **"Change Status" Toggle Switch**: Inline control allowing direct modification of operational product visibility states.

---

## 3. Business Logic and Product Operations Workflow

### Product Creation and Validation Rules
1. Admin clicks the "Create Product" button. The system instantiates a blank record entry interface.
2. Required field input verification parameters:
   * **Product Title**: Mandatory text input. Duplicate check validation is executed against active database records to prevent exact title collision.
   * **SKU Generation**: System validates format parameters. Code must be unique across the global inventory.
   * **Base Unit of Measure**: Dropdown choice mapping to standardized platform measurements.
3. Pricing Framework Logic:
   * System requires entry of base cost and standard retail pricing structures.
   * Input handling blocks negative value insertions or non-numeric characters.

### Dynamic Inventory Visibility Rules
The administrative operational state of a product dictates frontend accessibility across buyer channels based on matrix criteria:
* **"Draft" Status**: Product schema is saved securely in the database but remains completely invisible to all client applications and buyer matching algorithms.
* **"On Sale" Status**: System evaluates supplier dependencies. If the product is assigned to an active, operating supplier and contains a matching active quotation row, it is dynamically pulled into frontend search indexes and category navigation grids.
* **"Off Sale" Status**: Immediate visibility withdrawal rule. The product record is instantly hidden from category lists and product catalogs on web and mobile client views, and any existing buyer card interactions for the product are disabled.

---

## 4. Associated Database Entities
* **`b2b_products` (Product Table)**: Stores core master data attributes including product identifier, unique SKU numbers, titles, measurement unit codes, base pricing, and operational visibility status flags.
* **`b2b_categories` (Category Reference Table)**: Maintained as a relational entity to map structured products to correct level-1 or level-2 industry divisions.
* **`b2b_product_images` (Media Asset Table)**: Handles binary file path references for validated high-resolution product media assets linked via foreign product keys.

---

## 5. System Test Cases Matrix

### Functional Test Scenarios
* **Form Field Validation Scope**: Verify system behavior when attempting to save data with empty mandatory text blocks. Ensure helpful formatting alerts trigger for validation failures.
* **Inventory Constraints Enforcement**: Input values containing negative numbers or strings exceeding bounding limits must be blocked at interface validation before database transmission.
* **Status Visibility Pipeline**: Check that toggle adjustments from "Draft" or "Off Sale" directly to "On Sale" safely update backend index tables and cleanly transition structural visibility flags.
* **Relational Reference Mapping**: Ensure creating a product mapped to a non-existent category identification string generates proper error handling instead of breaking structural application arrays.

### Non-Functional & Technical Test Scenarios
* **Query Latency Constraints**: Searching large product datasets using wildcards or complex filtering properties must process and return matching listing views in under 2.5 seconds.
* **Administrative Data Resiliency**: Valid database connection interruption must result in soft transaction rollbacks, preventing partial record creation or corrupted data structures.