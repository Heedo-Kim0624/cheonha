# Tenant Cheonha Cutover - 2026-05-20

Goal: route `cheonha` production requests to `tenant_cheonha` after full
public-vs-tenant verification passed.

## Pre-Cutover Verification

```bash
python manage.py verify_company_tenant_copy cheonha
```

Result:

- verified tables: 31
- errors: 0
- warnings: 0
- `tracking_locationpoint`: 3,582,167 source / 3,582,167 tenant
- `tracking_blelog`: 1,257,699 source / 1,257,699 tenant
- settlement aggregates matched
- dispatch aggregates matched

Pre-cutover state:

- `CompanyTenant(cheonha).status=READY`
- `CompanyTenant(cheonha).routing_enabled=False`
- disk free: 3.2GB
- DB size: 1537MB

## Backup

- `/home/ubuntu/cheonha/backups/pre_tenant_cheonha_routing_cutover_20260520_074316.sql.gz`

## Cutover Commands

```bash
cd /home/ubuntu/cheonha
docker compose -f docker-compose.yml run --rm --no-deps backend python manage.py shell <<'PY'
from django.utils import timezone
from apps.accounts.models import CompanyTenant
CompanyTenant.objects.filter(company_app__code='cheonha', status='READY').update(
    routing_enabled=True,
    last_verified_at=timezone.now(),
)
PY

TENANT_SCHEMA_ROUTING_ENABLED=True TENANT_SCHEMA_COMPANIES=new,cheonha \
  docker compose -f docker-compose.yml up -d --no-deps backend
```

Live backend settings after cutover:

- `TENANT_SCHEMA_ROUTING_ENABLED=True`
- `TENANT_SCHEMA_COMPANIES=['new', 'cheonha']`
- `CompanyTenant(cheonha).routing_enabled=True`
- `CompanyTenant(new).routing_enabled=True`

## Post-Cutover Verification

Production API smoke passed:

- web root
- privacy page
- mobile app config
- teams
- dashboard KPI
- operation report
- operation report map
- operation report CSV
- settlements

Browser UI check passed for `cheonha`:

- `/cheonha/login`
- `/cheonha/dispatch`
- `/cheonha/crew`
- `/cheonha/settlement`
- `/cheonha/operations`
- `/cheonha/tracking`

Log checks:

- no recent traceback, ERROR, internal server error, or 500 markers
- routing markers confirmed `company=cheonha schema=tenant_cheonha`

Disk state after cutover:

- free: 3.0GB
- used: 80%
- DB size: 1537MB

## Rollback

Use this if `cheonha` tenant routing causes a production issue:

```bash
cd /home/ubuntu/cheonha

TENANT_SCHEMA_ROUTING_ENABLED=True TENANT_SCHEMA_COMPANIES=new \
  docker compose -f docker-compose.yml up -d --no-deps backend

docker compose -f docker-compose.yml run --rm --no-deps backend python manage.py shell <<'PY'
from apps.accounts.models import CompanyTenant
CompanyTenant.objects.filter(company_app__code='cheonha').update(routing_enabled=False)
PY
```

This rollback returns `cheonha` traffic to the public schema while keeping `new`
routed to `tenant_new`.
