# Operations Runbook

## Preflight (local/CI)
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py test --settings=config.settings.test`
- `python manage.py audit_content_integrity`

## Deploy Verification
- `systemctl status skinmenu --no-pager`
- `systemctl status skinmenu-rqworker --no-pager`
- `python scripts/smoke_test.py`
- `tail -n 20 /home/deploy/apps/skinmenu/.deploy_log`

## Rollback
1. Read previous SHA from `/home/deploy/apps/skinmenu/.deploy_state` or `.deploy_log`.
2. Re-run deploy pinned to that SHA:
   - `DEPLOY_REF=<sha> /home/deploy/apps/skinmenu/deploy.sh`
3. Verify services and smoke test again.

## Failure Triage
- App service logs:
  - `journalctl -u skinmenu -n 120 --no-pager`
- Worker logs:
  - `journalctl -u skinmenu-rqworker -n 120 --no-pager`
- Nginx logs:
  - `sudo tail -n 120 /var/log/nginx/error.log`
