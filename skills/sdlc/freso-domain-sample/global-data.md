# Global Test Data & Environment Configurations

This document stores all environment configurations, system URLs, and shared test accounts for the **Freso** project.

---

##  1. Staging Environment 

###  Admin Module
- **URL:** `http://gw-staging.digital.vn/freso/admin/login?returnUrl=product-management`
- **Credentials:**
  - **Phone Number:** `0988889999`
  - **Password:** `123456Aa@`

### Restaurant Module (Buyer)
- **Guest URL:** `http://gw-staging.digital.vn/freso/buyer/`
- **Login / Branch Selection URL:** `http://gw-staging.digital.vn/freso/buyer/chon-chi-nhanh`
- **Credentials:**
  - **Login Name:** `NHNGA2`
  - **Phone Number:** `0338952995`
  - **Password:** `123456Aa@`
  
###  Supplier Module (Seller / Farm)
- **URL:** `http://gw-staging.digital.vn/freso/seller/product`
- **Credentials:**
  - **Phone Number:** `0338952995`
  - **Password:** `123456Aa@`
  - **Supplier Code:** `PKA123`

---

## 2. Production Environment

### Restaurant Module (Buyer)
- **Guest URL:** `https://freso.vn/`
- **Product listing by category:** `https://freso.vn/danh-muc-san-pham/<category-slug>/<sub-slug>`
- **Credentials:** _(chưa có — hỏi user khi cần viết test authenticated trên production)_