# Product List Page by Category - Functional Specification & Test Cases

## 1. General Description

### Purpose
* Provides functionality for restaurants to view the product list according to each specific category.

### Function Type
* Web app.
* Mobile app.

### Target Users
* Restaurants and staff members in charge of importing goods.

### Applicable Channels
* E-commerce platform for agricultural products, web version.

### Screen Navigation Path
* Homepage =>
  1. Click on the category menu.
  2. Click on a specific category inside the "Product Catalog" section on the header.
  3. Click "See More" at the product areas divided by category.

### Preconditions
1. **Customer Types:**
   * Guest customers (Users who have not logged into an account).
   * Customers with a restaurant account (Logged in).
2. **Product Scope (Within Minimum Viable Product - MVP):**
   * **Case 1: Not logged in**
     * Products must be active and currently available for business.
     * Default sorting: Random display order of products.
   * **Case 2: Logged in**
     * Products must be active, available for business, and within the business scope of the Supplier.
     * Default sorting: Prioritize the display order of products based on geographic location, restaurant type, and business model.
3. **Product Status:**
   * Products must be in the "On Sale" status and belong to at least one valid/active quotation.

### Post-conditions
* The system correctly displays the product details of the desired category.

---

## 2. Screen Elements and UI Components

### General List Rules
* Displays the list of products matching the exact category selected from the homepage.
* The product list page includes pagination, where each page displays a maximum of 20 product items.

### UI Components Specification

| No. | Control Name | Control Type | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Breadcrumb | Breadcrumb | Home > Category Name | Displays when navigating from the homepage to the product list page by category. Clicking "Home" redirects back to the homepage. |
| 2 | Page Title | Label | Dynamic | Automatically pulled from the category name defined in the database. |
| 3 | Search Input | Input | "Search in catalog <Category Name>" | Allows users to enter keywords to search for products strictly within the current category. It does not include products from other categories. Placeholder category name is fetched from `b2b_product_categories`. |
| 4 | Category Tab Buttons | Tab Button | "All" | Displays tab buttons for level-2 sub-categories ("All" + "Sub-category X"). "All" displays all products in the main category, while "Sub-category X" filters products belonging exclusively to that group. |
| 5 | Pagination | Pagination | < 1 2 3 4 5 > | Displays when total items exceed 20. Each page contains 20 items. The left arrow icon `<` is inactive on page 1 and active on other pages. The right arrow icon `>` is inactive on the last page and active on others. |
| 6 | Product Item | Card | Product Card Type 1 | Displays product information block. Clicking on the card redirects the user to the Product Detail screen. |
| 7 | Description Quote | Label | "No results found for '<keyword>'" | Displays when no products match the search keyword inside the category. |
| 8 | Discover Button | Button | "Discover Now" | Displayed on the empty result view. Clicking this button redirects the user to the homepage. |

### Search Field Focus & Input Behaviors
* **Focus with no text:** When the cursor is placed into the search box (focused) and no data is entered yet, the system immediately displays the search history and search suggestions.
* **Typing text:** When the user starts typing data, the placeholder text, search history, and search suggestions disappear.
* **Empty history rule:** If there is no search history recorded, the entire history information block is hidden.
* **History storage limit:** Displays a maximum of 5 most recent keywords, sorted from newest to oldest at the top.
* **History capture scope:** Search history is saved from various screens including the header search box, new list pages, hot products, product list by category, supplier stores, search results page, and product detail page.
* **History clearing:** The system provides functionality to clear/delete history items.

---

## 3. Business Logic and Flow

### Sequence / Activity Diagram Overview
1. From the Homepage, the client selects a category from the product catalog menu, category menu, or "See More" links.
2. The Backend system identifies the selected category and checks for matching products.
3. The Frontend displays the product list page or an error/empty state notification if no data is found.

### Product Retrieval Criteria (Backend Logic)
To be eligible for display, a product must meet all the following conditions:
* Belongs to an active supplier who is currently operating.
* Product status is set to "On Sale" by both the Admin and the Supplier.
* Belongs to the exact category selected by the user.
* Associated with at least one quotation that remains currently valid.

### Sorting and Personalization Rules
* **Unauthenticated Users (Not Logged In):** Products are sorted randomly or alphabetically by product name.
* **Authenticated Users (Logged In):** Products are dynamically prioritized based on three main matching criteria:
  * **Location Matching (Condition A):** The restaurant's address (`b2b_cif.b2b_buyer_profiles.address_id`) must match the operational business zones of the supplier (`b2b_cif.b2b_seller_profiles.zones`), mapped down to the administrative level 2 (ward/commune to district/province). Location matching is strict; if a category contains no suppliers covering the restaurant's location, products are hidden.
  * **Restaurant Type Matching (Condition B):** Products that match the exact category profile or tier assignment of the restaurant.
  * **Business Model Matching (Condition C):** Products matching the specific type of business model configured for the restaurant.

#### Condition Combinations & Display Priority Matrix

| Combination | Conditions Met | Priority Level | Display Behavior |
| :---: | :--- | :--- | :--- |
| A + B + C | Location + Restaurant Type + Business Model | Highest Priority | Absolute match; prioritized at the top of the list. |
| A + B | Location + Restaurant Type | 2nd Priority | High matching level; close location and structural characteristics. |
| A + C | Location + Business Model | 3rd Priority | High matching level; close location and structural characteristics. |
| B + C | Restaurant Type + Business Model (Missing Location) | No Priority | Do not display products; hide the category block/area for this restaurant. |
| A | Location Only | 4th Priority | Partial match; displayed behind higher priority items. |
| B | Restaurant Type Only | No Priority | Do not display products; hide the category block/area. |
| C | Business Model Only | No Priority | Do not display products; hide the category block/area. |
| None | Zero conditions met | No Priority | Do not display products; hide the category block/area. |

---

## 4. Database Entities & Tables

### 1. Table: `b2b_categories`
* **Description:** Product Categories Table.
* **Purpose:** Determines and validates category definitions and hierarchies.
* **Operation Type:** Query (Read).

### 2. Table: `b2b_products`
* **Description:** Products Table.
* **Purpose:** Identifies and returns the list of products belonging to categories.
* **Operation Type:** Query (Read).

---
