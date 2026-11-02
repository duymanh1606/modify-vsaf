---
name: freso-domain-sample
description: Freso application domain knowledge — Business Scenario and Detailed Design. Use when writing test cases, writing automation test scripts, reviewing code or answering questions about how Freso works.
user-invocable: false
---

# Freso Domain Knowledge

> **Template note:** This skill follows the standard `<project>-domain` pattern.
> To create a domain skill for a new project:
> 1. Copy this folder and rename it `<your-project>-domain/`
> 2. Replace all paths below with `.claude/skills/<your-project>-domain/...`
> 3. Replace module sections (Farm, Restaurant) with your own modules
> 4. Update `global-data.md` with your environment URLs and credentials

## Overview
Freso is a full-stack Agritech B2B e-commerce platform that connects local suppliers (cooperatives, food companies) directly with restaurants. Users browse high-quality food ingredients, place automated orders, and manage supply chains. The platform facilitates a transparent, direct-to-market model, eliminating traditional intermediaries to ensure fresh sourcing and fair pricing.

## Detailed Knowledge (Sub-Files)

Load these based on what the current task needs:

### Global Overview
- **High-level system architecture & flow** → read `.claude/skills/freso-domain-sample/agricultural-marketplace-system-overview.md`
- **Global test data, environment configs & test accounts** → read `.claude/skills/freso-domain-sample/global-data.md`

### Farm Module
*If the task is related to farm product management, focus on this directory:* `.claude/skills/freso-domain-sample/farm/product-management/`
- **Product management business rules & test scenarios** → read `.claude/skills/freso-domain-sample/farm/product-management/business-scenario.md`
- **Product management technical specs, APIs & DB schema** → read `.claude/skills/freso-domain-sample/farm/product-management/detail-design.md`

### Restaurant Module
*If the task is related to the restaurant's home page and product listing, focus on this directory:* `.claude/skills/freso-domain-sample/restaurant/home-page/product-listing-page-by-category/`
- **Product listing page business logic & user flows** → read `.claude/skills/freso-domain-sample/restaurant/home-page/product-listing-page-by-category/business-scenario.md`
- **Product listing page technical specs, API design & DB schema** → read `.claude/skills/freso-domain-sample/restaurant/home-page/product-listing-page-by-category/detail-design.md`
