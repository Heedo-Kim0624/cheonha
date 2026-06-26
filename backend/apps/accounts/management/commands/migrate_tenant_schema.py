import re
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from apps.accounts.models import CompanyTenant


SCHEMA_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

DEFAULT_TENANT_APPS = (
    "contenttypes",
    "auth",
    "accounts",
    "partner",
    "crew",
    "dispatch",
    "region",
    "settlement",
    "inquiry",
    "tracking",
    "points",
    "mobile",
    "manpower",
    "territory",
    "one_settlement",
)

EXCLUDED_SCHEMA_HARDCODED_APPS = (
    "field_manager",
    "vehicle_management",
)


class Command(BaseCommand):
    help = (
        "Plan tenant schema migrations. This preparation command is dry-run by "
        "default and intentionally does not apply migrations yet."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to include in the tenant migration plan.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Reserved for a later phase. Currently refused for safety.",
        )

    def handle(self, *args, **options):
        if options["apply"]:
            raise CommandError(
                "--apply is intentionally disabled in this phase. "
                "Use this command as a read-only migration plan first."
            )

        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")

        if connection.vendor != "postgresql":
            raise CommandError("Tenant schema migration planning requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))

        schema_exists = self._schema_exists(schema_name)
        if not schema_exists:
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        table_count = self._schema_table_count(schema_name)
        migration_table_exists = self._table_exists(schema_name, "django_migrations")
        applied = self._applied_migrations(schema_name) if migration_table_exists else set()
        plan, unmigrated_apps = self._build_plan(selected_apps, applied)

        self.stdout.write("Tenant schema migration plan")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  table_count: {table_count}")
        self.stdout.write(f"  django_migrations_exists: {migration_table_exists}")
        self.stdout.write("")
        self.stdout.write("Included apps")
        self.stdout.write(f"  {', '.join(selected_apps)}")
        self.stdout.write("")
        self.stdout.write("Excluded for separate review")
        self.stdout.write(f"  {', '.join(EXCLUDED_SCHEMA_HARDCODED_APPS)}")
        self.stdout.write("")

        if not plan:
            self.stdout.write(self.style.SUCCESS("No pending migrations detected for selected apps."))
        else:
            self.stdout.write("Pending migration counts")
            for app_label, migrations in plan.items():
                self.stdout.write(f"  {app_label}: {len(migrations)}")
                for migration_name in migrations:
                    self.stdout.write(f"    - {migration_name}")

        if unmigrated_apps:
            self.stdout.write("")
            self.stdout.write("Selected apps without Django migrations")
            for app_label in unmigrated_apps:
                self.stdout.write(f"  - {app_label}")
            self.stdout.write(
                "  These apps need a reviewed tenant syncdb/table-creation strategy before apply."
            )

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - No migration was applied.")
        self.stdout.write("  - No table was created.")
        self.stdout.write("  - No data was copied.")
        self.stdout.write("  - Routing remains disabled.")
        self.stdout.write(
            "  - accounts migrations include central and tenant models together; "
            "actual apply needs a reviewed schema-safe migration strategy."
        )
        self.stdout.write(
            "  - field_manager and vehicle_management use hard-coded schemas today "
            "and are excluded from this tenant plan."
        )

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

    def _schema_table_count(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s",
                [schema_name],
            )
            return int(cursor.fetchone()[0])

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

    def _applied_migrations(self, schema_name):
        quoted_schema = connection.ops.quote_name(schema_name)
        quoted_table = connection.ops.quote_name("django_migrations")
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT app, name FROM {quoted_schema}.{quoted_table}")
            return {(row[0], row[1]) for row in cursor.fetchall()}

    def _build_plan(self, selected_apps, applied):
        from django.apps import apps

        loader = MigrationLoader(connection, ignore_no_migrations=True)
        by_app = defaultdict(list)
        disk_apps = {app_label for app_label, _migration_name in loader.disk_migrations}
        model_apps = {
            model._meta.app_label
            for model in apps.get_models()
            if model._meta.app_label in selected_apps
        }
        unmigrated_apps = sorted(model_apps - disk_apps)

        for app_label, migration_name in sorted(loader.disk_migrations):
            if app_label not in selected_apps:
                continue
            if (app_label, migration_name) in applied:
                continue
            by_app[app_label].append(migration_name)

        return dict(by_app), unmigrated_apps
