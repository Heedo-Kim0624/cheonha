import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.accounts.models import CompanyTenant


SCHEMA_NAME_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
BLOCKED_SCHEMA_NAMES = {"public", "information_schema"}


class Command(BaseCommand):
    help = (
        "Plan or create a company tenant schema. "
        "Default mode is dry-run and does not mutate the database."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually create the schema. Without this flag the command is read-only.",
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)

        self.stdout.write("Tenant schema creation plan")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  database_vendor: {connection.vendor}")

        exists = self._schema_exists(schema_name) if connection.vendor == "postgresql" else None
        if exists is None:
            self.stdout.write("  schema_exists: unknown (non-PostgreSQL connection)")
        else:
            self.stdout.write(f"  schema_exists: {exists}")

        create_sql = f"CREATE SCHEMA IF NOT EXISTS {connection.ops.quote_name(schema_name)};"
        self.stdout.write("")
        self.stdout.write("Planned SQL")
        self.stdout.write(f"  {create_sql}")
        self.stdout.write("")
        self.stdout.write("This command does not migrate tables, copy data, or enable routing.")

        if not options["apply"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("DRY RUN ONLY: no database changes were made."))
            return

        if connection.vendor != "postgresql":
            raise CommandError("--apply is only supported on PostgreSQL.")

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(create_sql)

        exists_after = self._schema_exists(schema_name)
        if not exists_after:
            raise CommandError(f"Schema {schema_name} was not found after CREATE SCHEMA.")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Schema ready: {schema_name}"))
        self.stdout.write(
            self.style.WARNING(
                "Routing remains disabled. Run migration/copy/verification steps before enabling tenant routing."
            )
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
        if value in BLOCKED_SCHEMA_NAMES or value.startswith("pg_"):
            raise CommandError(f"Refusing unsafe schema_name={value!r}.")
        if not value.startswith("tenant_"):
            raise CommandError(f"Tenant schema must start with 'tenant_': {value!r}.")
        if not SCHEMA_NAME_RE.match(value):
            raise CommandError(
                "Tenant schema must match ^[a-z_][a-z0-9_]{0,62}$: "
                f"{value!r}"
            )
        return value

    def _schema_exists(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [schema_name],
            )
            return cursor.fetchone() is not None
