# Tenant Cheonha Schema Seed - 2026-05-20

Goal: prepare `tenant_cheonha` tables and reference seed data while keeping
all `cheonha` production requests on the existing public tables.

## Code Safety Change

The table creation and base seed commands still reject core companies by
default. A new explicit flag is required for the controlled cheonha preparation:

```bash
python manage.py create_tenant_tables cheonha --apply --allow-core-company
python manage.py seed_tenant_base_data cheonha --apply --allow-core-company
```

Without `--allow-core-company`, both apply commands keep refusing `cheonha`.

## Backups

- `/home/ubuntu/cheonha/backups/pre_tenant_cheonha_tables_apply_20260520_064738.sql`
- `/home/ubuntu/cheonha/backups/pre_tenant_cheonha_base_seed_apply_20260520_064908.sql`

## Applied State

- `tenant_cheonha` tables created.
- `CompanyTenant(cheonha)` remains:
  - `schema_name=tenant_cheonha`
  - `status=PLANNED`
  - `routing_enabled=False`
- Live backend routing allow-list remains:
  - `TENANT_SCHEMA_COMPANIES=new`
- Therefore, `cheonha` still reads the public schema.

## Table Creation

Dry-run result:

- existing tenant tables: 0
- concrete model tables: 33
- deferred nullable FK fields: 1
- auto-created M2M tables: 3
- data rows copied: 0
- routing changes: 0

Apply result:

- expected tables: 36
- actual tables: 36
- verification errors: 0
- verification warnings: 0

## Base Seed

Seeded reference rows:

- `django_content_type`: 33
- `auth_permission`: 132
- `accounts_user`: 2
- `accounts_team`: 3
- `mobile_app_message_config`: 1
- `points_point_items`: 4

Seeded users:

- `admin`
- `clever_admin`

Seeded teams:

- `A:A조`
- `X:X조`
- `R:R조`

Operational data was not copied in this step:

- crew
- dispatch
- settlement
- region
- inquiry
- tracking
- manpower
- territory
- mobile user/password data
- point transactions/redemptions

## Verification

- `python manage.py verify_tenant_tables cheonha` passed:
  - expected tables: 36
  - actual tables: 36
  - errors: 0
  - warnings: 0
- Production smoke passed after the seed:
  - web root
  - privacy page
  - mobile app config
  - teams
  - dashboard KPI
  - operation report
  - operation report map
  - operation report CSV
  - settlements
- Backend logs had no recent traceback, ERROR, internal server error, or 500 markers.

## Remaining Steps

1. Prepare the final `cheonha` routing cutover command and rollback command.
2. Enable `cheonha` routing only after confirming the maintenance timing.
3. Run production smoke and UI checks immediately after cutover.

See also: `docs/tenant_cheonha_operational_copy_20260520.md`.
