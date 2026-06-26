from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.models import CompanyTenant


BASE_SEED_TABLES = (
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "accounts_user",
    "accounts_team",
    "accounts_user_groups",
    "accounts_user_user_permissions",
    "mobile_app_message_config",
    "points_point_items",
)


TEAM_IDS = "SELECT id FROM public.accounts_team WHERE company_app = %(company_code)s"
USER_IDS = """
    SELECT u.id
    FROM public.accounts_user u
    LEFT JOIN public.accounts_companyapp ca ON ca.code = %(company_code)s
    WHERE u.company_app = %(company_code)s OR u.id = ca.representative_user_id
"""
CREW_IDS = f"""
    SELECT c.id
    FROM public.crew_crewmember c
    WHERE c.team_id IN ({TEAM_IDS})
"""
UPLOAD_IDS = f"""
    SELECT du.id
    FROM public.dispatch_dispatchupload du
    WHERE du.team_id IN ({TEAM_IDS})
"""
SETTLEMENT_IDS = f"""
    SELECT s.id
    FROM public.settlement_settlement s
    WHERE s.team_id IN ({TEAM_IDS})
"""
REGION_IDS = f"""
    SELECT r.id
    FROM public.region_region r
    WHERE r.team_id IN ({TEAM_IDS})
"""
REGION_PRICE_IDS = f"""
    SELECT rp.id
    FROM public.region_regionprice rp
    WHERE rp.region_id IN ({REGION_IDS})
"""
INQUIRY_IDS = f"""
    SELECT i.id
    FROM public.inquiry_settlementinquiry i
    WHERE i.team_id IN ({TEAM_IDS})
       OR i.crew_member_id IN ({CREW_IDS})
"""
TRACKING_SESSION_IDS = f"""
    SELECT ts.id
    FROM public.tracking_trackingsession ts
    WHERE ts.crew_member_id IN ({CREW_IDS})
"""
MOBILE_USER_IDS = f"""
    SELECT mu.id
    FROM public.mobile_app_users mu
    WHERE mu.crew_member_id IN ({CREW_IDS})
"""
TERRITORY_IDS = f"""
    SELECT tt.id
    FROM public.territory_territory tt
    WHERE tt.team_id IN ({TEAM_IDS})
"""

ESSENTIAL_BASE_SEED_TABLES = (
    "django_content_type",
    "auth_permission",
    "accounts_user",
    "accounts_team",
    "mobile_app_message_config",
    "points_point_items",
)

USER_FK_COLUMNS = {
    "approved_by_id",
    "changed_by_id",
    "confirmed_by_id",
    "created_by_id",
    "updated_by_id",
    "uploaded_by_id",
}


@dataclass(frozen=True)
class CopyPolicy:
    app_label: str
    model_label: str
    table_name: str
    where_sql: str
    note: str = ""


@dataclass(frozen=True)
class BlockedPolicy:
    app_label: str
    model_label: str
    table_name: str
    reason: str


COPY_POLICIES = (
    CopyPolicy(
        "partner",
        "Partner",
        "partner_partner",
        f"id IN (SELECT DISTINCT c.partner_id FROM public.crew_crewmember c WHERE c.partner_id IS NOT NULL AND c.id IN ({CREW_IDS}))",
        "Only partners referenced by selected company crew members.",
    ),
    CopyPolicy(
        "crew",
        "YongchaPayGroup",
        "crew_yongcha_pay_group",
        "company_app = %(company_code)s",
    ),
    CopyPolicy(
        "crew",
        "CrewMember",
        "crew_crewmember",
        f"team_id IN ({TEAM_IDS})",
    ),
    CopyPolicy(
        "dispatch",
        "DispatchUpload",
        "dispatch_dispatchupload",
        f"team_id IN ({TEAM_IDS})",
    ),
    CopyPolicy(
        "dispatch",
        "DispatchRecord",
        "dispatch_dispatchrecord",
        f"upload_id IN ({UPLOAD_IDS})",
    ),
    CopyPolicy(
        "crew",
        "OvertimeSetting",
        "crew_overtimesetting",
        f"dispatch_upload_id IN ({UPLOAD_IDS})",
    ),
    CopyPolicy(
        "region",
        "Region",
        "region_region",
        f"team_id IN ({TEAM_IDS})",
    ),
    CopyPolicy(
        "region",
        "RegionPrice",
        "region_regionprice",
        f"region_id IN ({REGION_IDS})",
    ),
    CopyPolicy(
        "region",
        "PriceHistory",
        "region_pricehistory",
        f"region_price_id IN ({REGION_PRICE_IDS})",
    ),
    CopyPolicy(
        "settlement",
        "Settlement",
        "settlement_settlement",
        f"team_id IN ({TEAM_IDS})",
    ),
    CopyPolicy(
        "settlement",
        "SettlementDetail",
        "settlement_settlementdetail",
        f"settlement_id IN ({SETTLEMENT_IDS})",
    ),
    CopyPolicy(
        "inquiry",
        "SettlementInquiry",
        "inquiry_settlementinquiry",
        f"team_id IN ({TEAM_IDS}) OR (team_id IS NULL AND crew_member_id IN ({CREW_IDS}))",
    ),
    CopyPolicy(
        "inquiry",
        "InquiryMessage",
        "inquiry_inquirymessage",
        f"inquiry_id IN ({INQUIRY_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "TrackingSession",
        "tracking_trackingsession",
        f"crew_member_id IN ({CREW_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "LocationPoint",
        "tracking_locationpoint",
        f"session_id IN ({TRACKING_SESSION_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "BleLog",
        "tracking_blelog",
        f"session_id IN ({TRACKING_SESSION_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "CameraCapture",
        "tracking_cameracapture",
        f"session_id IN ({TRACKING_SESSION_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "Cycle",
        "tracking_cycle",
        f"session_id IN ({TRACKING_SESSION_IDS})",
    ),
    CopyPolicy(
        "tracking",
        "LiveWorkSessionStatus",
        "tracking_live_work_session_status",
        f"crew_member_id IN ({CREW_IDS})",
    ),
    CopyPolicy(
        "mobile",
        "MobileAppUser",
        "mobile_app_users",
        f"crew_member_id IN ({CREW_IDS})",
    ),
    CopyPolicy(
        "mobile",
        "MobilePassword",
        "mobile_passwords",
        f"mobile_user_id IN ({MOBILE_USER_IDS})",
    ),
    CopyPolicy(
        "points",
        "PointRedemption",
        "points_point_redemptions",
        f"crew_member_id IN ({CREW_IDS})",
    ),
    CopyPolicy(
        "points",
        "PointTransaction",
        "points_point_transactions",
        f"crew_member_id IN ({CREW_IDS})",
    ),
    CopyPolicy(
        "territory",
        "Territory",
        "territory_territory",
        f"team_id IN ({TEAM_IDS})",
        "Territories without team_id are intentionally excluded until a company policy is reviewed.",
    ),
    CopyPolicy(
        "territory",
        "TerritoryBoxRecord",
        "territory_territoryboxrecord",
        f"territory_id IN ({TERRITORY_IDS})",
    ),
)

BLOCKED_POLICIES = (
    BlockedPolicy(
        "manpower",
        "Manpower",
        "manpower_manpower",
        "No company/team/crew foreign key exists. Copying all rows could mix company data.",
    ),
)


class Command(BaseCommand):
    help = (
        "Plan or apply company-to-tenant operational data copy. Apply mode is "
        "restricted to non-core tenants with seeded base rows and empty target "
        "operational tables."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to include in the copy plan.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Copy operational rows into a prepared non-core tenant schema. "
                "Routing remains disabled."
            ),
        )
        parser.add_argument(
            "--allow-core-company",
            action="store_true",
            help=(
                "Allow apply for a core company after dry-run review and backup. "
                "Without this flag, core companies are still refused."
            ),
        )
        parser.add_argument(
            "--tables",
            nargs="+",
            default=[],
            help=(
                "Optional exact tenant table names to copy, for staged copy runs. "
                "Example: --tables tracking_locationpoint"
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=0,
            help=(
                "Copy one selected table in batches of this many source IDs. "
                "Requires --tables with exactly one table."
            ),
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help=(
                "Resume a batched one-table copy from the tenant table's current "
                "maximum ID. Requires --batch-size."
            ),
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")
        if connection.vendor != "postgresql":
            raise CommandError("Tenant copy planning requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(
            dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip())
        )
        selected_tables = tuple(
            dict.fromkeys(str(table).strip() for table in options["tables"] if str(table).strip())
        )
        self._validate_selected_tables(selected_tables)
        batch_size = int(options["batch_size"] or 0)
        if batch_size < 0:
            raise CommandError("--batch-size must be 0 or a positive integer.")
        resume = bool(options["resume"])
        if resume and not batch_size:
            raise CommandError("--resume requires --batch-size.")
        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        params = {"company_code": company_code}
        base_seed_rows = self._base_seed_rows(schema_name)
        copy_rows = self._copy_rows(schema_name, selected_apps, params, selected_tables)
        blocked_rows = self._blocked_rows(schema_name, selected_apps, selected_tables)
        summary = self._summary(copy_rows, blocked_rows)

        mode = "APPLY" if options["apply"] else "dry-run"
        self.stdout.write(f"Company tenant copy {mode}")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        if selected_tables:
            self.stdout.write(f"  selected_tables: {', '.join(selected_tables)}")
        if batch_size:
            self.stdout.write(f"  batch_size: {batch_size}")
        if resume:
            self.stdout.write("  resume: True")
        self.stdout.write("")

        self.stdout.write("Summary")
        self.stdout.write(f"  planned_copy_tables: {summary['copy_tables']}")
        self.stdout.write(f"  planned_source_rows: {summary['source_rows']}")
        self.stdout.write(f"  target_rows_already_present: {summary['target_rows']}")
        self.stdout.write(f"  missing_target_tables: {summary['missing_targets']}")
        self.stdout.write(f"  blocked_tables: {summary['blocked_tables']}")
        self.stdout.write("")

        self.stdout.write("Base seed tables already handled by seed_tenant_base_data")
        for row in base_seed_rows:
            target = "missing target" if row["target_count"] is None else row["target_count"]
            source = "missing source" if row["source_count"] is None else row["source_count"]
            self.stdout.write(f"  - {row['table']}: public={source}, tenant={target}")

        self.stdout.write("")
        self.stdout.write("Planned operational copy rows")
        for row in copy_rows:
            target = "missing target" if row["target_count"] is None else row["target_count"]
            source = "missing source" if row["source_count"] is None else row["source_count"]
            self.stdout.write(
                f"  - {row['app']}.{row['model']} -> {row['table']}: "
                f"source={source}, tenant_existing={target}"
            )
            if row["note"]:
                self.stdout.write(f"    note: {row['note']}")

        if blocked_rows:
            self.stdout.write("")
            self.stdout.write("Blocked copy policies")
            for row in blocked_rows:
                target = "missing target" if row["target_count"] is None else row["target_count"]
                source = "missing source" if row["source_count"] is None else row["source_count"]
                self.stdout.write(
                    f"  - {row['app']}.{row['model']} -> {row['table']}: "
                    f"source={source}, tenant_existing={target}"
                )
                self.stdout.write(f"    reason: {row['reason']}")

        warnings = self._warnings(copy_rows, blocked_rows, tenant)
        if warnings:
            self.stdout.write("")
            self.stdout.write("Warnings")
            for message in warnings:
                self.stdout.write(f"  - {message}")

        self.stdout.write("")
        if options["apply"]:
            result = self._apply_copy(
                tenant=tenant,
                schema_name=schema_name,
                base_seed_rows=base_seed_rows,
                copy_rows=copy_rows,
                blocked_rows=blocked_rows,
                params=params,
                allow_core_company=options["allow_core_company"],
                batch_size=batch_size,
                resume=resume,
            )
            self.stdout.write("")
            self.stdout.write("Applied operational rows")
            for row in result:
                self.stdout.write(f"  - {row['table']}: {row['copied']}")
            self.stdout.write("")
            self.stdout.write("Safety notes")
            self.stdout.write("  - Base seed tables were not modified.")
            self.stdout.write("  - CompanyTenant.routing_enabled remains False.")
            self.stdout.write("  - No public schema data was changed.")
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Company operational rows copied to tenant schema."))
            return

        self.stdout.write("Safety notes")
        self.stdout.write("  - DRY RUN ONLY: no database changes were made.")
        self.stdout.write("  - No data was inserted, updated, or deleted.")
        self.stdout.write("  - CompanyTenant.routing_enabled remains unchanged.")
        self.stdout.write("  - Use --apply only after reviewing the plan and taking a backup.")

    def _get_tenant(self, company_code):
        try:
            return CompanyTenant.objects.select_related("company_app").get(
                company_app__code=company_code
            )
        except CompanyTenant.DoesNotExist as exc:
            raise CommandError(
                f"No CompanyTenant registry row exists for company_code={company_code!r}."
            ) from exc

    def _validate_schema_name(self, schema_name):
        value = str(schema_name or "").strip().lower()
        if not value.startswith("tenant_") or not SCHEMA_NAME_RE.match(value):
            raise CommandError(f"Unsafe tenant schema_name={value!r}.")
        return value

    def _schema_exists(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name],
            )
            return cursor.fetchone() is not None

    def _table_exists(self, schema_name, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,
                [schema_name, table_name],
            )
            return cursor.fetchone() is not None

    def _base_seed_rows(self, schema_name):
        rows = []
        for table_name in BASE_SEED_TABLES:
            rows.append(
                {
                    "table": table_name,
                    "source_count": self._table_count("public", table_name),
                    "target_count": self._table_count(schema_name, table_name),
                }
            )
        return rows

    def _validate_selected_tables(self, selected_tables):
        if not selected_tables:
            return
        known_tables = {policy.table_name for policy in COPY_POLICIES}
        known_tables.update(policy.table_name for policy in BLOCKED_POLICIES)
        unknown_tables = sorted(set(selected_tables) - known_tables)
        if unknown_tables:
            raise CommandError(
                "Unknown --tables value(s): " + ", ".join(unknown_tables)
            )

    def _copy_rows(self, schema_name, selected_apps, params, selected_tables=()):
        selected_table_set = set(selected_tables)
        rows = []
        for policy in COPY_POLICIES:
            if policy.app_label not in selected_apps:
                continue
            if selected_table_set and policy.table_name not in selected_table_set:
                continue
            rows.append(
                {
                    "app": policy.app_label,
                    "model": policy.model_label,
                    "table": policy.table_name,
                    "source_count": self._filtered_count(
                        "public",
                        policy.table_name,
                        policy.where_sql,
                        params,
                    ),
                    "target_count": self._table_count(schema_name, policy.table_name),
                    "note": policy.note,
                }
            )
        return rows

    def _blocked_rows(self, schema_name, selected_apps, selected_tables=()):
        selected_table_set = set(selected_tables)
        rows = []
        for policy in BLOCKED_POLICIES:
            if policy.app_label not in selected_apps:
                continue
            if selected_table_set and policy.table_name not in selected_table_set:
                continue
            rows.append(
                {
                    "app": policy.app_label,
                    "model": policy.model_label,
                    "table": policy.table_name,
                    "source_count": self._table_count("public", policy.table_name),
                    "target_count": self._table_count(schema_name, policy.table_name),
                    "reason": policy.reason,
                }
            )
        return rows

    def _summary(self, copy_rows, blocked_rows):
        return {
            "copy_tables": len(copy_rows),
            "source_rows": sum(row["source_count"] or 0 for row in copy_rows),
            "target_rows": sum(row["target_count"] or 0 for row in copy_rows),
            "missing_targets": sum(1 for row in copy_rows if row["target_count"] is None),
            "blocked_tables": len(blocked_rows),
        }

    def _warnings(self, copy_rows, blocked_rows, tenant):
        warnings = []
        missing_targets = [
            row["table"]
            for row in copy_rows
            if row["source_count"] and row["target_count"] is None
        ]
        if missing_targets:
            warnings.append(
                "source rows exist but tenant target tables are missing: "
                + ", ".join(missing_targets)
            )

        populated_targets = [
            f"{row['table']}={row['target_count']}"
            for row in copy_rows
            if row["target_count"]
        ]
        if populated_targets:
            warnings.append(
                "tenant operational tables already contain rows: "
                + ", ".join(populated_targets)
            )

        nonzero_blocked = [
            f"{row['table']}={row['source_count']}"
            for row in blocked_rows
            if row["source_count"]
        ]
        if nonzero_blocked:
            warnings.append(
                "blocked tables have source rows and need an explicit policy before apply: "
                + ", ".join(nonzero_blocked)
            )

        if tenant.routing_enabled:
            warnings.append("routing is already enabled; do not run public-to-tenant copy blindly.")
        return warnings

    def _apply_copy(
        self,
        tenant,
        schema_name,
        base_seed_rows,
        copy_rows,
        blocked_rows,
        params,
        allow_core_company=False,
        batch_size=0,
        resume=False,
    ):
        self._validate_apply_allowed(
            tenant=tenant,
            base_seed_rows=base_seed_rows,
            copy_rows=copy_rows,
            blocked_rows=blocked_rows,
            allow_core_company=allow_core_company,
            allow_existing_targets=bool(batch_size and resume),
        )

        if batch_size:
            if len(copy_rows) != 1:
                raise CommandError("--batch-size requires --tables with exactly one copy table.")
            row = copy_rows[0]
            policy = self._policy_for_copy_row(row)
            with connection.cursor() as cursor:
                start_after_id = (
                    self._validate_batch_resume_target(cursor, schema_name, policy, params)
                    if resume
                    else 0
                )
                if not resume:
                    self._assert_operational_targets_still_empty(cursor, schema_name, copy_rows)
            copied = self._copy_policy_rows_batched(
                schema_name=schema_name,
                policy=policy,
                params=params,
                batch_size=batch_size,
                start_after_id=start_after_id,
            )
            final_target_count = self._table_count(schema_name, policy.table_name)
            if final_target_count != row["source_count"]:
                raise CommandError(
                    f"Final count mismatch for {policy.table_name}: "
                    f"source={row['source_count']} tenant={final_target_count} "
                    f"newly_copied={copied}"
                )
            with transaction.atomic():
                with connection.cursor() as cursor:
                    self._reset_sequences(cursor, schema_name, [row["table"]])
            return [{"table": policy.table_name, "copied": copied}]

        applied = []
        with transaction.atomic():
            with connection.cursor() as cursor:
                self._assert_operational_targets_still_empty(cursor, schema_name, copy_rows)
                for policy in COPY_POLICIES:
                    row = next(
                        (
                            item
                            for item in copy_rows
                            if item["app"] == policy.app_label and item["table"] == policy.table_name
                        ),
                        None,
                    )
                    if row is None:
                        continue
                    copied = self._copy_policy_rows(
                        cursor=cursor,
                        schema_name=schema_name,
                        policy=policy,
                        params=params,
                    )
                    if copied != row["source_count"]:
                        raise CommandError(
                            f"Copy count changed for {policy.table_name}: "
                            f"planned={row['source_count']} copied={copied}"
                        )
                    applied.append({"table": policy.table_name, "copied": copied})

                self._reset_sequences(cursor, schema_name, [row["table"] for row in copy_rows])

        return applied

    def _policy_for_copy_row(self, row):
        for policy in COPY_POLICIES:
            if policy.app_label == row["app"] and policy.table_name == row["table"]:
                return policy
        raise CommandError(f"No copy policy found for {row['table']}.")

    def _validate_apply_allowed(
        self,
        tenant,
        base_seed_rows,
        copy_rows,
        blocked_rows,
        allow_core_company=False,
        allow_existing_targets=False,
    ):
        if tenant.company_app.is_core_company and not allow_core_company:
            raise CommandError(
                "Refusing to copy operational data for a core company in this phase. "
                "Re-run with --allow-core-company only after dry-run review and backup."
            )
        if tenant.routing_enabled:
            raise CommandError("Refusing copy apply while tenant routing is enabled.")
        if not copy_rows:
            raise CommandError("Refusing copy apply because no copy policies were selected.")

        missing_base = [
            row["table"]
            for row in base_seed_rows
            if row["table"] in ESSENTIAL_BASE_SEED_TABLES and row["target_count"] is None
        ]
        if missing_base:
            raise CommandError(
                "Refusing copy apply because base seed target tables are missing: "
                + ", ".join(missing_base)
            )

        empty_base = [
            row["table"]
            for row in base_seed_rows
            if row["table"] in ESSENTIAL_BASE_SEED_TABLES and not row["target_count"]
        ]
        if empty_base:
            raise CommandError(
                "Refusing copy apply because base seed target tables are empty: "
                + ", ".join(empty_base)
            )

        missing_targets = [
            row["table"]
            for row in copy_rows
            if row["target_count"] is None
        ]
        if missing_targets:
            raise CommandError(
                "Refusing copy apply because operational target tables are missing: "
                + ", ".join(missing_targets)
            )

        populated_targets = [
            f"{row['table']}={row['target_count']}"
            for row in copy_rows
            if row["target_count"]
        ]
        if populated_targets and not allow_existing_targets:
            raise CommandError(
                "Refusing copy apply because operational target tables are not empty: "
                + ", ".join(populated_targets)
            )

        blocked_with_source = [
            f"{row['table']}={row['source_count']}"
            for row in blocked_rows
            if row["source_count"]
        ]
        if blocked_with_source:
            raise CommandError(
                "Refusing copy apply because blocked tables have source rows: "
                + ", ".join(blocked_with_source)
            )

    def _assert_operational_targets_still_empty(self, cursor, schema_name, copy_rows):
        populated = []
        for row in copy_rows:
            cursor.execute(f"SELECT COUNT(*) FROM {self._qualified_table(schema_name, row['table'])}")
            count = int(cursor.fetchone()[0])
            if count:
                populated.append(f"{row['table']}={count}")
        if populated:
            raise CommandError(
                "Tenant operational rows changed before apply could run: "
                + ", ".join(populated)
            )

    def _copy_policy_rows(self, cursor, schema_name, policy, params):
        source_columns = self._table_columns("public", policy.table_name)
        target_columns = self._table_columns(schema_name, policy.table_name)
        if not source_columns or not target_columns:
            raise CommandError(f"Cannot inspect columns for {policy.table_name}.")
        missing_source_columns = sorted(set(target_columns) - set(source_columns))
        extra_source_columns = sorted(set(source_columns) - set(target_columns))
        if missing_source_columns:
            raise CommandError(
                f"Column mismatch for {policy.table_name}: "
                f"missing public columns for tenant target: {missing_source_columns}"
            )
        if extra_source_columns:
            raise CommandError(
                f"Column mismatch for {policy.table_name}: "
                f"extra public columns not present in tenant target: {extra_source_columns}"
            )

        quoted_columns = ", ".join(connection.ops.quote_name(column) for column in target_columns)
        select_expressions = ", ".join(
            self._select_expression_for_column(schema_name, column)
            for column in target_columns
        )
        target = self._qualified_table(schema_name, policy.table_name)
        source = self._qualified_table("public", policy.table_name)
        cursor.execute(
            f"INSERT INTO {target} ({quoted_columns}) "
            f"SELECT {select_expressions} FROM {source} src WHERE {policy.where_sql}",
            params,
        )
        return cursor.rowcount

    def _validate_batch_resume_target(self, cursor, schema_name, policy, params):
        target = self._qualified_table(schema_name, policy.table_name)
        source = self._qualified_table("public", policy.table_name)
        cursor.execute(f"SELECT COUNT(*), COALESCE(MAX(id), 0) FROM {target}")
        tenant_count, max_id = cursor.fetchone()
        tenant_count = int(tenant_count or 0)
        max_id = int(max_id or 0)
        if not tenant_count:
            return 0

        resume_params = dict(params)
        resume_params["max_id"] = max_id
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {source} src
            WHERE ({policy.where_sql}) AND src.id <= %(max_id)s
            """,
            resume_params,
        )
        expected_prefix_count = int(cursor.fetchone()[0] or 0)
        if expected_prefix_count != tenant_count:
            raise CommandError(
                f"Cannot resume {policy.table_name}: tenant rows are not a complete "
                f"source prefix. tenant_count={tenant_count}, "
                f"expected_source_prefix_count={expected_prefix_count}, max_id={max_id}"
            )

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {target} tenant_row
            WHERE NOT EXISTS (
                SELECT 1
                FROM {source} src
                WHERE src.id = tenant_row.id AND ({policy.where_sql})
            )
            """,
            params,
        )
        unexpected_rows = int(cursor.fetchone()[0] or 0)
        if unexpected_rows:
            raise CommandError(
                f"Cannot resume {policy.table_name}: tenant contains "
                f"{unexpected_rows} rows outside the source policy."
            )

        self.stdout.write(
            f"    resume {policy.table_name}: existing={tenant_count} start_after_id={max_id}"
        )
        return max_id

    def _copy_policy_rows_batched(self, schema_name, policy, params, batch_size, start_after_id=0):
        source_columns = self._table_columns("public", policy.table_name)
        target_columns = self._table_columns(schema_name, policy.table_name)
        if "id" not in source_columns or "id" not in target_columns:
            raise CommandError(f"Batch copy requires an id column for {policy.table_name}.")
        if not source_columns or not target_columns:
            raise CommandError(f"Cannot inspect columns for {policy.table_name}.")
        missing_source_columns = sorted(set(target_columns) - set(source_columns))
        extra_source_columns = sorted(set(source_columns) - set(target_columns))
        if missing_source_columns:
            raise CommandError(
                f"Column mismatch for {policy.table_name}: "
                f"missing public columns for tenant target: {missing_source_columns}"
            )
        if extra_source_columns:
            raise CommandError(
                f"Column mismatch for {policy.table_name}: "
                f"extra public columns not present in tenant target: {extra_source_columns}"
            )

        quoted_columns = ", ".join(connection.ops.quote_name(column) for column in target_columns)
        select_expressions = ", ".join(
            self._select_expression_for_column(schema_name, column)
            for column in target_columns
        )
        target = self._qualified_table(schema_name, policy.table_name)
        source = self._qualified_table("public", policy.table_name)
        last_id = int(start_after_id or 0)
        total_copied = 0

        while True:
            batch_params = dict(params)
            batch_params.update({"last_id": last_id, "batch_size": batch_size})
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        WITH batch AS (
                            SELECT id
                            FROM {source}
                            WHERE ({policy.where_sql}) AND id > %(last_id)s
                            ORDER BY id
                            LIMIT %(batch_size)s
                        ),
                        inserted AS (
                            INSERT INTO {target} ({quoted_columns})
                            SELECT {select_expressions}
                            FROM {source} src
                            JOIN batch ON batch.id = src.id
                            RETURNING id
                        )
                        SELECT COUNT(*) AS copied, COALESCE(MAX(id), %(last_id)s) AS max_id
                        FROM inserted
                        """,
                        batch_params,
                    )
                    copied, max_id = cursor.fetchone()

            copied = int(copied or 0)
            if not copied:
                break
            total_copied += copied
            last_id = int(max_id)
            self.stdout.write(
                f"    batch copied {policy.table_name}: total={total_copied} last_id={last_id}"
            )

        return total_copied

    def _select_expression_for_column(self, schema_name, column):
        quoted_column = connection.ops.quote_name(column)
        if column not in USER_FK_COLUMNS:
            return f"src.{quoted_column}"
        tenant_users = self._qualified_table(schema_name, "accounts_user")
        return (
            f"CASE WHEN src.{quoted_column} IS NULL THEN NULL "
            f"WHEN EXISTS (SELECT 1 FROM {tenant_users} tu WHERE tu.id = src.{quoted_column}) "
            f"THEN src.{quoted_column} ELSE NULL END AS {quoted_column}"
        )

    def _table_columns(self, schema_name, table_name):
        if not self._table_exists(schema_name, table_name):
            return []
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                [schema_name, table_name],
            )
            return [row[0] for row in cursor.fetchall()]

    def _reset_sequences(self, cursor, schema_name, table_names):
        for table_name in table_names:
            self._reset_sequence(cursor, schema_name, table_name)

    def _reset_sequence(self, cursor, schema_name, table_name):
        if "id" not in self._table_columns(schema_name, table_name):
            return
        qualified_name = f"{schema_name}.{table_name}"
        cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [qualified_name])
        sequence_name = cursor.fetchone()[0]
        if not sequence_name:
            return
        cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {self._qualified_table(schema_name, table_name)}")
        max_id = int(cursor.fetchone()[0])
        if max_id:
            cursor.execute("SELECT setval(%s, %s, true)", [sequence_name, max_id])

    def _table_count(self, schema_name, table_name):
        if not self._table_exists(schema_name, table_name):
            return None
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {self._qualified_table(schema_name, table_name)}")
            return int(cursor.fetchone()[0])

    def _filtered_count(self, schema_name, table_name, where_sql, params):
        if not self._table_exists(schema_name, table_name):
            return None
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM {self._qualified_table(schema_name, table_name)} WHERE {where_sql}",
                params,
            )
            return int(cursor.fetchone()[0])

    def _qualified_table(self, schema_name, table_name):
        return f"{connection.ops.quote_name(schema_name)}.{connection.ops.quote_name(table_name)}"
