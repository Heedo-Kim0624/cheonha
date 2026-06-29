from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    EXCLUDED_SCHEMA_HARDCODED_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.models import CompanyTenant


CENTRAL_ONLY_MODELS = {
    ("accounts", "CompanyApp"),
    ("accounts", "CompanyTenant"),
    ("accounts", "Shipper"),
}

DUAL_SCHEMA_MODELS = {
    ("accounts", "User"),
}


class Command(BaseCommand):
    help = (
        "Read-only tenant table inventory. It shows which model tables would be "
        "expected in a tenant schema without creating tables, copying data, or "
        "enabling routing."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to include in the tenant table inventory.",
        )
        parser.add_argument(
            "--with-counts",
            action="store_true",
            help=(
                "Also count rows in existing public tables. This can be slower on "
                "large tables, so it is off by default."
            ),
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")
        if connection.vendor != "postgresql":
            raise CommandError("Tenant table planning requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))

        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        public_tables = self._table_names("public")
        tenant_tables = self._table_names(schema_name)
        migration_apps = self._migration_app_labels()
        rows = self._collect_rows(
            selected_apps=selected_apps,
            public_tables=public_tables,
            tenant_tables=tenant_tables,
            migration_apps=migration_apps,
            with_counts=options["with_counts"],
        )

        self.stdout.write("Tenant table inventory")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")

        stats = self._build_stats(rows)
        self.stdout.write("Summary")
        self.stdout.write(f"  tenant target tables: {stats['tenant_total']}")
        self.stdout.write(f"  tenant existing tables: {stats['tenant_existing']}")
        self.stdout.write(f"  tenant missing tables: {stats['tenant_missing']}")
        self.stdout.write(f"  central-only models: {stats['central_only']}")
        self.stdout.write(f"  hard-coded schema tables: {stats['hardcoded']}")
        self.stdout.write("")

        self._write_grouped_rows("Tenant tables missing", rows, lambda row: row["target"] == "tenant" and not row["tenant_exists"])
        self._write_grouped_rows("Tenant tables already present", rows, lambda row: row["target"] == "tenant" and row["tenant_exists"])
        self._write_grouped_rows("Central-only models kept in public", rows, lambda row: row["target"] == "public")
        self._write_grouped_rows("Hard-coded schema models for separate review", rows, lambda row: row["target"] == "hardcoded")

        syncdb_apps = sorted({row["app"] for row in rows if row["mode"] == "syncdb" and row["target"] == "tenant"})
        if syncdb_apps:
            self.stdout.write("")
            self.stdout.write("Tenant apps without Django migrations")
            for app_label in syncdb_apps:
                self.stdout.write(f"  - {app_label}")
            self.stdout.write(
                "  These need an explicit schema-editor/syncdb strategy before any table creation step."
            )

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - No table was created or altered.")
        self.stdout.write("  - No data was copied.")
        self.stdout.write("  - No migration row was written.")
        self.stdout.write("  - Routing remains disabled.")

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

    def _table_names(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                """,
                [schema_name],
            )
            return {row[0] for row in cursor.fetchall()}

    def _migration_app_labels(self):
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        return {app_label for app_label, _migration_name in loader.disk_migrations}

    def _collect_rows(self, selected_apps, public_tables, tenant_tables, migration_apps, with_counts):
        rows = []
        for model in apps.get_models(include_auto_created=True):
            opts = model._meta
            if opts.app_label not in selected_apps:
                continue
            if opts.proxy or not opts.managed:
                continue

            app_label = opts.app_label
            model_name = opts.object_name
            table_name = opts.db_table
            model_key = (app_label, model_name)
            hardcoded = self._is_hardcoded_schema_table(table_name)
            mode = "migration" if app_label in migration_apps else "syncdb"
            row = {
                "app": app_label,
                "model": model_name,
                "table": table_name,
                "mode": mode,
                "public_exists": table_name in public_tables,
                "tenant_exists": table_name in tenant_tables,
                "public_count": None,
            }

            if hardcoded:
                row["target"] = "hardcoded"
            elif model_key in CENTRAL_ONLY_MODELS:
                row["target"] = "public"
            elif model_key in DUAL_SCHEMA_MODELS:
                row["target"] = "tenant"
                row["mode"] = f"{mode}, dual"
            else:
                row["target"] = "tenant"

            if with_counts and row["public_exists"] and not hardcoded:
                row["public_count"] = self._public_row_count(table_name)

            rows.append(row)

        return sorted(rows, key=lambda item: (item["app"], item["target"], item["table"]))

    def _is_hardcoded_schema_table(self, table_name):
        return "." in table_name or '"' in table_name

    def _public_row_count(self, table_name):
        quoted_schema = connection.ops.quote_name("public")
        quoted_table = connection.ops.quote_name(table_name)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {quoted_schema}.{quoted_table}")
            return int(cursor.fetchone()[0])

    def _build_stats(self, rows):
        tenant_rows = [row for row in rows if row["target"] == "tenant"]
        return {
            "tenant_total": len(tenant_rows),
            "tenant_existing": sum(1 for row in tenant_rows if row["tenant_exists"]),
            "tenant_missing": sum(1 for row in tenant_rows if not row["tenant_exists"]),
            "central_only": sum(1 for row in rows if row["target"] == "public"),
            "hardcoded": sum(1 for row in rows if row["target"] == "hardcoded"),
        }

    def _write_grouped_rows(self, title, rows, predicate):
        selected = [row for row in rows if predicate(row)]
        if not selected:
            return

        grouped = defaultdict(list)
        for row in selected:
            grouped[row["app"]].append(row)

        self.stdout.write("")
        self.stdout.write(title)
        for app_label in sorted(grouped):
            self.stdout.write(f"  {app_label}")
            for row in grouped[app_label]:
                suffix = ""
                if row["public_count"] is not None:
                    suffix = f", public_rows={row['public_count']}"
                self.stdout.write(
                    "    - "
                    f"{row['model']} -> {row['table']} "
                    f"({row['mode']}, public_exists={row['public_exists']}{suffix})"
                )

