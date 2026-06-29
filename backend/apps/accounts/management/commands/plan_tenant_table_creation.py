from collections import defaultdict

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.loader import MigrationLoader

from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.management.commands.plan_tenant_tables import (
    CENTRAL_ONLY_MODELS,
    DUAL_SCHEMA_MODELS,
)
from apps.accounts.models import CompanyTenant


class Command(BaseCommand):
    help = (
        "Read-only tenant table creation readiness plan. It determines concrete "
        "model creation order and dependency blockers without creating tables, "
        "copying data, or enabling routing."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels to include in the tenant table creation plan.",
        )
        parser.add_argument(
            "--show-sql",
            action="store_true",
            help=(
                "Show best-effort SQL for acyclic ready models only. If blockers "
                "exist, this intentionally refuses to print incomplete execution SQL."
            ),
        )

    def handle(self, *args, **options):
        company_code = str(options["company_code"] or "").strip().lower()
        if not company_code:
            raise CommandError("company_code is required.")
        if connection.vendor != "postgresql":
            raise CommandError("Tenant table creation planning requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))

        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        tenant_tables = self._table_names(schema_name)
        migration_apps = self._migration_app_labels()
        concrete_models = self._tenant_concrete_models(selected_apps, tenant_tables)
        dependency_details = self._build_dependency_details(concrete_models)
        dependencies = self._details_to_dependencies(dependency_details)
        creation_order, blocked_models = self._topological_order(concrete_models, dependencies)
        deferred_resolution = (
            self._plan_nullable_fk_deferrals(concrete_models, dependency_details)
            if blocked_models
            else None
        )
        through_tables = self._auto_through_tables(concrete_models, tenant_tables)
        syncdb_apps = sorted(
            {
                model._meta.app_label
                for model in concrete_models
                if model._meta.app_label not in migration_apps
            }
        )

        self.stdout.write("Tenant table creation readiness plan")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")

        self.stdout.write("Summary")
        self.stdout.write(f"  concrete tenant model tables pending: {len(concrete_models)}")
        self.stdout.write(f"  auto-created many-to-many tables pending: {len(through_tables)}")
        self.stdout.write(f"  ordered concrete models before blockers: {len(creation_order)}")
        self.stdout.write(f"  blocked concrete models: {len(blocked_models)}")
        readiness = "READY" if not blocked_models else "BLOCKED"
        self.stdout.write(f"  creation_readiness: {readiness}")
        if deferred_resolution:
            deferred_readiness = "READY" if deferred_resolution["resolved"] else "BLOCKED"
            self.stdout.write(f"  readiness_with_nullable_fk_deferral: {deferred_readiness}")

        if creation_order:
            self.stdout.write("")
            self.stdout.write("Acyclic creation order")
            for index, model in enumerate(creation_order, start=1):
                self.stdout.write(f"  {index:02d}. {self._label(model)} -> {model._meta.db_table}")

        if blocked_models:
            self.stdout.write("")
            self.stdout.write("Dependency blockers")
            for model in sorted(blocked_models, key=self._sort_key):
                unresolved = sorted(
                    self._label(dep)
                    for dep in dependencies[model]
                    if dep in blocked_models
                )
                suffix = f" depends on {', '.join(unresolved)}" if unresolved else ""
                self.stdout.write(f"  - {self._label(model)}{suffix}")

            cycles = self._find_cycles(blocked_models, dependencies)
            if cycles:
                self.stdout.write("")
                self.stdout.write("Detected dependency cycles")
                for cycle in cycles[:5]:
                    self.stdout.write(f"  - {' -> '.join(cycle)}")

        if deferred_resolution:
            self.stdout.write("")
            self.stdout.write("Nullable FK split plan")
            if deferred_resolution["deferred_fields"]:
                self.stdout.write("  Defer these nullable FK fields during initial table creation:")
                for item in deferred_resolution["deferred_fields"]:
                    self.stdout.write(
                        f"    - {self._label(item['model'])}.{item['field'].name} "
                        f"-> {self._label(item['target'])}"
                    )
            else:
                self.stdout.write("  No nullable FK deferral candidate was found.")

            if deferred_resolution["resolved"]:
                self.stdout.write("  Result: all concrete tables can be ordered after deferral.")
                self.stdout.write("  Creation order after deferral:")
                for index, model in enumerate(deferred_resolution["creation_order"], start=1):
                    self.stdout.write(f"    {index:02d}. {self._label(model)} -> {model._meta.db_table}")
                self.stdout.write("  Add deferred FK fields after all target tables exist:")
                for index, item in enumerate(deferred_resolution["deferred_fields"], start=1):
                    self.stdout.write(
                        f"    {index:02d}. add {self._label(item['model'])}.{item['field'].name}"
                    )
            else:
                self.stdout.write("  Result: still blocked after nullable FK deferral.")
                if deferred_resolution["blocked_models"]:
                    self.stdout.write("  Remaining blockers:")
                    for model in deferred_resolution["blocked_models"]:
                        self.stdout.write(f"    - {self._label(model)}")

        if through_tables:
            self.stdout.write("")
            self.stdout.write("Auto-created many-to-many tables")
            for row in through_tables:
                self.stdout.write(
                    f"  - {row['owner']} creates {row['through']} -> {row['table']}"
                )

        if syncdb_apps:
            self.stdout.write("")
            self.stdout.write("Apps needing syncdb/schema-editor handling")
            for app_label in syncdb_apps:
                self.stdout.write(f"  - {app_label}")

        if options["show_sql"]:
            if blocked_models:
                raise CommandError(
                    "--show-sql refused because dependency blockers exist. "
                    "Resolve/split blockers first so the SQL preview is not misleading."
                )
            self._write_sql_preview(schema_name, creation_order)

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - No table was created or altered.")
        self.stdout.write("  - No data was copied.")
        self.stdout.write("  - No migration row was written.")
        self.stdout.write("  - Routing remains disabled.")
        self.stdout.write(
            "  - If creation_readiness is BLOCKED, build a reviewed split-table plan before apply."
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

    def _tenant_concrete_models(self, selected_apps, tenant_tables):
        selected = []
        for model in apps.get_models(include_auto_created=False):
            opts = model._meta
            model_key = (opts.app_label, opts.object_name)
            if opts.app_label not in selected_apps:
                continue
            if opts.proxy or not opts.managed:
                continue
            if model_key in CENTRAL_ONLY_MODELS:
                continue
            if self._is_hardcoded_schema_table(opts.db_table):
                continue
            if opts.db_table in tenant_tables:
                continue
            selected.append(model)
        return sorted(selected, key=self._sort_key)

    def _build_dependency_details(self, concrete_models):
        concrete_set = set(concrete_models)
        dependencies = {model: defaultdict(list) for model in concrete_models}

        for model in concrete_models:
            for field in model._meta.get_fields():
                if field.auto_created and not field.concrete:
                    continue
                remote_model = getattr(field, "remote_field", None)
                if not remote_model:
                    continue
                target_model = remote_model.model
                if target_model == "self" or target_model is model:
                    continue
                if target_model in concrete_set:
                    dependencies[model][target_model].append(field)

            for field in model._meta.many_to_many:
                target_model = field.remote_field.model
                if target_model in concrete_set and target_model is not model:
                    dependencies[model][target_model].append(field)

        return dependencies

    def _details_to_dependencies(self, dependency_details, deferred_fields=None):
        deferred_fields = set(deferred_fields or ())
        dependencies = {}
        for model, targets in dependency_details.items():
            dependencies[model] = set()
            for target_model, fields in targets.items():
                active_fields = [
                    field
                    for field in fields
                    if self._field_key(model, field) not in deferred_fields
                ]
                if active_fields:
                    dependencies[model].add(target_model)
        return dependencies

    def _topological_order(self, concrete_models, dependencies):
        remaining = set(concrete_models)
        ordered = []
        ordered_set = set()

        while remaining:
            ready = sorted(
                [
                    model
                    for model in remaining
                    if not (dependencies[model] - ordered_set)
                ],
                key=self._sort_key,
            )
            if not ready:
                break
            model = ready[0]
            remaining.remove(model)
            ordered.append(model)
            ordered_set.add(model)

        return ordered, sorted(remaining, key=self._sort_key)

    def _plan_nullable_fk_deferrals(self, concrete_models, dependency_details):
        deferred_fields = []
        deferred_keys = set()
        max_iterations = len(concrete_models) * 2

        for _iteration in range(max_iterations):
            dependencies = self._details_to_dependencies(dependency_details, deferred_keys)
            creation_order, blocked_models = self._topological_order(concrete_models, dependencies)
            if not blocked_models:
                return {
                    "resolved": True,
                    "creation_order": creation_order,
                    "blocked_models": [],
                    "deferred_fields": deferred_fields,
                }

            candidate = self._best_nullable_fk_candidate(
                blocked_models=blocked_models,
                dependency_details=dependency_details,
                deferred_keys=deferred_keys,
            )
            if candidate is None:
                return {
                    "resolved": False,
                    "creation_order": creation_order,
                    "blocked_models": blocked_models,
                    "deferred_fields": deferred_fields,
                }

            field_key = self._field_key(candidate["model"], candidate["field"])
            deferred_keys.add(field_key)
            deferred_fields.append(candidate)

        dependencies = self._details_to_dependencies(dependency_details, deferred_keys)
        creation_order, blocked_models = self._topological_order(concrete_models, dependencies)
        return {
            "resolved": not blocked_models,
            "creation_order": creation_order,
            "blocked_models": blocked_models,
            "deferred_fields": deferred_fields,
        }

    def _best_nullable_fk_candidate(self, blocked_models, dependency_details, deferred_keys):
        blocked_set = set(blocked_models)
        candidates = []

        for model in sorted(blocked_models, key=self._sort_key):
            for target_model, fields in dependency_details[model].items():
                if target_model not in blocked_set:
                    continue
                for field in fields:
                    if self._field_key(model, field) in deferred_keys:
                        continue
                    if not self._is_nullable_fk_candidate(field):
                        continue
                    candidates.append(
                        {
                            "model": model,
                            "target": target_model,
                            "field": field,
                            "priority": self._defer_priority(model, field),
                        }
                    )

        if not candidates:
            return None

        scored = []
        for candidate in candidates:
            trial_keys = set(deferred_keys)
            trial_keys.add(self._field_key(candidate["model"], candidate["field"]))
            dependencies = self._details_to_dependencies(dependency_details, trial_keys)
            _order, blocked_after = self._topological_order(
                list(dependency_details.keys()),
                dependencies,
            )
            reduction = len(blocked_models) - len(blocked_after)
            scored.append((reduction, candidate["priority"], candidate))

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1],
                self._label(item[2]["model"]),
                item[2]["field"].name,
            )
        )
        return scored[0][2]

    def _is_nullable_fk_candidate(self, field):
        return bool(
            getattr(field, "concrete", False)
            and (getattr(field, "many_to_one", False) or getattr(field, "one_to_one", False))
            and getattr(field, "null", False)
        )

    def _defer_priority(self, model, field):
        label = self._label(model)
        if label == "accounts.User" and field.name == "team":
            return 0
        if label == "accounts.Team" and field.name == "leader":
            return 1
        if field.name in {"created_by", "updated_by"}:
            return 20
        return 10

    def _auto_through_tables(self, concrete_models, tenant_tables):
        rows = []
        concrete_set = set(concrete_models)
        for model in concrete_models:
            for field in model._meta.many_to_many:
                through = field.remote_field.through
                if not through._meta.auto_created:
                    continue
                if through._meta.db_table in tenant_tables:
                    continue
                remote_model = field.remote_field.model
                if remote_model not in concrete_set and self._model_key(remote_model) not in CENTRAL_ONLY_MODELS:
                    continue
                rows.append(
                    {
                        "owner": self._label(model),
                        "through": self._label(through),
                        "table": through._meta.db_table,
                    }
                )
        return sorted(rows, key=lambda row: (row["owner"], row["table"]))

    def _find_cycles(self, blocked_models, dependencies):
        blocked = set(blocked_models)
        graph = {
            model: sorted(dependencies[model] & blocked, key=self._sort_key)
            for model in blocked
        }
        cycles = []

        def visit(node, path):
            if node in path:
                start = path.index(node)
                cycle = path[start:] + [node]
                labels = [self._label(item) for item in cycle]
                if labels not in cycles:
                    cycles.append(labels)
                return
            if len(cycles) >= 5:
                return
            for child in graph.get(node, []):
                visit(child, path + [node])

        for model in sorted(blocked, key=self._sort_key):
            visit(model, [])
            if len(cycles) >= 5:
                break
        return cycles

    def _write_sql_preview(self, schema_name, creation_order):
        quoted_schema = connection.ops.quote_name(schema_name)
        self.stdout.write("")
        self.stdout.write("SQL preview")
        self.stdout.write("  -- Read-only preview. Not executed by this command.")
        self.stdout.write(f"  SET LOCAL search_path TO {quoted_schema}, public;")
        with connection.schema_editor(collect_sql=True) as schema_editor:
            for model in creation_order:
                schema_editor.create_model(model)
        for statement in schema_editor.collected_sql:
            self.stdout.write(f"  {statement}")

    def _model_key(self, model):
        return (model._meta.app_label, model._meta.object_name)

    def _field_key(self, model, field):
        return (self._label(model), field.name)

    def _label(self, model):
        return f"{model._meta.app_label}.{model._meta.object_name}"

    def _sort_key(self, model):
        return (model._meta.app_label, model._meta.db_table, model._meta.object_name)

    def _is_hardcoded_schema_table(self, table_name):
        return "." in table_name or '"' in table_name
