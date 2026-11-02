# Knowledge Base & System Overview: Agricultural Trading Platform Project

## 1. Document Control & Metadata
* **Project Name:** Agricultural Trading Platform Project
* **Document Title:** System Overview of Agricultural Trading Platform
* **Export Date:** May 20, 2026
* **Initial Document Creation Date:** May 05, 2025
* **Document Version:** 1.0 (Confluence Version 2)
* **Source Origin:** Product Development Department (TTSP)

---

## 2. General Description & Target Users
The system serves as an e-commerce platform facilitating agricultural trading with three main target user groups:
* **VDS (Viettel Digital Services):** System Administrators, Customer Service (CSKH), and Farm/Supplier Business Development Departments.
* **Farm / Supplier (NCC):** Entities distributing and selling agricultural products on the platform.
* **Restaurant (Res):** End-users purchasing agricultural products on the platform via dedicated applications or partner applications (such as Viettel Money).

---

## 3. Business Flows & Processes

### 3.1. Farm Onboarding Flow
1. **Catalog Definition:** Business staff initialize the required document profile catalog based on business logic.
2. **Profile Submission:** The Farm registers a business account and uploads the required registration profiles on the platform.
3. **Review & Contract Sign-off:** Business staff review the submitted profile against specific criteria and execute the contract with the supplier.
4. **Account Initialization:** Following contract execution, business staff upload or edit official documents to approve account creation. The system generates an admin account and sends credentials to the Farm.
5. **Profile Supplementation:** If the profile is rejected, the Farm must supplement the required documents.

### 3.2. Supplier Pricing & Promotion Management Flow
* **Product Catalog Declaration:** Operational staff declare the product catalog authorized for sale on the platform.
* **Product Listing:** Farms declare specific product details using a provided standard template.
* **Data Display:** The system displays active selling information based on the latest verified declaration from the Farm.
* **Promotion Management:** Farms configure promotional details and activate marketing campaigns. The system automatically calculates and applies these active promotions to matching customer orders.

### 3.3. Restaurant Purchasing & Order Flow
1. **Search & Discovery:** Restaurants search for required commodities and view search results provided by the system.
2. **Cart Management:** Restaurants add selected items to their shopping cart. Items can be added via the home screen, direct search, order history, recommendations, quick order codes, or file imports.
3. **Supplier Matching:** The system searches for active suppliers capable of fulfilling the designated order.
4. **Checkout & Payment:** The restaurant selects the preferred supplier, reviews the order summary, selects a funding source, and confirms payment.

### 3.4. Delivery & Fulfillment Flow
1. **Order Confirmation:** The supplier checks new incoming orders and chooses to accept or reject them.
2. **Preparation & Inventory Outflow:** The supplier prepares the items, confirms the warehouse inventory release, and prepares for shipment.
3. **Logistics Shipment:** The supplier or an integrated third-party logistics provider delivers the goods to the restaurant.
4. **Receipt Confirmation:** The restaurant verifies the delivered items and confirms successful delivery on the application.

### 3.5. Returns, Exchanges, and Refunds Flow
* **Exchange Process:** Restaurants can initiate an exchange request after successful receipt by attaching evidence. The Farm verifies the proof, accepts the request, schedules a new delivery, and the restaurant confirms receipt of the replaced goods. *(Note: Detailed exchange handling is excluded from Phase 1)*.
* **Return Process:** Restaurants submit a return request. Upon Farm approval, logistics are arranged to ship the items back to the supplier. Once the Farm confirms the inventory condition, the system initiates a refund to the restaurant's account. *(Note: Detailed return handling is excluded from Phase 1)*.

### 3.6. Financial Payout Flow (Phase 1)
1. **Revenue Aggregation:** The system captures and aggregates sales data belonging to each specific farm.
2. **Automated Payouts:** The system periodically executes automated payment orders to transfer funds directly to the registered bank account of the Farm.
3. **Reporting:** Farms can export financial reports as required.

---

## 4. Functional Capabilities Matrix by System Role

### 4.1. Farm / Supplier Module
* **Account & Staff Management:** View platform policies, register accounts, track registration status, manage authentication (login, password reset/change), modify store profile details, and manage employee accounts (add roles, assign permissions, lock, unlock, or delete staff).
* **Logistics & Financials:** Set up shipping methods, define default logistics options, link financial funding sources, prioritize payment methods, and remove financial linkages.
* **Product & Promotion Control:** View approved items, import product files in bulk, add individual items, edit product details, look up listings, delete products, configure promotional rules, and view promotion reports.
* **Order Processing:** Fetch order lists, filter/search orders, view detailed orders, preview or print invoices and delivery notes, trigger email updates, cancel orders, confirm pending delivery items, select shipping providers, and confirm successful fulfillment.

### 4.2. Restaurant Module
* **Profile & Branch Management:** Register, authenticate, update info, set up sub-branches, manage branch permissions, and control branch staff accounts (add, update, assign/revoke roles, lock, or delete).
* **Discovery & Shopping:** View public home layouts, fetch specific category trees, view highlighted/new products, explore supplier storefronts, manage favorites lists (add products/suppliers to favorites), handle shopping carts, and execute rapid orders via code entries or uploaded files.
* **Checkout & Reviews:** Compare suppliers, apply order vouchers, submit orders for internal approval, process payments, track live order statuses, print receipts, request digital tax invoices, rate suppliers, and manage conversations via chat.

### 4.3. VDS Admin & Customer Service (CSKH) Module
* **Profile & Account Auditing:** Manage business document categories, search onboarding profiles, update profile status flags, and provision administrator accounts for Farms and Restaurants.
* **Entity Information Tracking:** Manage and edit comprehensive master profiles for restaurants, branches, farms, and platform employees; manage system roles and explicit permissions.
* **Catalog & Verification:** Maintain global product categories, define platform-wide available items, and review and approve new custom items declared by suppliers.
* **Order Coordination & Dispute Handling:** Oversee order logs, chat with buyers and sellers, force order confirmations, track customer complaints, modify dispute information, and update resolution states.

### 4.4. Automated System Module
* **Order Engine Processes:** Calculate promotion rules, validate vouchers, calculate net order totals, and lock or unlock discount codes and vouchers during active checkout sessions.
* **Payment Clearing Processes:** Process payments, check for timeout transactions, handle failed transaction reversals, aggregate platform commission fees, clear net revenue for farms, and handle manual refund operations.
* **Data Aggregation Engine:** Perform background updates for supplier evaluations based on predefined scoring rules, and monitor automated payout transfers to suppliers.

---

## 5. System Components & Architecture
* **Frontend Touchpoints:** Farm Web/App (for sales, orders, and dashboard tracking) and Restaurant Web/App (for discovery and buying).
* **Portal Management:** Core Portal application used by Viettel administrators for daily platform operations.
* **Profile Subsystem:** Dedicated service handling catalog settings, profile persistence, and registration status states.
* **Account Subsystem:** Secure service governing authentication, account lifecycles, and role-based access control (RBAC).
* **Partner Subsystem:** Stores detailed master records of Farms (representatives, distribution boundaries, quality certificates like ISO/ATVSTP, evaluation scores) and Restaurants (operating sectors, branches, ratings).
* **Product Subsystem:** Manages active platform master data, pricing matrix configurations per target tier, and farm inventory listings.
* **Promotion Subsystem:** Governs active campaign discounts, voucher allocations, customer segmentation checks, and code state locks.
* **Purchase Subsystem:** Handles shopping cart states, order generation lifecycles, and historical purchase data.
* **Financial Subsystem:** Coordinates payment processing, refund handling, platform fee aggregation, and supplier payout automation.
* **External Integration Gateways:** Integrates with payment gateways (CTT) for transaction processing, core fee/commission policy rules, third-party payout systems, and specialized voucher allocation frameworks (M1 Subsystem).

---

## 6. Data Entities & Storage Definitions
* **PRODUCT (Product entity):** Contains `product_id` (Primary identifier), `name` (Product name), `description` (Detailed text), `category_id` (Associated category link), and `wallet_id` (Financial wallet reference code).
* **FARM (Supplier entity):** Contains `farm_id` (Primary identifier), `name` (Company name), `address` (Physical location), `category` (Business sector), and additional corporate documentation fields to be finalized.
* **import_white_list_promotion:** Operational database table utilized to verify if a given subscriber or customer ID is whitelisted for restrictive promotion campaigns.
* **cust_challenge:** Structural database entity used to initialize and map primary system onboarding challenges or initial configurations for customers.