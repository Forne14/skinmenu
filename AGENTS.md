# Repository Guidelines

## Project Structure & Module Organization
This repository is a Django 5 + Wagtail 7 project with Tailwind CSS.
- `config/`: settings (`config/settings/{base,dev,production,local}.py`), URLs, shared templates/static.
- `pages/`, `catalog/`, `search/`, `site_settings/`, `media_derivatives/`: app code (models, views, admin, migrations, tests).
- `src/styles/`: Tailwind input (`tailwind.css`, design tokens).
- `config/static/css/app.css`: compiled Tailwind output.
- `scripts/`: operational helpers (`local_deploy_check.sh`, `smoke_test.py`, rollback/sync).

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create/activate local Python environment.
- `pip install -r requirements.txt && npm install`: install backend and frontend dependencies.
- `python manage.py migrate`: apply database migrations.
- `python manage.py runserver`: run Django locally.
- `./scripts/run_dev.sh`: start local server on `127.0.0.1:8001` and use `skinmenu.local:8001` as canonical dev URL.
- `npm run css:dev`: watch and rebuild Tailwind with sourcemaps.
- `npm run css:build`: produce minified CSS for deploy.
- `python manage.py test`: run Django/Wagtail test suite.
- `python manage.py audit_legacy_content --fail-on-issues`: detect legacy/zombie page content debt.
- `python manage.py cleanup_legacy_content`: preview safe legacy cleanup (`--apply` to persist).
- `python manage.py validate_integrations_config`: fail fast on invalid integration env config.
- `./scripts/pre_release_check.sh`: run local release gate checks before any deploy.
- `./scripts/sqlite_backup_restore_drill.sh`: rehearse sqlite backup/restore integrity.
- `python manage.py database_snapshot --output var/baseline.json`: generate DB parity snapshot.
- `python manage.py compare_database_snapshots --left var/baseline.json --right var/candidate.json`: enforce parity.
- `./scripts/postgres_cutover_rehearsal.sh`: non-prod sqlite->postgres rehearsal workflow.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, descriptive class/function names.
- JavaScript/CSS: Prettier-driven (`singleQuote: true`, `semi: false`, `printWidth: 100`).
- Django/Wagtail: keep app boundaries clear; add migrations for model changes.
- Templates: organize under `templates/<app>/...`; use clear block/partial names (example: `pages/blocks/hero.html`).

## Testing Guidelines
- Put tests in each app (`pages/tests.py`, `site_settings/tests.py`, `media_derivatives/tests.py`).
- Name test methods `test_<behavior>` and group by feature in `TestCase`/`WagtailPageTestCase` classes.
- Run `python manage.py test <app_name>` before opening focused PRs.

## Commit & Pull Request Guidelines
- Follow existing history style: short imperative summaries (example: `add django-rq and django-redis`).
- Keep commits scoped to one change type (feature, fix, refactor, migration).
- PRs should include purpose, key module changes, migration/static impact, and screenshots for frontend/admin template updates.
- Link related issue/task IDs when available.

## Production Environment
- Server access: `ssh -C -i ~/.ssh/hetzner_ed25519 deploy@91.99.125.39`.
- App root: `/home/deploy/apps/skinmenu`; virtualenv: `/home/deploy/venvs/skinmenu`.
- Runtime env file: `/etc/skinmenu/skinmenu.env` (do not commit secrets; keep key names stable).
- Integration env keys: `DATABASE_URL` (optional, Postgres), `LEAD_SYNC_ENABLED`, `LEAD_SYNC_BACKEND`, `LEAD_SYNC_WEBHOOK_URL`, `BOOKING_BASE_URL`, `USE_S3_STORAGE` plus `AWS_*` S3 variables.
- `skinmenu.service` runs Gunicorn on unix socket `/run/skinmenu/skinmenu.sock`.
- `skinmenu-rqworker.service` runs `manage.py rqworker default --with-scheduler`.
- Nginx site `skinmenu` fronts the app; `/static/` maps to `.../staticfiles/`, `/media/` maps to `.../media/`.

## Deployment Flow
- Production policy: deploy only from `main` unless explicitly approved for hotfixes.
- Canonical deploy path is `deploy.sh`. It locks deploy, validates clean git state, fetches, and checks out target commit (detached `HEAD` is expected).
- It installs deps, runs `check --deploy`, checks migration drift, runs `migrate`, then `collectstatic --clear`.
- It restarts `skinmenu` and `skinmenu-rqworker`, runs `scripts/smoke_test.py`, and writes `.deploy_state`/`.deploy_log`.
- Verification commands: `systemctl status skinmenu --no-pager`, `systemctl status skinmenu-rqworker --no-pager`, `tail -n 20 /home/deploy/apps/skinmenu/.deploy_log`, `cat /home/deploy/apps/skinmenu/.deploy_state`.
- Health endpoint: `GET /healthz/` (checks DB + cache).
- Replay failed lead-sync events: `python manage.py replay_outbound_events --status failed,pending --limit 50`.
