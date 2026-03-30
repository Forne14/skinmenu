# GEMINI.md - Skinmenu Project Context

## Project Overview
Skinmenu is a specialized medical aesthetic clinic website built with **Django 5** and **Wagtail 7**. It uses **Tailwind CSS** for a modern, responsive frontend and is designed to handle complex treatment catalogs, blog content, and patient enquiries.

- **Main Technologies:** Python 3.12+, Django 5.2, Wagtail 7.2, Tailwind CSS 3.4, PostgreSQL (Production), Redis + RQ (Background Tasks).
- **Architecture:** Wagtail-driven CMS where core business data (Treatments, Options, Clinic Locations) is managed as Wagtail Snippets in the `catalog` app, and rendered via various Page types in the `pages` app.

## Core Applications
- **`pages/`**: Defines the Wagtail page tree. Key models: `HomePage`, `TreatmentsIndexPage`, `MenuSectionPage`, `TreatmentPage`, `BlogPage`, `AboutPage`, and `ContactPage`.
- **`catalog/`**: Business logic snippets. `Treatment` (top-level categories like Lasers, Fillers) and `TreatmentOption` (specific treatments like PicoGenesis). These are linked to `MenuSectionPage` and `TreatmentPage`.
- **`integrations/`**: Manages outbound events (e.g., newsletter signups) with an `OutboundEvent` model for tracking status, attempts, and failures.
- **`media_derivatives/`**: Handles specialized media processing, likely for video/image optimization.
- **`site_settings/`**: Global configuration (Social Media, Contact Info) and newsletter handling.

## Development & Operations

### Key Commands
- **Environment:** `source .venv/bin/activate`
- **Development Server:** `./scripts/run_dev.sh` (starts on `127.0.0.1:8001`, canonical URL `skinmenu.local:8001`).
- **CSS Build:** `npm run css:dev` (watch) or `npm run css:build` (production).
- **Database:** `python manage.py migrate`, `python manage.py database_snapshot`.
- **Tests:** `python manage.py test`.
- **Deployment:** `deploy.sh` (Production on Hetzner).

### Infrastructure
- **Database:** SQLite (local), PostgreSQL (production).
- **Caching/Queue:** Redis used for both Django cache and `django-rq` background workers.
- **Media:** Local file storage by default, supports S3-compatible storage via environment variables (`USE_S3_STORAGE`).
- **Monitoring:** Health endpoint at `/healthz/`.

## Coding & Contribution Guidelines
- **Python:** Adhere to **PEP 8**. Use descriptive names. Keep business logic in models or specialized services.
- **Wagtail:** 
    - Use `StreamField` for modular content sections.
    - Register reusable business entities as **Snippets**.
    - Organize templates under `templates/<app>/...`.
- **CSS:** Use Tailwind classes. Avoid writing custom CSS unless necessary (put in `src/styles/tailwind.css`).
- **Migrations:** Always include migrations for any model changes.
- **Testing:** Add tests for new features in the respective app's `tests.py`. Use `WagtailPageTestCase` for page-related logic.

## Deployment Policy
- Deployments are canonicalized via `deploy.sh`.
- Pre-release checks should be run using `./scripts/pre_release_check.sh`.
- Production deployments should only occur from the `main` branch.
