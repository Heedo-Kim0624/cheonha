# Tenant Phase 6 Production Check - 2026-05-20

Goal: enable tenant routing only for the test company `new`, while keeping
`cheonha` on the existing public tables.

## Applied State

- `docker-compose.yml` passes tenant routing env vars into the backend.
- Production backend env:
  - `TENANT_SCHEMA_ROUTING_ENABLED=True`
  - `TENANT_SCHEMA_COMPANIES=new`
- `CompanyTenant(new)`:
  - `schema_name=tenant_new`
  - `status=READY`
  - `routing_enabled=True`
- `CompanyTenant(cheonha)` remains:
  - `status=PLANNED`
  - `routing_enabled=False`

## Backup

- `/home/ubuntu/cheonha/backups/pre_tenant_new_routing_on_20260520_063449.sql`

## Verification

- Existing production smoke passed after backend startup completed.
- Normal `new` login through `/api/v1/auth/login/` with `X-Company-App: new` passed.
- Browser UI check for `new` passed:
  - `/company/new/login` logged in as `admin12`.
  - Token was saved in local storage.
  - `/company/new/dispatch` loaded without API 4xx/5xx.
  - `/company/new/crew` loaded without API 4xx/5xx.
  - `/company/new/settlement` loaded without API 4xx/5xx.
  - `/company/new/operations` loaded without API 4xx/5xx.
- Request with `X-Company-App: new` and a tenant user token read:
  - teams: 1 row, `CO001`
  - dispatch uploads: 1 row
  - settlements: 1 row
  - operation report for `2026-05-19`: 1 row, 246 boxes, receive 246000, profit -152920
- Request with `X-Company-App: cheonha` still read public data:
  - teams: 3 rows
  - operation report for `2026-05-19`: 3 rows, 30075 boxes
- `python manage.py verify_company_tenant_copy new` passed:
  - verified tables: 31
  - errors: 0
  - warnings: 0
- Backend logs had no recent traceback, ERROR, internal server error, or 500 markers after both API and browser checks.

## Rollback

```bash
cd /home/ubuntu/cheonha
TENANT_SCHEMA_ROUTING_ENABLED=False TENANT_SCHEMA_COMPANIES= docker compose -f docker-compose.yml up -d --no-deps backend
docker compose -f docker-compose.yml run --rm --no-deps backend python manage.py shell -c "from apps.accounts.models import CompanyTenant; CompanyTenant.objects.filter(company_app__code='new').update(routing_enabled=False, status='PLANNED')"
```

## Remaining Steps

1. Copy `cheonha` operational data in a controlled maintenance window or write freeze.
2. Run public-vs-tenant comparison for `cheonha`.
3. Enable `cheonha` routing only after numbers match and rollback is ready.

See also: `docs/tenant_cheonha_schema_seed_20260520.md`.
