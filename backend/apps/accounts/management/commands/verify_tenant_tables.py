from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, models

from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.management.commands.plan_tenant_tables import CENTRAL_ONLY_MODELS
from apps.accounts.models import CompanyTenant


class Command(BaseCommand):
    help = (
        "Read-only tenant schema verification. Compares model tables, columns, "
        "FKs, unique constraints, and basic index coverage against the tenant schema."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to verify in the tenant schema.",
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
            raise CommandError("Tenant table verification requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))
        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        expected_models = self._expected_tenant_models(selected_apps)
        actual_tables = self._table_names(schema_name)
        expected_tables = {model._meta.db_table for model in expected_models}

        errors = []
        warnings = []
        self._verify_tables(expected_tables, actual_tables, errors, warnings)
        self._verify_columns(schema_name, expected_models, actual_tables, errors, warnings)
        self._verify_foreign_keys(schema_name, expected_models, actual_tables, errors)
        self._verify_unique_constraints(schema_name, expected_models, actual_tables, errors, warnings)
        self._verify_indexes(schema_name, expected_models, actual_tables, warnings)

        self.stdout.write("Tenant table verification")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")
        self.stdout.write("Summary")
        self.stdout.write(f"  expected_tables: {len(expected_tables)}")
        self.stdout.write(f"  actual_tables: {len(actual_tables)}")
        self.stdout.write(f"  errors: {len(errors)}")
        self.stdout.write(f"  warnings: {len(warnings)}")

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
        self.stdout.write("  - No table was created or altered.")
        self.stdout.write("  - No data was copied.")
        self.stdout.write("  - No migration row was written.")
        self.stdout.write("  - Routing remains disabled.")

        if errors and not options["allow_incomplete"]:
            raise CommandError("Tenant table verification failed.")

        if errors:
            self.stdout.write(self.style.WARNING("Verification completed with errors allowed."))
        else:
            self.stdout.write(self.style.SUCCESS("Tenant table verification passed."))

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

    def _expected_tenant_models(self, selected_apps):
        expected = []
        for model in apps.get_models(include_auto_created=True):
            opts = model._meta
            if opts.app_label not in selected_apps:
                continue
            if opts.proxy or not opts.managed:
                continue
            if (opts.app_label, opts.object_name) in CENTRAL_ONLY_MODELS:
                continue
            if self._is_hardcoded_schema_table(opts.db_table):
                continue
            expected.append(model)
        return sorted(expected, key=lambda model: (model._meta.app_label, model._meta.db_table))

    def _verify_tables(self, expected_tables, actual_tables, errors, warnings):
        missing = sorted(expected_tables - actual_tables)
        extra = sorted(actual_tables - expected_tables)
        for table_name in missing:
            errors.append(f"missing table: {table_name}")
        for table_name in extra:
            warnings.append(f"extra table not mapped to selected tenant models: {table_name}")

    def _verify_columns(self, schema_name, expected_models, actual_tables, errors, warnings):
        for model in expected_models:
            table_name = model._meta.db_table
            if table_name not in actual_tables:
                continue
            actual_columns = self._columns(schema_name, table_name)
            expected_columns = {
                field.column: field
                for field in model._meta.local_fields
                if getattr(field, "concrete", False)
            }

            missing_columns = sorted(set(expected_columns) - set(actual_columns))
            extra_columns = sorted(set(actual_columns) - set(expected_columns))
            for column_name in missing_columns:
                errors.append(f"{table_name}: missing column {column_name}")
            for column_name in extra_columns:
                warnings.append(f"{table_name}: extra column {column_name}")

            for column_name, field in expected_columns.items():
                if column_name not in actual_columns:
                    continue
                expected_nullable = bool(field.null)
                actual_nullable = actual_columns[column_name]["is_nullable"]
                if expected_nullable != actual_nullable:
                    errors.append(
                        f"{table_name}.{column_name}: nullable mismatch "
                        f"expected={expected_nullable} actual={actual_nullable}"
                    )

    def _columns(self, schema_name, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                """,
                [schema_name, table_name],
            )
            return {
                row[0]: {"is_nullable": row[1] == "YES"}
                for row in cursor.fetchall()
            }

    def _verify_foreign_keys(self, schema_name, expected_models, actual_tables, errors):
        actual_fks = self._foreign_keys(schema_name)
        for model in expected_models:
            table_name = model._meta.db_table
            if table_name not in actual_tables:
                continue
            for field in model._meta.local_fields:
                if not self._is_fk_field(field):
                    continue
                if not getattr(field.remote_field, "model", None):
                    continue
                target_model = field.remote_field.model
                target_table = target_model._meta.db_table
                if self._is_hardcoded_schema_table(target_table):
                    continue
                expected = (table_name, field.column, target_table)
                if expected not in actual_fks:
                    errors.append(
                        f"{table_name}.{field.column}: missing FK to {target_table}"
                    )

    def _foreign_keys(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.constraint_schema = tc.constraint_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = %s
                """,
                [schema_name],
            )
            return {(row[0], row[1], row[2]) for row in cursor.fetchall()}

    def _verify_unique_constraints(self, schema_name, expected_models, actual_tables, errors, warnings):
        actual_uniques = self._unique_constraints(schema_name)
        for model in expected_models:
            table_name = model._meta.db_table
            if table_name not in actual_tables:
                continue
            expected_uniques = self._expected_unique_sets(model)
            for columns in expected_uniques:
                key = (table_name, tuple(columns))
                if key not in actual_uniques:
                    warnings.append(
                        f"{table_name}: unique/index coverage not found for ({', '.join(columns)})"
                    )

    def _unique_constraints(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tc.table_name, kcu.column_name, kcu.ordinal_position
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = %s
                  AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
                ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
                """,
                [schema_name],
            )
            rows = cursor.fetchall()
        grouped = defaultdict(list)
        for table_name, column_name, _position in rows:
            grouped[(table_name, column_name)].append(column_name)

        # Re-query grouped by constraint name to preserve multi-column unique order.
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tc.table_name, tc.constraint_name, kcu.column_name, kcu.ordinal_position
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = %s
                  AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
                ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
                """,
                [schema_name],
            )
            constraint_rows = cursor.fetchall()
        by_constraint = defaultdict(list)
        for table_name, constraint_name, column_name, _position in constraint_rows:
            by_constraint[(table_name, constraint_name)].append(column_name)
        return {
            (table_name, tuple(columns))
            for (table_name, _constraint_name), columns in by_constraint.items()
        }

    def _expected_unique_sets(self, model):
        uniques = []
        for field in model._meta.local_fields:
            if field.primary_key or field.unique:
                uniques.append((field.column,))
        for unique_together in model._meta.unique_together:
            uniques.append(tuple(model._meta.get_field(field_name).column for field_name in unique_together))
        for constraint in model._meta.constraints:
            if isinstance(constraint, models.UniqueConstraint) and constraint.fields:
                uniques.append(tuple(model._meta.get_field(field_name).column for field_name in constraint.fields))
        return sorted(set(uniques))

    def _verify_indexes(self, schema_name, expected_models, actual_tables, warnings):
        actual_index_columns = self._index_columns(schema_name)
        for model in expected_models:
            table_name = model._meta.db_table
            if table_name not in actual_tables:
                continue
            for columns in self._expected_index_sets(model):
                if not self._has_index_prefix(actual_index_columns.get(table_name, set()), columns):
                    warnings.append(
                        f"{table_name}: index coverage not found for ({', '.join(columns)})"
                    )

    def _index_columns(self, schema_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    tab.relname AS table_name,
                    array_agg(att.attname ORDER BY ord.ordinality) AS columns
                FROM pg_index idx
                JOIN pg_class ind ON ind.oid = idx.indexrelid
                JOIN pg_class tab ON tab.oid = idx.indrelid
                JOIN pg_namespace ns ON ns.oid = tab.relnamespace
                JOIN unnest(idx.indkey) WITH ORDINALITY AS ord(attnum, ordinality) ON TRUE
                JOIN pg_attribute att ON att.attrelid = tab.oid AND att.attnum = ord.attnum
                WHERE ns.nspname = %s
                GROUP BY tab.relname, ind.relname
                """,
                [schema_name],
            )
            rows = cursor.fetchall()
        indexes = defaultdict(set)
        for table_name, columns in rows:
            indexes[table_name].add(tuple(columns))
        return indexes

    def _expected_index_sets(self, model):
        indexes = []
        for field in model._meta.local_fields:
            if field.db_index and not field.unique:
                indexes.append((field.column,))
        for index in model._meta.indexes:
            if getattr(index, "fields", None):
                indexes.append(tuple(model._meta.get_field(field_name).column for field_name in index.fields))
        return sorted(set(indexes))

    def _has_index_prefix(self, actual_indexes, expected_columns):
        expected_columns = tuple(expected_columns)
        return any(index[: len(expected_columns)] == expected_columns for index in actual_indexes)

    def _is_fk_field(self, field):
        return bool(
            getattr(field, "concrete", False)
            and (getattr(field, "many_to_one", False) or getattr(field, "one_to_one", False))
            and getattr(field.remote_field, "model", None)
            and getattr(field, "db_constraint", True)
        )

    def _is_hardcoded_schema_table(self, table_name):
        return "." in table_name or '"' in table_name

