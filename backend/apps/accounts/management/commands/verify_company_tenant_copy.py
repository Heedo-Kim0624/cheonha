from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.accounts.management.commands.copy_company_to_tenant_schema import (
    BLOCKED_POLICIES,
    COPY_POLICIES,
    TEAM_IDS,
    USER_IDS,
)
from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.models import CompanyTenant


BASE_VERIFY_POLICIES = (
    {
        "app": "accounts",
        "model": "Team",
        "table": "accounts_team",
        "where": f"id IN ({TEAM_IDS})",
        "strict": True,
    },
    {
        "app": "accounts",
        "model": "User",
        "table": "accounts_user",
        "where": f"id IN ({USER_IDS})",
        "strict": True,
    },
    {
        "app": "mobile",
        "model": "MobileAppMessageConfig",
        "table": "mobile_app_message_config",
        "where": "TRUE",
        "strict": True,
    },
    {
        "app": "points",
        "model": "PointItem",
        "table": "points_point_items",
        "where": "TRUE",
        "strict": True,
    },
    {
        "app": "contenttypes",
        "model": "ContentType",
        "table": "django_content_type",
        "where": "TRUE",
        "strict": False,
        "note": "Tenant keeps only selected app content types, so public count can be larger.",
    },
    {
        "app": "auth",
        "model": "Permission",
        "table": "auth_permission",
        "where": "TRUE",
        "strict": False,
        "note": "Tenant keeps only selected app permissions, so public count can be larger.",
    },
)


AGGREGATE_COLUMNS = {
    "dispatch_dispatchrecord": ("boxes", "households", "original_boxes"),
    "settlement_settlement": (
        "total_receive",
        "total_pay",
        "total_overtime",
        "total_other_cost",
        "total_profit",
    ),
    "settlement_settlementdetail": (
        "boxes",
        "receive_amount",
        "pay_amount",
        "overtime_cost",
        "other_cost",
        "profit",
    ),
}


class Command(BaseCommand):
    help = (
        "Read-only source-vs-tenant data copy verification. Compares row counts, "
        "id checksums, and key operational aggregates."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to include in the verification.",
        )
        parser.add_argument(
            "--allow-incomplete",
            action="store_true",
            help="Print verification errors without failing the command.",
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")
        if connection.vendor != "postgresql":
            raise CommandError("Tenant copy verification requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(
            dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip())
        )
        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        params = {"company_code": company_code}
        rows = []
        errors = []
        warnings = []

        rows.extend(self._verify_base_tables(schema_name, selected_apps, params, errors, warnings))
        rows.extend(self._verify_operational_tables(schema_name, selected_apps, params, errors))
        blocked_rows = self._blocked_rows(schema_name, selected_apps, warnings)

        self.stdout.write("Company tenant copy verification")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")

        self.stdout.write("Summary")
        self.stdout.write(f"  verified_tables: {len(rows)}")
        self.stdout.write(f"  verified_source_rows: {sum(row['source']['count'] or 0 for row in rows)}")
        self.stdout.write(f"  verified_tenant_rows: {sum(row['tenant']['count'] or 0 for row in rows)}")
        self.stdout.write(f"  blocked_tables: {len(blocked_rows)}")
        self.stdout.write(f"  errors: {len(errors)}")
        self.stdout.write(f"  warnings: {len(warnings)}")

        self.stdout.write("")
        self.stdout.write("Verified tables")
        for row in rows:
            source = row["source"]
            tenant_stats = row["tenant"]
            status = "OK" if row["ok"] else "MISMATCH"
            self.stdout.write(
                f"  - {status} {row['app']}.{row['model']} -> {row['table']}: "
                f"source_count={source['count']} tenant_count={tenant_stats['count']} "
                f"source_id_sum={source['id_sum']} tenant_id_sum={tenant_stats['id_sum']}"
            )
            aggregate_diff = self._aggregate_diff(source["aggregates"], tenant_stats["aggregates"])
            if aggregate_diff:
                self.stdout.write(f"    aggregate_diff: {aggregate_diff}")
            if row.get("note"):
                self.stdout.write(f"    note: {row['note']}")

        if blocked_rows:
            self.stdout.write("")
            self.stdout.write("Blocked policies")
            for row in blocked_rows:
                self.stdout.write(
                    f"  - {row['app']}.{row['model']} -> {row['table']}: "
                    f"public_rows={row['source_count']} tenant_rows={row['tenant_count']}"
                )
                self.stdout.write(f"    reason: {row['reason']}")

        if errors:
            self.stdout.write("")
            self.stdout.write("Errors")
            for message in errors[:200]:
                self.stdout.write(f"  - {message}")
            if len(errors) > 200:
                self.stdout.write(f"  ... {len(errors) - 200} more")

        if warnings:
            self.stdout.write("")
            self.stdout.write("Warnings")
            for message in warnings[:200]:
                self.stdout.write(f"  - {message}")
            if len(warnings) > 200:
                self.stdout.write(f"  ... {len(warnings) - 200} more")

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - Read-only verification: no database changes were made.")
        self.stdout.write("  - Routing remains unchanged.")

        if errors and not options["allow_incomplete"]:
            raise CommandError("Company tenant copy verification failed.")

        if errors:
            self.stdout.write(self.style.WARNING("Verification completed with errors allowed."))
        else:
            self.stdout.write(self.style.SUCCESS("Company tenant copy verification passed."))

    def _verify_base_tables(self, schema_name, selected_apps, params, errors, warnings):
        rows = []
        for policy in BASE_VERIFY_POLICIES:
            if policy["app"] not in selected_apps:
                continue
            row = self._compare_policy(
                schema_name=schema_name,
                app_label=policy["app"],
                model_label=policy["model"],
                table_name=policy["table"],
                where_sql=policy["where"],
                params=params,
                strict=policy["strict"],
                note=policy.get("note", ""),
            )
            rows.append(row)
            if row["ok"]:
                continue
            message = self._mismatch_message(row)
            if policy["strict"]:
                errors.append(message)
            else:
                warnings.append(message)
        return rows

    def _verify_operational_tables(self, schema_name, selected_apps, params, errors):
        rows = []
        for policy in COPY_POLICIES:
            if policy.app_label not in selected_apps:
                continue
            row = self._compare_policy(
                schema_name=schema_name,
                app_label=policy.app_label,
                model_label=policy.model_label,
                table_name=policy.table_name,
                where_sql=policy.where_sql,
                params=params,
                strict=True,
                note=policy.note,
            )
            rows.append(row)
            if not row["ok"]:
                errors.append(self._mismatch_message(row))
        return rows

    def _compare_policy(
        self,
        schema_name,
        app_label,
        model_label,
        table_name,
        where_sql,
        params,
        strict,
        note="",
    ):
        source = self._stats("public", table_name, where_sql, params)
        tenant_stats = self._stats(schema_name, table_name, "TRUE", {})
        ok = source == tenant_stats if strict else self._is_present(tenant_stats)
        return {
            "app": app_label,
            "model": model_label,
            "table": table_name,
            "source": source,
            "tenant": tenant_stats,
            "ok": ok,
            "strict": strict,
            "note": note,
        }

    def _blocked_rows(self, schema_name, selected_apps, warnings):
        rows = []
        for policy in BLOCKED_POLICIES:
            if policy.app_label not in selected_apps:
                continue
            source_count = self._count("public", policy.table_name, "TRUE", {})
            tenant_count = self._count(schema_name, policy.table_name, "TRUE", {})
            rows.append(
                {
                    "app": policy.app_label,
                    "model": policy.model_label,
                    "table": policy.table_name,
                    "source_count": source_count,
                    "tenant_count": tenant_count,
                    "reason": policy.reason,
                }
            )
            if source_count:
                warnings.append(
                    f"blocked table has source rows and still needs policy: {policy.table_name}={source_count}"
                )
        return rows

    def _stats(self, schema_name, table_name, where_sql, params):
        if not self._table_exists(schema_name, table_name):
            return {
                "count": None,
                "min_id": None,
                "max_id": None,
                "id_sum": None,
                "aggregates": {},
            }

        columns = self._table_columns(schema_name, table_name)
        aggregates = {}
        aggregate_selects = []
        for column_name in AGGREGATE_COLUMNS.get(table_name, ()):
            if column_name in columns:
                alias = f"sum_{column_name}"
                aggregate_selects.append(
                    f"COALESCE(SUM({connection.ops.quote_name(column_name)}), 0) AS {alias}"
                )

        id_selects = (
            "COUNT(*) AS row_count, "
            "MIN(id) AS min_id, "
            "MAX(id) AS max_id, "
            "COALESCE(SUM(id), 0) AS id_sum"
            if "id" in columns
            else "COUNT(*) AS row_count, NULL AS min_id, NULL AS max_id, NULL AS id_sum"
        )
        select_sql = id_selects
        if aggregate_selects:
            select_sql += ", " + ", ".join(aggregate_selects)

        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {select_sql} FROM {self._qualified_table(schema_name, table_name)} WHERE {where_sql}",
                params,
            )
            row = cursor.fetchone()
            description = [item[0] for item in cursor.description]

        values = dict(zip(description, row))
        for key, value in values.items():
            if key.startswith("sum_"):
                aggregates[key[4:]] = value

        return {
            "count": int(values["row_count"]),
            "min_id": values["min_id"],
            "max_id": values["max_id"],
            "id_sum": values["id_sum"],
            "aggregates": aggregates,
        }

    def _count(self, schema_name, table_name, where_sql, params):
        if not self._table_exists(schema_name, table_name):
            return None
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM {self._qualified_table(schema_name, table_name)} WHERE {where_sql}",
                params,
            )
            return int(cursor.fetchone()[0])

    def _aggregate_diff(self, source, tenant_stats):
        differences = []
        for key in sorted(set(source) | set(tenant_stats)):
            if source.get(key) != tenant_stats.get(key):
                differences.append(f"{key}: source={source.get(key)} tenant={tenant_stats.get(key)}")
        return "; ".join(differences)

    def _mismatch_message(self, row):
        return (
            f"{row['table']} mismatch: "
            f"source={row['source']} tenant={row['tenant']}"
        )

    def _is_present(self, stats):
        return stats["count"] is not None and stats["count"] > 0

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

    def _qualified_table(self, schema_name, table_name):
        return f"{connection.ops.quote_name(schema_name)}.{connection.ops.quote_name(table_name)}"
