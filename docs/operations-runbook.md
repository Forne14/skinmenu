# Operations Runbook

## Preflight (local/CI)
- `./scripts/pre_release_check.sh`
- `python manage.py check`
- `python manage.py validate_integrations_config`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test --settings=config.settings.test`
- `python manage.py audit_content_integrity`
- `python manage.py audit_legacy_content`
- `./scripts/sqlite_backup_restore_drill.sh`

## Deploy Verification
- `systemctl status skinmenu --no-pager`
- `systemctl status skinmenu-rqworker --no-pager`
- `python scripts/smoke_test.py`
- `curl -fsS https://skin-menu.co.uk/healthz/`
- `tail -n 20 /home/deploy/apps/skinmenu/.deploy_log`

## Rollback
1. Read previous SHA from `/home/deploy/apps/skinmenu/.deploy_state` or `.deploy_log`.
2. Re-run deploy pinned to that SHA:
   - `DEPLOY_REF=<sha> /home/deploy/apps/skinmenu/deploy.sh`
3. Verify services and smoke test again.

## SQLite -> Postgres Rehearsal (No-Prod)
1. Set required env and validate prerequisites:
   - `export DJANGO_SECRET_KEY=...`
   - `export DATABASE_URL=postgresql://...`
   - `./scripts/pre_cutover_check.sh`
2. Run:
   - `./scripts/postgres_cutover_rehearsal.sh`
3. Review artifacts in `var/postgres-rehearsal/<timestamp>/`:
   - `baseline.json`
   - `candidate.json`
4. Confirm parity command passes:
   - `python manage.py compare_database_snapshots --left <baseline> --right <candidate>`
5. Treat the latest successful artifact directory as the migration gate record.
6. If parity fails, do not cut over. Fix data import/mapping first.

## Local Control Sequence (No-Prod)
- Single command gate for readiness assessment:
  - `DJANGO_SECRET_KEY=... DATABASE_URL=postgresql://... ./scripts/local_cutover_control_sequence.sh`
- Expected success markers:
  - `pre_cutover_check: ok`
  - `database_snapshots_match`
  - `local_cutover_control_sequence: ok`

## Failure Triage
- App service logs:
  - `journalctl -u skinmenu -n 120 --no-pager`
- Worker logs:
  - `journalctl -u skinmenu-rqworker -n 120 --no-pager`
- Lead-sync retries:
  - `python manage.py replay_outbound_events --status failed,pending --limit 50`
- Wagtail admin monitor:
  - `/admin/integrations/outbound-events/`
- Nginx logs:
  - `sudo tail -n 120 /var/log/nginx/error.log`
