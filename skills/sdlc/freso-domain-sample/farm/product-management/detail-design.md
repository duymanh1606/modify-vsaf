# Knowledge Base: Product Management System (Product Catalog Service)

This document contains a structured compilation of operational knowledge, system design schemas, database structures, business logic rules, and API specifications derived from the technical documentation of the Agricultural Trading Platform (Dự án Sàn nông sản - TKCT_Quản lý sản phẩm).

---

## 1. System Overview & Technology Stack
The Product Catalog Service acts as the centralized system for managing the product catalog hierarchy, product details, variants, inventory locations, and seller pricing matrix (quotes).

### Core Technology Stack
* **Framework:** Spring Boot
* **Language:** Java 21
* **Database:** MariaDB (Utilizing CQRS Pattern: Command repositories for writes, Query repositories for native optimized reads)
* **Persistence & Processing:** JPA / Hibernate, Native SQL Queries, Jackson ObjectMapper (JSON Processing)
* **Architecture & Utilities:** Lombok, Spring Transaction Management (`@Transactional`), Feign Client (for external integrations), Bean Validation

---

## 2. Database Schema and Technical Design
The system uses specialized database tables to manage products, categories, assets, and custom seller pricing parameters.

### 2.1 Core Entity Schema Tables

#### Table: `b2b_products` / `product`
Stores global attributes of agricultural products available on the platform.
* `id` (varchar(255), PRIMARY KEY): Unique product identifier.
* `name` (varchar(500), NOT NULL): Name of the product.
* `unit` (varchar(100), NULL): Measurement unit (e.g., kg, liter, box).
* `description` / `description` (text, NULL): Detailed description of the product.
* `product_sku` (varchar(100), NOT NULL, UNIQUE): Stock Keeping Unit string.
* `category_id` (varchar(255), NOT NULL): Associated sub-category identifier.
* `sub_category_id` (varchar(255), NULL): Nested category identifier level 2.
* `country_origin` (varchar(100), NULL): Manufacturing or growth origin country.
* `is_on_sale` (boolean, NOT NULL DEFAULT true): Operational status indicating if the product is open for sales.
* `deleted_at` / `is_delete` (datetime/boolean): Soft delete tracking indicator.
* `created_at` (datetime, DEFAULT CURRENT_TIMESTAMP): Creation timestamp.
* `updated_at` (datetime, NULL ON UPDATE CURRENT_TIMESTAMP): Last modification timestamp.

#### Table: `b2b_variants` / `variant`
Maintains individual configurations or product packaging styles.
* `id` (varchar(255), PRIMARY KEY): Variant identifier.
* `product_id` (varchar(255), NOT NULL, Foreign Key): Reference back to `b2b_products`.
* `specification` (varchar(500), NULL): Engineering or physical descriptor (e.g., Size, Color, 5kg Bag, 12-Bottle Box).
* `sku` (varchar(255), UNIQUE): Unique variant level SKU index.
* `deleted_at` (datetime, NULL): Timestamp for soft deletes.

#### Table: `b2b_product_categories` / `b2b_category`
Represents the structural master tree for product segmentation.
* `id` (varchar(255), PRIMARY KEY): Category node identifier.
* `name` (varchar(255), NOT NULL): Functional name of the category classification.
* `code` (varchar(100), NOT NULL, UNIQUE): Unique identifier code.
* `parent_id` (varchar(255), NULL): Self-referencing link to parent item (null for root element).
* `level` (int, NOT NULL): Hierarchy depth identifier (1: Parent, 2: Sub-category).

#### Table: `b2b_product_assets`
Manages multimedia bindings for products.
* `id` (varchar(255), PRIMARY KEY): Asset record token.
* `product_id` (varchar(255), NOT NULL): Targeted product object.
* `file_path` (varchar(500), NOT NULL): Storage location path or relative link.
* `asset_type` (varchar(50), NOT NULL): Enumeration value (e.g., IMAGE, VIDEO).
* `is_main` (boolean, NOT NULL DEFAULT false): Set to true for default display.

#### Table: `b2b_seller_prices` / `b2b_seller_price`
Contains the localized pricing definitions offered by individual suppliers.
* `id` (varchar(255), PRIMARY KEY): Row identifier.
* `variant_id` (varchar(255), NOT NULL, Foreign Key): Targeted component variant.
* `seller_id` (varchar(255), NOT NULL, Foreign Key): Merchant account ownership identifier.
* `stock_location_id` (varchar(255), NULL): Warehouse inventory mapping link.
* `price` (bigint, NOT NULL): Total numeric post-tax unit cost value (VND).
* `tax_rate` (double, NOT NULL): Active regulatory tax rate context percentage.
* `start_date` (datetime, NOT NULL): Activation timestamp for the quote validity.
* `end_date` (datetime, NULL): Expiration schedule limit (NULL means perpetual).
* `is_on_sale` (boolean, DEFAULT false): Supplier toggle for active marketplace presentation.
* `is_delete` (boolean, DEFAULT false): Soft deletion row flag.

#### Table: `b2b_seller_product_settings` / `b2b_seller_product_setting`
Custom profile switches for tailored item visibility per store.
* `id` (varchar(255), PRIMARY KEY): Settings instance token.
* `product_id` (varchar(255), NOT NULL): Associated base material product.
* `seller_id` (varchar(255), NOT NULL): Supplier key index.
* `is_hot` (boolean, NOT NULL DEFAULT false): High-visibility or featured item preference switch.

---

## 3. Core Business Logic & Process Flow Engine

### 3.1 Product Inquiry, Search, and Filtering Engine
* **Search Normalization:** The input text argument matching the product `name` parameter undergoes automatic Vietnamese accent removal (conversion of string elements to clean non-diacritic symbols) and precise programmatic sanitization to escape special query patterns (e.g., character components like `%` and `_` are converted to `\%` and `\_`) preventing structural SQL manipulation vectors.
* **SKU Search Conversion:** Search text entries are dynamically trimmed, stripped of spaces, and transformed to completely uppercase parameters to accurately intercept matched fields inside product or variant tables.
* **SQL Generation Optimization:** High-efficiency data retrieval is performed using programmatic native SQL aggregation expressions via single nested database transactions utilizing operations like `JSON_OBJECT` and `JSON_ARRAYAGG`. This converts database output arrays directly to unified JSON structured records, maximizing throughput by avoiding multi-fetch entity relational mapping cycles.
* **Asset CDN Resolution:** Relative storage entries located on server local folders are systematically appended with full qualified domain infrastructure identifiers (e.g., mapping a raw path like `/images/product.jpg` instantly into an absolute secure network handle `https://cdn.f2r.vn/images/product.jpg`).

### 3.2 Supplier Pricing Configuration and Quoting Engine
The system handles single updates, creations, and bulk imports via Excel spreadsheets through a unified algorithmic engine.

#### Multi-Tier Verification Blueprint
1.  **Identity Context Assessment:** Intercepts authentication headers (`Bearer {token}`) via a specialized user context component to verify that the active user contains the explicit type authorization code matching `SELLER`. If verification fails, it performs an immediate quiet exit returning null to minimize information disclosure vectors.
2.  **External Permission Audit:** Executes an internal remote Feign call to the external Customer Information File (CIF) Service endpoint (`/api/v1/sellers/{sellerId}`) to verify the supplier's runtime status. It also queries category assignments (`/api/v1/seller/settings`) to confirm the merchant is legally authorized to list products inside the specific `category_id`.
3.  **Product State Validation:** Verifies that the targeted global element inside `b2b_products` has soft delete flags set to null and is globally available for marketplace sales (`is_on_sale = true`).
4.  **Relational Scope Verification:** Confirms that all input `variant_id` values exist inside the master relational database and correspond to the parent `product_id` scope block.
5.  **Data Integrity Audit:** Validates that incoming tax rates and post-tax final item prices are not null and carry numeric coefficients greater than or equal to zero.
6.  **Temporal Schedule Checking:** Ensures the incoming activation schedule parameter `startDate` follows the exact validation profile structure `dd/MM/yyyy`. The effective date must represent a runtime point equivalent to or succeeding the system's current tracking timestamp (comparing calendar values, ignoring smaller clock time parameters).

#### Structural Data Mutation Design (Soft Delete History Tracking)
To preserve strict transaction history auditing trails, product price mutations follow an insert-only state strategy instead of in-place row mutations:
* The historically active price record row has its termination parameters updated (`is_delete = true`, `is_on_sale = false`, and `end_date = Current Timestamp - 1 Day`).
* A new price state row is generated (`is_delete = false`), configured with the newly supplied variables, and processed for entry storage.
* All associated pricing variations and accompanying visibility definitions (`b2b_seller_product_settings` mapping parameters like `is_hot`) are processed inside a single atomic execution boundary managed via `@Transactional`. Any runtime database exception triggers an immediate rollback to maintain consistent data states.

---

## 4. Bulk Processing Engine (Excel Import File Specifications)
The spreadsheet ingestion component provides rapid batch loading mechanisms for handling up to 10,000 distinct items per single upload session.

### 4.1 Spreadsheet File Criteria Limits
* **Maximum File Size Limit:** 5MB.
* **Maximum Records Capacity:** 10,000 spreadsheet rows per ingestion task.
* **Target Excel Document File Extension:** `.xlsx`.
* **Required Ingestion Target Worksheet Name:** `NCC nhập sản phẩm`.
* **Spreadsheet Parsing Row Boundary:** Header definition occurs strictly on Row index 1. Dynamic content collection sequences begin parsing sequentially from Row index 2.
* **Required Worksheet Structural Column Alignment:**
    1.  `Tên sản phẩm` (Product Name)
    2.  `Tên biến thể` (Variant Name)
    3.  `Giá trước thuế` (Pre-tax Base Cost Value)
    4.  `Thuế suất (%)` (Tax Rate Percentage Context)
    5.  `Giá sau thuế` (Post-tax Computed Cost Value)
    6.  `Tên danh mục` (Master Category Name Level 1)
    7.  `Tên danh mục con` (Nested Target Sub-category Name Level 2)

### 4.2 Ingestion Engine Execution Profiles
The system executes data import streams through two distinct operational runtime modes controlled by an input flag argument (`isExecute`):

* **Preview Simulation Mode (`isExecute = false`):** The engine processes file layout structures, validates business logic rules across worksheet lines, compiles row-by-row error logs, and immediately yields structured summary responses to the client. This allows suppliers to preview errors without modifying database storage tables.
* **Commit Storage Mode (`isExecute = true`):** The system passes records through the validation framework. If any entries violate validation criteria, the entire ingestion session is aborted, triggering an immediate database execution rollback to guarantee data consistency.

---

## 5. API Design & Specification Catalog

### 5.1 Public: Search and Filter Product Catalog Catalog
* **Endpoint:** `/api/v1/products`
* **HTTP Protocol Method:** `GET`
* **Query Filtering Arguments:**
    * `categoryIds` (List<String>, REQUIRED): Primary targeted operational categorization collection boundaries.
    * `name` (String, Optional): Free-form character input array matching target items.
    * `pageNo` (Integer, Optional, Default: 0): Target page offset.
    * `limit` (Integer, Optional, Default: 10): Item count per page.
    * `sortBy` (String, Optional, Default: "updated_at"): Relational target field name for output organization.
    * `sortDirection` (String, Optional, Default: "DESC"): Sorting order direction criteria ("ASC" or "DESC").
* **Successful Structural Output Profile (200 OK):** Yields a paginated envelope array object (`content`) listing complete identity details, embedded specs array configurations, unified nested sub/parent objects, and matching base CDN image location hyperlinks.

### 5.2 Public: Register New Supplier Price Metrics
* **Endpoint:** `/api/v1/sellers/products`
* **HTTP Protocol Method:** `POST`
* **Request Payload Format Blueprint (`application/json`):**
    * `isHot` (Boolean, REQUIRED): Strategic marketing status setting indicator.
    * `variants` (List, REQUIRED): Array collection block outlining target price details (`id`, `taxRate`, `price`, `isOnSale`, `startDate`).

### 5.3 Public: Modify Existing Supplier Pricing Specifications
* **Endpoint:** `/api/v1/seller/product-price`
* **HTTP Protocol Method:** `PUT`
* **Payload Structural Elements Configuration:** Identical parameters to the price registration template, but handles missing elements as optional values. It skips execution if no updates are detected relative to database tracking matrices.

### 5.4 Public: Bulk File Upload Spreadsheet Ingestion
* **Endpoint:** `/api/seller-prices/import`
* **HTTP Protocol Method:** `POST`
* **Request Payload Encoding Format:** `multipart/form-data`
* **Target Arguments:**
    * `file` (MultipartFile[], REQUIRED): Targeted physical spreadsheet item.
    * `isExecute` (Boolean, REQUIRED): Toggle configuration value determining whether to finalize database persistence or simulate execution results.

---

## 6. Service Dependencies Framework
The architecture uses specialized components to decouple core services from database storage operations.
* `Query Product Repository`: Handles highly optimized native SQL operations and converts structural query entries directly into database JSON strings.
* `Command Seller Price Repository`: Coordinates structural database insertions and batch storage persistence tasks.
* `CIF Service Client`: Manages declarative Feign integrations to query merchant configuration definitions and legal status properties from remote domains.
* `Base Util`: Houses reusable logical utilities for accent removal, text sequence sanitization, validation tasks, and checking text sequence lengths.

---

## 7. System Observability, Metrics & Telemetry
The core runtime engine provides comprehensive telemetry mapping variables exposed via spring actuator monitoring links (`/actuator/health` and `/actuator/ready`).

### System Performance Indicators (KPI Tracker)
* **Traffic Quantifier Matrix:** Tracks absolute concurrent search execution volumes, item registration volumes, and transaction volume trends across explicit timestamps.
* **Latency Diagnostic Metrics:** Registers accurate performance execution durations divided into native database search queries, remote CIF API transactions, object parsing tasks, and batch file ingestion times.
* **Validation Failures Tracking:** Monitors absolute operational error trends classified by specific exception error identities (e.g., monitoring illegal category access tokens `F2R_M058`, invalid price inputs `F2R_M065`, and duplicate quote errors `F2R_M059`).
* **Database Ingestion Analytics:** Monitors metrics like total processed sheet entries (`import_seller_prices_record_count`), tracking alerts if row metrics transcend 10,000 records, or if processing latency shifts past a 5000ms threshold limit.