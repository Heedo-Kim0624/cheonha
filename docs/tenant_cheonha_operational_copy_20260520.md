# Tenant Cheonha Operational Copy - 2026-05-20

Goal: copy `cheonha` operational data into `tenant_cheonha` without enabling
`cheonha` tenant routing.

## Safety Changes

`copy_company_to_tenant_schema` was updated for staged production copy:

- Core company apply still refuses by default.
- `--allow-core-company` is required for `cheonha`.
- `--tables` allows exact table-level copy stages.
- `--batch-size` allows a future one-table batched copy for large tables.

## Backup

- `/home/ubuntu/cheonha/backups/pre_tenant_cheonha_light_operational_copy_20260520_065529.sql`

## Dry-Run Size

Full `cheonha` copy dry-run:

- planned copy tables: 25
- planned source rows: 4,892,986
- blocked tables: 1
- blocked source rows: 0

Largest remaining tables:

- `tracking_locationpoint`: 3,582,167 rows
- `tracking_blelog`: 1,257,699 rows

## Applied Copy Stages

An initial copy including `points` failed because `points_point_transactions`
references `tracking_trackingsession`, which had not been copied yet. The copy
ran inside one transaction and was rolled back; tenant target counts remained 0.

Successful stage 1:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps partner crew dispatch region settlement inquiry mobile territory \
  --apply --allow-core-company
```

Copied rows:

- `partner_partner`: 1
- `crew_yongcha_pay_group`: 8
- `crew_crewmember`: 270
- `dispatch_dispatchupload`: 199
- `dispatch_dispatchrecord`: 4,877
- `crew_overtimesetting`: 0
- `region_region`: 143
- `region_regionprice`: 113
- `region_pricehistory`: 0
- `settlement_settlement`: 68
- `settlement_settlementdetail`: 7,889
- `inquiry_settlementinquiry`: 10
- `inquiry_inquirymessage`: 30
- `mobile_app_users`: 14
- `mobile_passwords`: 14
- `territory_territory`: 111
- `territory_territoryboxrecord`: 0

Successful stage 2:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps tracking --tables tracking_trackingsession \
  --apply --allow-core-company
```

Copied rows:

- `tracking_trackingsession`: 212

Successful stage 3:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps points --apply --allow-core-company
```

Copied rows:

- `points_point_redemptions`: 0
- `points_point_transactions`: 173

Successful stage 4:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps tracking \
  --tables tracking_cameracapture tracking_cycle tracking_live_work_session_status \
  --apply --allow-core-company
```

Copied rows:

- `tracking_cameracapture`: 28,543
- `tracking_cycle`: 10,434
- `tracking_live_work_session_status`: 11

## Verification

Verification excluding large tracking child logs passed:

```bash
python manage.py verify_company_tenant_copy cheonha \
  --apps contenttypes auth accounts partner crew dispatch region settlement inquiry mobile points territory
```

Result:

- verified tables: 25
- errors: 0
- warnings: 0

Full verification with `--allow-incomplete` now has only two expected
mismatches:

- `tracking_locationpoint`
- `tracking_blelog`

All other checked tables matched.

Production smoke passed after copy:

- web root
- privacy page
- mobile app config
- teams
- dashboard KPI
- operation report
- operation report map
- operation report CSV
- settlements

## Current Routing State

- `new` remains routed to `tenant_new`.
- `cheonha` still has `routing_enabled=False`.
- live backend allow-list remains `TENANT_SCHEMA_COMPANIES=new`.

## Remaining Steps

## Large Tracking Copy

Before the large copy, plain SQL backups were compressed with `gzip -9` to
recover disk space. Backups were preserved as `.sql.gz` files.

Disk state:

- before compression: 285MB free, 99% used
- after compression: 3.2GB free, 79% used
- database size after copy: 1537MB

Backup before large copy:

- `/home/ubuntu/cheonha/backups/pre_tenant_cheonha_large_tracking_copy_20260520_072404.sql.gz`

Successful stage 5:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps tracking \
  --tables tracking_locationpoint \
  --batch-size 100000 \
  --resume \
  --apply \
  --allow-core-company
```

Copied rows:

- `tracking_locationpoint`: 3,582,167

Successful stage 6:

```bash
python manage.py copy_company_to_tenant_schema cheonha \
  --apps tracking \
  --tables tracking_blelog \
  --batch-size 100000 \
  --resume \
  --apply \
  --allow-core-company
```

Copied rows:

- `tracking_blelog`: 1,257,699

Full verification after the large copy:

```bash
python manage.py verify_company_tenant_copy cheonha
```

Result:

- verified tables: 31
- errors: 0
- warnings: 0
- `tracking_locationpoint`: source 3,582,167 / tenant 3,582,167
- `tracking_blelog`: source 1,257,699 / tenant 1,257,699

`CompanyTenant(cheonha)` was marked ready without enabling routing:

- `status=READY`
- `routing_enabled=False`

Production smoke passed after the full copy.

## Remaining Steps

Cutover completed. See `docs/tenant_cheonha_cutover_20260520.md`.
