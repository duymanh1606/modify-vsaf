# Knowledge Base: Product Category Service - E-Commerce Agricultural Platform

## 1. General Description
* **Service Name**: `getCatalogsWithProducts`
* **Purpose**: This service provides product catalogs grouped by categories for display on the platform. It supports two distinct operating modes depending on system configuration availability.
* **Operating Modes**:
  * **Admin Settings Mode (Mode 1)**: Triggered when explicit homepage layout settings exist and are enabled. It parses custom configuration parameters including banners and chosen product arrays.
  * **Default Mode (Mode 2)**: Fallback execution when specific layout configurations are missing or disabled. It retrieves active inventory items straight from the primary system database records.
* **Target Audience**: Client web and mobile storefront interfaces displaying catalog listings.

### Preconditions & Processing Controls
* **Request Parameters**:
  * `limit` (Integer): Maximum count of catalogs displayed per single page block (Default parameter: 10, Maximum value bounding: 20).
  * `pageNo` (Integer): The current target page position identifier requested by the client (Default parameter: 1).
  * `sortBy` (String): Target database attribute or field token used for sorting arrays (e.g., `displayOrder`, `name`).
  * `sortDirection` (String): Intended direction for order sorting algorithms, constrained to `ASC` or `DESC` tokens.
* **Header Configurations**:
  * `Authorization` (String, Optional): Bearer token containing cryptographically validated user session strings (`Bearer {token}`).
* **Post-conditions**: Returns a standardized JSON object tracking structural category hierarchies, nested product lists, image path resolution strings, and pagination statistics.

---

## 2. Interface and API Response Schemas
The service responds using a globally unified JSON format layout encapsulating response status codes, status messaging, and execution datasets.

### API Response Format (`200 OK`)
* **Standard Wrapper Properties**:
  * `code` (String): Operations status descriptor (e.g., `"00"` marks successful completion).
  * `message` (String): Explanatory status context (e.g., `"Success"`).
  * `data` (Object): High-level payload tracking result arrays and pagination metrics.

### Success Response Structural Fields
* **`results` (Array of Categories/Catalogs)**:
  * `id` (String): Unique database identifier for the specific main category.
  * `name` (String): Structural category title matching database naming rows.
  * `title` (String): Formatted title text designated for frontend presentation blocks.
  * `banner` (Object / Null): Tracks optional visual assets containing file name rows and resolved path strings (e.g., `"https://minio.example.com/banners/thuc-pham-tuoi-song.jpg"`). Null specified during Default Mode.
* **`products` (Nested Array within Catalog Objects)**:
  * `id` (String): Globally unique product identification index string.
  * `name` (String): Base product name string.
  * `logo` (Object): Structured file tracking data pointing to product image assets.
  * `title` (String): Complete marketing title text for product display cards.
  * `parentCategory` (String): Relational name mapping to parent category tiers.
  * `subCategory` (String): Relational name mapping to sub-classification tiers.
  * `unit` (String): Standardized unit of measurement code (e.g., `"kg"`, `"lít"`).
  * `skuProduct` (String): System generated standard product SKU number.
  * `defaultPrice` (Object): Tracks initial price bounding boundaries using `priceFrom` and `priceTo` string values.
  * `hover` (Array of Variant Objects): Tracks product variant properties accessible via interactive buyer hover motions, containing unique `variantId`, descriptive `variantName`, specific `skuVariant`, and isolated pricing parameters.
  * `isTagCart` (Boolean): System visibility flag denoting specific shopping cart state attributes.
* **Pagination Statistics Payload**:
  * `totalElements` (Integer): Global count of matching dataset records found across database tables.
  * `pageNo` (Integer): Confirmed page row returned.
  * `limit` (Integer): Confirmed record restriction value applied.

---

## 3. Core Business Logic and Algorithmic Flow

### Runtime Execution Workflow
1. The service intercepts incoming RESTful requests, examining pagination parameters and processing optional authentication header tokens.
2. System looks for homepage configuration parameters inside administrative lookup structures (`homeSettings`).
3. **Admin Settings Evaluation Path**:
   * System extracts the `featuredSellers` layout configuration area from configuration models.
   * If the area configuration is active and marked `display = true`, the application maps embedded `JsonNode` lists into structured `ProductCatalog` configuration arrays.
   * Extracts targeted product arrays via specific arrays of requested IDs (`productIds`) or falls back to standard category retrieval if explicit arrays are absent.
4. **Default Evaluation Path**:
   * Executed when custom configurations are entirely missing or marked `display = false`.
   * Directly interfaces with primary application databases via performance-optimized data queries to fetch valid category blocks containing active items.
5. System maps all relative media records, prepends structural root repository URLs, filters out empty categories containing zero available listings, and passes complete responses back to clients.

### Mapping Data Contract (`HomeSettingDto`)
* **`Area` Schema properties**:
  * `id` (String): Static component area flag (e.g., `"featuredSellers"`).
  * `name` (String): Display title corresponding to layout zones.
  * `display` (Boolean): Flag controlling whether the zone is rendered.
  * `orderNum` (Integer): Positional sorting rank guiding layout stacking structures.
  * `value` (List of JsonNodes): Deep configuration rules storing specific catalog configurations (`bannerUrl`, `productIds`).

---

## 4. Associated Database Entities and Technical Stack
* **Architecture Technology Components**: Core framework relies on native data execution models incorporating structured Common Table Expressions (`CTE`) and aggregate functions (`JSON_ARRAYAGG`). Relational entities include:
  * **`b2b_categories`**: Resolves structured parent-child class linkages and sorting orders.
  * **`b2b_products`**: Primary inventory master store containing pricing information and item descriptions.

---

## 5. Architectural Quality Matrix

### Non-Functional & Usability Constraints
* **Query Optimization Standards**: Mandatory use of native database routines paired with robust structural index layers applied directly on primary relational properties including `parent_id` and `category_id` references.
* **DTO Separation Design Patterns**: Strict structural isolation separating request handling, underlying internal mapping logic, response schemas, and external data contracts.
* **Usability Requirements**:
  * Clear RESTful API design models relying on clean parameterization conventions for all filtering and pagination operations.
  * Path Uniformity: Complete URLs are generated on the fly by resolving base repository endpoints (e.g., MinIO or Content Delivery Network parameters).
  * Inventory Resilience Rule: The service must automatically prune and filter empty category groups containing zero active product records.
  * Transparency Constraint: Dual mode execution paths must yield mathematically identical JSON payload wrapper schemas to ensure client-side structural predictability.
* **Observability Endpoints**:
  * Main Health Indicators: Accessible via standardized paths (`/actuator/health`).
  * System Readiness Indicators: Monitored cleanly via standard structural endpoints (`/actuator/ready`).