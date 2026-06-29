from django.apps import apps as global_apps
from django.core.management.base import CommandError
from django.db import transaction
from django.db.migrations.state import ModelState, ProjectState

from apps.accounts.management.commands.plan_tenant_table_creation import (
    Command as PlanTenantTableCreationCommand,
)


class Command(PlanTenantTableCreationCommand):
    help = (
        "Create tenant tables from the reviewed dry-run plan. Apply mode is "
        "restricted to non-core companies with empty tenant schemas."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(self._default_tenant_apps()),
            help="App labels to include in the tenant table creation plan.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Actually create tables. Refused for core companies and non-empty "
                "schemas in this phase."
            ),
        )
        parser.add_argument(
            "--allow-core-company",
            action="store_true",
            help=(
                "Allow apply for a core company after dry-run review. This is required "
                "for the controlled cheonha preparation phase."
            ),
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")
        if self._connection().vendor != "postgresql":
            raise CommandError("Tenant table creation dry-run requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))

        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        tenant_tables = self._table_names(schema_name)
        table_count = len(tenant_tables)
        concrete_models = self._tenant_concrete_models(selected_apps, tenant_tables)
        dependency_details = self._build_dependency_details(concrete_models)
        dependencies = self._details_to_dependencies(dependency_details)
        creation_order, blocked_models = self._topological_order(concrete_models, dependencies)
        deferred_resolution = (
            self._plan_nullable_fk_deferrals(concrete_models, dependency_details)
            if blocked_models
            else {
                "resolved": True,
                "creation_order": creation_order,
                "blocked_models": [],
                "deferred_fields": [],
            }
        )
        through_tables = self._auto_through_tables(concrete_models, tenant_tables)

        if not deferred_resolution["resolved"]:
            raise CommandError(
                "Tenant table creation is still blocked after nullable FK deferral. "
                "Run plan_tenant_table_creation for details."
            )
        if options["apply"]:
            self._validate_apply_allowed(
                tenant=tenant,
                table_count=table_count,
                allow_core_company=options["allow_core_company"],
            )

        mode = "APPLY" if options["apply"] else "dry-run"
        self.stdout.write(f"Tenant table creation {mode}")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  existing_tenant_tables: {table_count}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")

        self.stdout.write("Operation summary")
        self.stdout.write(f"  concrete model create_model operations: {len(deferred_resolution['creation_order'])}")
        self.stdout.write(f"  deferred nullable FK add_field operations: {len(deferred_resolution['deferred_fields'])}")
        self.stdout.write(f"  auto-created many-to-many tables: {len(through_tables)}")
        self.stdout.write("  migration rows to write now: 0")
        self.stdout.write("  data rows to copy now: 0")
        self.stdout.write("  routing changes now: 0")

        if table_count:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Tenant schema is not empty. The future apply command must skip existing tables "
                    "and stay idempotent."
                )
            )

        self.stdout.write("")
        self.stdout.write("Phase 1. Create concrete model tables")
        self.stdout.write(
            "  The apply phase must create these with SET LOCAL search_path to the tenant schema."
        )
        for index, model in enumerate(deferred_resolution["creation_order"], start=1):
            note = self._deferred_field_note(model, deferred_resolution["deferred_fields"])
            self.stdout.write(f"  {index:02d}. create {self._label(model)} -> {model._meta.db_table}{note}")

        if through_tables:
            self.stdout.write("")
            self.stdout.write("Phase 1a. Auto-created M2M tables expected from create_model")
            for row in through_tables:
                self.stdout.write(f"  - {row['owner']} creates {row['table']}")

        if deferred_resolution["deferred_fields"]:
            self.stdout.write("")
            self.stdout.write("Phase 2. Add deferred nullable FK fields")
            for index, item in enumerate(deferred_resolution["deferred_fields"], start=1):
                self.stdout.write(
                    f"  {index:02d}. add {self._label(item['model'])}.{item['field'].name} "
                    f"-> {self._label(item['target'])}"
                )

        self.stdout.write("")
        self.stdout.write("Phase 3. Post-create verification before any data copy")
        self.stdout.write("  - Count tables in tenant schema.")
        self.stdout.write("  - Verify expected table names exist.")
        self.stdout.write("  - Verify no routing flag changed.")
        self.stdout.write("  - Keep CompanyTenant.routing_enabled=False.")

        if options["apply"]:
            self._apply_table_creation(
                schema_name=schema_name,
                creation_order=deferred_resolution["creation_order"],
                deferred_fields=deferred_resolution["deferred_fields"],
                expected_tables=self._expected_created_tables(
                    deferred_resolution["creation_order"],
                    through_tables,
                ),
            )
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Tenant tables created."))
            self.stdout.write(
                self.style.WARNING(
                    "Routing is still disabled and no data was copied. "
                    "Run verification before any next step."
                )
            )
            return

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - DRY RUN ONLY: no database changes were made.")
        self.stdout.write("  - --apply is available only for non-core companies with empty tenant schemas.")
        self.stdout.write("  - No table was created or altered.")
        self.stdout.write("  - No data was copied.")
        self.stdout.write("  - No migration row was written.")
        self.stdout.write("  - Routing remains disabled.")

    def _validate_apply_allowed(self, tenant, table_count, allow_core_company=False):
        if tenant.company_app.is_core_company and not allow_core_company:
            raise CommandError(
                "Refusing to create tenant tables for a core company in this phase. "
                "Re-run with --allow-core-company only after dry-run review."
            )
        if tenant.routing_enabled:
            raise CommandError("Refusing apply while tenant routing is enabled.")
        if table_count:
            raise CommandError(
                "Refusing apply because tenant schema is not empty. "
                "This phase only supports first-time creation into an empty schema."
            )

    def _apply_table_creation(self, schema_name, creation_order, deferred_fields, expected_tables):
        connection = self._connection()
        quoted_schema = connection.ops.quote_name(schema_name)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f"SET LOCAL search_path TO {quoted_schema}, public")

            with connection.schema_editor() as schema_editor:
                for model in creation_order:
                    model_to_create = self._model_without_deferred_fields(
                        model,
                        deferred_fields,
                    )
                    schema_editor.create_model(model_to_create)

                for item in deferred_fields:
                    schema_editor.add_field(item["model"], item["field"])

            created_tables = self._table_names(schema_name)
            missing_tables = sorted(expected_tables - created_tables)
            if missing_tables:
                raise CommandError(
                    "Tenant table creation verification failed. Missing tables: "
                    + ", ".join(missing_tables)
                )

    def _model_without_deferred_fields(self, model, deferred_fields):
        field_names = {
            item["field"].name
            for item in deferred_fields
            if item["model"] is model
        }
        if not field_names:
            return model

        project_state = ProjectState()
        for app_config in global_apps.get_app_configs():
            for candidate in app_config.get_models(include_auto_created=False):
                opts = candidate._meta
                if opts.proxy or not opts.managed:
                    continue
                model_state = ModelState.from_model(candidate)
                if candidate is model:
                    for field_name in field_names:
                        model_state.fields.pop(field_name, None)
                project_state.add_model(model_state)

        return project_state.apps.get_model(model._meta.app_label, model._meta.object_name)

    def _expected_created_tables(self, creation_order, through_tables):
        table_names = {model._meta.db_table for model in creation_order}
        table_names.update(row["table"] for row in through_tables)
        return table_names

    def _deferred_field_note(self, model, deferred_fields):
        names = [
            item["field"].name
            for item in deferred_fields
            if item["model"] is model
        ]
        if not names:
            return ""
        return f" (without deferred fields: {', '.join(names)})"

    def _connection(self):
        from django.db import connection

        return connection

    def _default_tenant_apps(self):
        from apps.accounts.management.commands.migrate_tenant_schema import DEFAULT_TENANT_APPS

        return DEFAULT_TENANT_APPS
