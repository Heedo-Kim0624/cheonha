from collections import Counter

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q

from apps.accounts.management.commands.migrate_tenant_schema import (
    DEFAULT_TENANT_APPS,
    SCHEMA_NAME_RE,
)
from apps.accounts.management.commands.plan_tenant_tables import CENTRAL_ONLY_MODELS
from apps.accounts.models import CompanyTenant, Team, User
from apps.mobile.models import MobileAppMessageConfig
from apps.points.models import PointItem


REFERENCE_TABLES = (
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

OPERATIONAL_TABLE_GROUPS_EXCLUDED = (
    "crew_*",
    "dispatch_*",
    "settlement_*",
    "region_*",
    "inquiry_*",
    "tracking_*",
    "manpower_*",
    "territory_*",
    "mobile_app_users",
    "mobile_passwords",
    "points_point_transactions",
    "points_point_redemptions",
)


class Command(BaseCommand):
    help = (
        "Plan or apply base tenant seed data for a prepared non-core tenant schema."
    )

    def add_arguments(self, parser):
        parser.add_argument("company_code", help="CompanyApp.code, for example cheonha or new")
        parser.add_argument(
            "--apps",
            nargs="+",
            default=list(DEFAULT_TENANT_APPS),
            help="App labels used to derive content type and permission seed rows.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Insert reference rows into an empty non-core tenant schema. "
                "Operational rows and routing are not changed."
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
        if connection.vendor != "postgresql":
            raise CommandError("Tenant base seed planning requires PostgreSQL.")

        tenant = self._get_tenant(company_code)
        schema_name = self._validate_schema_name(tenant.schema_name)
        selected_apps = tuple(dict.fromkeys(str(app).strip() for app in options["apps"] if str(app).strip()))

        if not self._schema_exists(schema_name):
            raise CommandError(
                f"Schema {schema_name!r} does not exist. "
                f"Run create_tenant_schema {company_code} --apply first."
            )

        tenant_table_counts = self._tenant_table_counts(schema_name, REFERENCE_TABLES)
        content_type_plan = self._content_type_plan(selected_apps)
        permission_plan = self._permission_plan(content_type_plan)
        auth_group_plan = self._auth_group_plan(permission_plan["ids"])
        company_plan = self._company_user_team_plan(tenant)
        app_config_plan = self._app_config_plan()
        warnings = self._build_warnings(
            tenant=tenant,
            tenant_table_counts=tenant_table_counts,
            content_type_plan=content_type_plan,
            company_plan=company_plan,
        )

        mode = "APPLY" if options["apply"] else "dry-run"
        self.stdout.write(f"Tenant base seed {mode}")
        self.stdout.write(f"  company: {tenant.company_app.code} ({tenant.company_app.name})")
        self.stdout.write(f"  schema: {schema_name}")
        self.stdout.write(f"  status: {tenant.status}")
        self.stdout.write(f"  routing_enabled: {tenant.routing_enabled}")
        self.stdout.write(f"  selected_apps: {', '.join(selected_apps)}")
        self.stdout.write("")

        self.stdout.write("Existing tenant reference rows")
        for table_name in REFERENCE_TABLES:
            count = tenant_table_counts.get(table_name)
            label = "missing table" if count is None else count
            self.stdout.write(f"  {table_name}: {label}")

        self.stdout.write("")
        self.stdout.write("Planned seed batches")
        self.stdout.write(
            f"  content types: {content_type_plan['total_count']} "
            f"(copy existing public rows: {content_type_plan['copy_count']}, "
            f"generate missing rows: {content_type_plan['generate_count']})"
        )
        self.stdout.write(
            f"  permissions: {permission_plan['total_count']} "
            f"(copy existing public rows: {permission_plan['copy_count']}, "
            f"generate missing defaults: {permission_plan['generate_count']})"
        )
        self.stdout.write(f"  groups: {auth_group_plan['group_count']}")
        self.stdout.write(
            f"  group-permission links for selected permissions: "
            f"{auth_group_plan['group_permission_count']}"
        )
        self.stdout.write(f"  company teams: {company_plan['team_count']}")
        self.stdout.write(f"  company users: {company_plan['user_count']}")
        self.stdout.write(f"  user-group links: {company_plan['user_group_count']}")
        self.stdout.write(f"  user-permission links: {company_plan['user_permission_count']}")
        self.stdout.write(f"  mobile app message configs: {app_config_plan['mobile_message_count']}")
        self.stdout.write(f"  point catalog items: {app_config_plan['point_item_count']}")

        self.stdout.write("")
        self.stdout.write("Company user role summary")
        for role, count in sorted(company_plan["roles"].items()):
            self.stdout.write(f"  {role}: {count}")
        if company_plan["sample_users"]:
            self.stdout.write("  sample users: " + ", ".join(company_plan["sample_users"]))
        else:
            self.stdout.write("  sample users: none")

        self.stdout.write("")
        self.stdout.write("Company team summary")
        if company_plan["sample_teams"]:
            self.stdout.write("  sample teams: " + ", ".join(company_plan["sample_teams"]))
        else:
            self.stdout.write("  sample teams: none")

        if content_type_plan["missing_keys"]:
            self.stdout.write("")
            self.stdout.write("Missing public content types")
            for app_label, model_name in sorted(content_type_plan["missing_keys"]):
                self.stdout.write(f"  - {app_label}.{model_name}")

        if warnings:
            self.stdout.write("")
            self.stdout.write("Warnings")
            for message in warnings:
                self.stdout.write(f"  - {message}")

        self.stdout.write("")
        self.stdout.write("Operational data excluded from this seed step")
        for label in OPERATIONAL_TABLE_GROUPS_EXCLUDED:
            self.stdout.write(f"  - {label}")

        if options["apply"]:
            result = self._apply_seed(
                tenant=tenant,
                schema_name=schema_name,
                tenant_table_counts=tenant_table_counts,
                content_type_plan=content_type_plan,
                permission_plan=permission_plan,
                company_plan=company_plan,
                warnings=warnings,
                allow_core_company=options["allow_core_company"],
            )
            self.stdout.write("")
            self.stdout.write("Applied seed rows")
            for label, count in result.items():
                self.stdout.write(f"  {label}: {count}")
            self.stdout.write("")
            self.stdout.write("Safety notes")
            self.stdout.write("  - Operational tables were not copied.")
            self.stdout.write("  - CompanyTenant.routing_enabled remains False.")
            self.stdout.write("  - No public schema data was changed.")
            self.stdout.write("  - Run verify_tenant_tables before the next phase.")
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Tenant base seed applied."))
            return

        self.stdout.write("")
        self.stdout.write("Future apply notes")
        self.stdout.write("  - Preserve source primary keys for content types, permissions, users, and teams.")
        self.stdout.write("  - Use SET LOCAL search_path to the tenant schema during insert.")
        self.stdout.write("  - Keep CompanyTenant.routing_enabled=False after seed.")
        self.stdout.write("  - Run verify_tenant_tables before and after any future apply.")

        self.stdout.write("")
        self.stdout.write("Safety notes")
        self.stdout.write("  - DRY RUN ONLY: no database changes were made.")
        self.stdout.write("  - No data was inserted.")
        self.stdout.write("  - No table was created or altered.")
        self.stdout.write("  - No migration row was written.")
        self.stdout.write("  - Routing remains disabled.")

    def _get_tenant(self, company_code):
        try:
            return CompanyTenant.objects.select_related(
                "company_app",
                "company_app__representative_user",
            ).get(company_app__code=company_code)
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

    def _tenant_table_counts(self, schema_name, table_names):
        counts = {}
        with connection.cursor() as cursor:
            for table_name in table_names:
                if not self._table_exists(schema_name, table_name):
                    counts[table_name] = None
                    continue
                quoted_schema = connection.ops.quote_name(schema_name)
                quoted_table = connection.ops.quote_name(table_name)
                cursor.execute(f"SELECT COUNT(*) FROM {quoted_schema}.{quoted_table}")
                counts[table_name] = int(cursor.fetchone()[0])
        return counts

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

    def _content_type_plan(self, selected_apps):
        expected_models = self._expected_content_type_models(selected_apps)
        expected_keys = set(expected_models)
        public_rows = [
            row
            for row in ContentType.objects.values("id", "app_label", "model")
            if (row["app_label"], row["model"]) in expected_keys
        ]
        found_keys = {(row["app_label"], row["model"]) for row in public_rows}
        missing_keys = sorted(expected_keys - found_keys)
        return {
            "total_count": len(expected_keys),
            "copy_count": len(public_rows),
            "generate_count": len(missing_keys),
            "ids": [row["id"] for row in public_rows],
            "missing_keys": missing_keys,
            "missing_models": [expected_models[key] for key in missing_keys],
        }

    def _expected_content_type_models(self, selected_apps):
        model_by_key = {}
        for model in apps.get_models(include_auto_created=False):
            opts = model._meta
            if opts.app_label not in selected_apps:
                continue
            if opts.proxy or not opts.managed:
                continue
            if (opts.app_label, opts.object_name) in CENTRAL_ONLY_MODELS:
                continue
            if self._is_hardcoded_schema_table(opts.db_table):
                continue
            model_by_key[(opts.app_label, opts.model_name)] = model
        return model_by_key

    def _permission_plan(self, content_type_plan):
        permission_ids = list(
            Permission.objects.filter(content_type_id__in=content_type_plan["ids"]).values_list("id", flat=True)
        )
        generated_permissions = []
        for model in content_type_plan["missing_models"]:
            generated_permissions.extend(self._default_permissions_for_model(model))
        return {
            "total_count": len(permission_ids) + len(generated_permissions),
            "copy_count": len(permission_ids),
            "generate_count": len(generated_permissions),
            "ids": permission_ids,
            "generated": generated_permissions,
        }

    def _default_permissions_for_model(self, model):
        permissions = []
        for action in model._meta.default_permissions:
            codename = f"{action}_{model._meta.model_name}"
            permissions.append((codename, f"Can {action} {model._meta.verbose_name_raw}"))
        for codename, name in model._meta.permissions:
            permissions.append((codename, name))
        return permissions

    def _auth_group_plan(self, permission_ids):
        group_permission_model = Group.permissions.through
        return {
            "group_count": Group.objects.count(),
            "group_permission_count": group_permission_model.objects.filter(
                permission_id__in=permission_ids
            ).count(),
        }

    def _company_user_team_plan(self, tenant):
        company = tenant.company_app
        user_filter = Q(company_app=company.code)
        if company.representative_user_id:
            user_filter |= Q(pk=company.representative_user_id)
        users = list(User.objects.filter(user_filter).order_by("id"))
        teams = list(Team.objects.filter(company_app=company.code).order_by("id"))
        user_ids = {user.id for user in users}
        team_ids = {team.id for team in teams}
        user_group_model = User.groups.through
        user_permission_model = User.user_permissions.through

        return {
            "user_count": len(users),
            "team_count": len(teams),
            "roles": Counter(user.role for user in users),
            "sample_users": [user.username for user in users[:10]],
            "sample_teams": [f"{team.code}:{team.name}" for team in teams[:10]],
            "user_group_count": user_group_model.objects.filter(user_id__in=user_ids).count() if user_ids else 0,
            "user_permission_count": user_permission_model.objects.filter(user_id__in=user_ids).count() if user_ids else 0,
            "users_missing_team_seed": [
                user.username
                for user in users
                if user.team_id and user.team_id not in team_ids
            ],
            "teams_missing_leader_seed": [
                team.code
                for team in teams
                if team.leader_id and team.leader_id not in user_ids
            ],
            "representative_username": (
                company.representative_user.username
                if company.representative_user_id
                else ""
            ),
        }

    def _app_config_plan(self):
        return {
            "mobile_message_count": MobileAppMessageConfig.objects.count(),
            "point_item_count": PointItem.objects.count(),
        }

    def _build_warnings(self, tenant, tenant_table_counts, content_type_plan, company_plan):
        warnings = []
        populated = {
            table_name: count
            for table_name, count in tenant_table_counts.items()
            if count
        }
        if populated:
            warnings.append(
                "tenant reference tables already contain rows: "
                + ", ".join(f"{table}={count}" for table, count in sorted(populated.items()))
            )
        if content_type_plan["missing_keys"]:
            warnings.append("public schema is missing one or more expected content type rows.")
        if not company_plan["user_count"]:
            warnings.append("no public users found for this company.")
        if not company_plan["team_count"]:
            warnings.append("no public teams found for this company; default team seed policy is still needed.")
        if company_plan["users_missing_team_seed"]:
            warnings.append(
                "some selected users reference teams outside the selected company team seed: "
                + ", ".join(company_plan["users_missing_team_seed"][:10])
            )
        if company_plan["teams_missing_leader_seed"]:
            warnings.append(
                "some selected teams reference leaders outside the selected company user seed: "
                + ", ".join(company_plan["teams_missing_leader_seed"][:10])
            )
        if tenant.routing_enabled:
            warnings.append("routing is already enabled; do not seed through public-source copy blindly.")
        return warnings

    def _is_hardcoded_schema_table(self, table_name):
        return "." in table_name or '"' in table_name

    def _apply_seed(
        self,
        tenant,
        schema_name,
        tenant_table_counts,
        content_type_plan,
        permission_plan,
        company_plan,
        warnings,
        allow_core_company=False,
    ):
        self._validate_apply_allowed(
            tenant=tenant,
            tenant_table_counts=tenant_table_counts,
            company_plan=company_plan,
            warnings=warnings,
            allow_core_company=allow_core_company,
        )

        with transaction.atomic():
            with connection.cursor() as cursor:
                self._assert_reference_tables_still_empty(cursor, schema_name)
                content_type_ids, copied_content_types, generated_content_types = self._seed_content_types(
                    cursor=cursor,
                    schema_name=schema_name,
                    content_type_plan=content_type_plan,
                )
                copied_permissions, generated_permissions = self._seed_permissions(
                    cursor=cursor,
                    schema_name=schema_name,
                    permission_plan=permission_plan,
                    content_type_ids=content_type_ids,
                )
                group_count = self._copy_auth_groups(cursor, schema_name)
                group_permission_count = self._copy_auth_group_permissions(
                    cursor=cursor,
                    schema_name=schema_name,
                    permission_ids=copied_permissions + generated_permissions,
                )
                team_ids, user_ids, team_count, user_count = self._copy_company_teams_and_users(
                    cursor=cursor,
                    schema_name=schema_name,
                    tenant=tenant,
                )
                user_group_count = self._copy_user_groups(
                    cursor=cursor,
                    schema_name=schema_name,
                    user_ids=user_ids,
                )
                user_permission_count = self._copy_user_permissions(
                    cursor=cursor,
                    schema_name=schema_name,
                    user_ids=user_ids,
                    permission_ids=copied_permissions + generated_permissions,
                )
                mobile_message_count = self._copy_mobile_message_configs(cursor, schema_name)
                point_item_count = self._copy_point_items(
                    cursor=cursor,
                    schema_name=schema_name,
                    user_ids=user_ids,
                )
                self._reset_reference_sequences(cursor, schema_name)

        return {
            "content_types_copied": copied_content_types,
            "content_types_generated": generated_content_types,
            "permissions_copied": len(copied_permissions),
            "permissions_generated": len(generated_permissions),
            "groups": group_count,
            "group_permission_links": group_permission_count,
            "company_teams": team_count,
            "company_users": user_count,
            "user_group_links": user_group_count,
            "user_permission_links": user_permission_count,
            "mobile_app_message_configs": mobile_message_count,
            "point_catalog_items": point_item_count,
        }

    def _validate_apply_allowed(
        self,
        tenant,
        tenant_table_counts,
        company_plan,
        warnings,
        allow_core_company=False,
    ):
        if tenant.company_app.is_core_company and not allow_core_company:
            raise CommandError(
                "Refusing to seed a core company in this phase. "
                "Re-run with --allow-core-company only after dry-run review."
            )
        if tenant.routing_enabled:
            raise CommandError("Refusing seed apply while tenant routing is enabled.")

        missing_tables = [
            table_name
            for table_name, count in tenant_table_counts.items()
            if count is None
        ]
        if missing_tables:
            raise CommandError(
                "Refusing seed apply because tenant reference tables are missing: "
                + ", ".join(sorted(missing_tables))
            )

        populated_tables = [
            f"{table_name}={count}"
            for table_name, count in tenant_table_counts.items()
            if count
        ]
        if populated_tables:
            raise CommandError(
                "Refusing seed apply because tenant reference tables are not empty: "
                + ", ".join(sorted(populated_tables))
            )

        if not company_plan["user_count"]:
            raise CommandError("Refusing seed apply because no company users were selected.")
        if not company_plan["team_count"]:
            raise CommandError("Refusing seed apply because no company teams were selected.")
        if company_plan["users_missing_team_seed"]:
            raise CommandError(
                "Refusing seed apply because selected users reference teams outside the seed: "
                + ", ".join(company_plan["users_missing_team_seed"][:10])
            )
        if company_plan["teams_missing_leader_seed"]:
            raise CommandError(
                "Refusing seed apply because selected teams reference leaders outside the seed: "
                + ", ".join(company_plan["teams_missing_leader_seed"][:10])
            )

        blocking_warnings = [
            message
            for message in warnings
            if "tenant reference tables already contain rows" in message
        ]
        if blocking_warnings:
            raise CommandError("Refusing seed apply: " + blocking_warnings[0])

    def _assert_reference_tables_still_empty(self, cursor, schema_name):
        populated = []
        for table_name in REFERENCE_TABLES:
            quoted_table = self._qualified_table(schema_name, table_name)
            cursor.execute(f"SELECT COUNT(*) FROM {quoted_table}")
            count = int(cursor.fetchone()[0])
            if count:
                populated.append(f"{table_name}={count}")
        if populated:
            raise CommandError(
                "Tenant reference rows changed before apply could run: "
                + ", ".join(sorted(populated))
            )

    def _seed_content_types(self, cursor, schema_name, content_type_plan):
        public_rows = list(
            ContentType.objects.filter(id__in=content_type_plan["ids"])
            .order_by("id")
            .values("id", "app_label", "model")
        )
        rows = [dict(row) for row in public_rows]
        content_type_ids = {
            (row["app_label"], row["model"]): row["id"]
            for row in rows
        }

        next_id = self._next_explicit_id(cursor, schema_name, "django_content_type", ContentType)
        for model in sorted(
            content_type_plan["missing_models"],
            key=lambda item: (item._meta.app_label, item._meta.model_name),
        ):
            key = (model._meta.app_label, model._meta.model_name)
            content_type_ids[key] = next_id
            rows.append(
                {
                    "id": next_id,
                    "app_label": model._meta.app_label,
                    "model": model._meta.model_name,
                }
            )
            next_id += 1

        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name="django_content_type",
            columns=("id", "app_label", "model"),
            rows=rows,
        )
        return content_type_ids, len(public_rows), len(content_type_plan["missing_models"])

    def _seed_permissions(self, cursor, schema_name, permission_plan, content_type_ids):
        public_rows = list(
            Permission.objects.filter(id__in=permission_plan["ids"])
            .order_by("id")
            .values("id", "name", "content_type_id", "codename")
        )
        rows = [dict(row) for row in public_rows]
        copied_ids = [row["id"] for row in rows]
        generated_ids = []
        next_id = self._next_explicit_id(cursor, schema_name, "auth_permission", Permission)

        generated_models = self._models_for_generated_content_types(content_type_ids, permission_plan)
        for model in generated_models:
            content_type_id = content_type_ids[(model._meta.app_label, model._meta.model_name)]
            for codename, name in self._default_permissions_for_model(model):
                rows.append(
                    {
                        "id": next_id,
                        "name": str(name),
                        "content_type_id": content_type_id,
                        "codename": codename,
                    }
                )
                generated_ids.append(next_id)
                next_id += 1

        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name="auth_permission",
            columns=("id", "name", "content_type_id", "codename"),
            rows=rows,
        )
        return copied_ids, generated_ids

    def _models_for_generated_content_types(self, content_type_ids, permission_plan):
        generated = []
        generated_permission_count = 0
        for model in apps.get_models(include_auto_created=False):
            opts = model._meta
            key = (opts.app_label, opts.model_name)
            if key not in content_type_ids:
                continue
            if opts.proxy or not opts.managed:
                continue
            if (opts.app_label, opts.object_name) in CENTRAL_ONLY_MODELS:
                continue
            if self._is_hardcoded_schema_table(opts.db_table):
                continue
            public_exists = ContentType.objects.filter(app_label=opts.app_label, model=opts.model_name).exists()
            if public_exists:
                continue
            generated.append(model)
            generated_permission_count += len(self._default_permissions_for_model(model))

        if generated_permission_count != permission_plan["generate_count"]:
            raise CommandError(
                "Generated permission count changed during apply. "
                f"planned={permission_plan['generate_count']} actual={generated_permission_count}"
            )
        return sorted(generated, key=lambda model: (model._meta.app_label, model._meta.model_name))

    def _copy_auth_groups(self, cursor, schema_name):
        return self._copy_table_rows_from_public(
            cursor=cursor,
            schema_name=schema_name,
            table_name=Group._meta.db_table,
            columns=self._model_columns(Group),
        )

    def _copy_auth_group_permissions(self, cursor, schema_name, permission_ids):
        if not permission_ids:
            return 0
        through_model = Group.permissions.through
        return self._copy_table_rows_from_public(
            cursor=cursor,
            schema_name=schema_name,
            table_name=through_model._meta.db_table,
            columns=self._model_columns(through_model),
            where_sql="WHERE permission_id = ANY(%s)",
            params=[permission_ids],
        )

    def _copy_company_teams_and_users(self, cursor, schema_name, tenant):
        company = tenant.company_app
        user_filter = Q(company_app=company.code)
        if company.representative_user_id:
            user_filter |= Q(pk=company.representative_user_id)
        teams = list(Team.objects.filter(company_app=company.code).order_by("id"))
        users = list(User.objects.filter(user_filter).order_by("id"))
        team_ids = [team.id for team in teams]
        user_ids = [user.id for user in users]

        team_rows = []
        for team in teams:
            row = self._model_instance_row(Team, team)
            row["leader_id"] = None
            team_rows.append(row)
        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name=Team._meta.db_table,
            columns=self._model_columns(Team),
            rows=team_rows,
        )

        user_rows = [self._model_instance_row(User, user) for user in users]
        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name=User._meta.db_table,
            columns=self._model_columns(User),
            rows=user_rows,
        )

        for team in teams:
            if not team.leader_id:
                continue
            cursor.execute(
                f"UPDATE {self._qualified_table(schema_name, Team._meta.db_table)} "
                "SET leader_id = %s WHERE id = %s",
                [team.leader_id, team.id],
            )

        return team_ids, user_ids, len(team_rows), len(user_rows)

    def _copy_user_groups(self, cursor, schema_name, user_ids):
        if not user_ids:
            return 0
        through_model = User.groups.through
        return self._copy_table_rows_from_public(
            cursor=cursor,
            schema_name=schema_name,
            table_name=through_model._meta.db_table,
            columns=self._model_columns(through_model),
            where_sql="WHERE user_id = ANY(%s)",
            params=[user_ids],
        )

    def _copy_user_permissions(self, cursor, schema_name, user_ids, permission_ids):
        if not user_ids or not permission_ids:
            return 0
        through_model = User.user_permissions.through
        return self._copy_table_rows_from_public(
            cursor=cursor,
            schema_name=schema_name,
            table_name=through_model._meta.db_table,
            columns=self._model_columns(through_model),
            where_sql="WHERE user_id = ANY(%s) AND permission_id = ANY(%s)",
            params=[user_ids, permission_ids],
        )

    def _copy_mobile_message_configs(self, cursor, schema_name):
        rows = [
            self._model_instance_row(MobileAppMessageConfig, instance)
            for instance in MobileAppMessageConfig.objects.order_by("id")
        ]
        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name=MobileAppMessageConfig._meta.db_table,
            columns=self._model_columns(MobileAppMessageConfig),
            rows=rows,
        )
        return len(rows)

    def _copy_point_items(self, cursor, schema_name, user_ids):
        allowed_user_ids = set(user_ids)
        rows = []
        for instance in PointItem.objects.order_by("id"):
            row = self._model_instance_row(PointItem, instance)
            if row.get("created_by_id") not in allowed_user_ids:
                row["created_by_id"] = None
            if row.get("updated_by_id") not in allowed_user_ids:
                row["updated_by_id"] = None
            rows.append(row)
        self._insert_rows(
            cursor=cursor,
            schema_name=schema_name,
            table_name=PointItem._meta.db_table,
            columns=self._model_columns(PointItem),
            rows=rows,
        )
        return len(rows)

    def _model_columns(self, model):
        return tuple(field.column for field in model._meta.local_fields)

    def _model_instance_row(self, model, instance):
        row = {}
        for field in model._meta.local_fields:
            value = getattr(instance, field.attname)
            row[field.column] = field.get_db_prep_save(value, connection)
        return row

    def _copy_table_rows_from_public(
        self,
        cursor,
        schema_name,
        table_name,
        columns,
        where_sql="",
        params=None,
    ):
        params = params or []
        quoted_columns = ", ".join(connection.ops.quote_name(column) for column in columns)
        target = self._qualified_table(schema_name, table_name)
        source = self._qualified_table("public", table_name)
        sql = f"INSERT INTO {target} ({quoted_columns}) SELECT {quoted_columns} FROM {source} {where_sql}"
        cursor.execute(sql, params)
        return cursor.rowcount

    def _insert_rows(self, cursor, schema_name, table_name, columns, rows):
        if not rows:
            return
        quoted_columns = ", ".join(connection.ops.quote_name(column) for column in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        target = self._qualified_table(schema_name, table_name)
        sql = f"INSERT INTO {target} ({quoted_columns}) VALUES ({placeholders})"
        cursor.executemany(sql, [[row[column] for column in columns] for row in rows])

    def _next_explicit_id(self, cursor, schema_name, table_name, model):
        public_max = model.objects.order_by("-id").values_list("id", flat=True).first() or 0
        tenant_max = self._max_id(cursor, schema_name, table_name)
        return max(int(public_max), int(tenant_max)) + 1

    def _max_id(self, cursor, schema_name, table_name):
        cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {self._qualified_table(schema_name, table_name)}")
        return int(cursor.fetchone()[0])

    def _reset_reference_sequences(self, cursor, schema_name):
        for table_name in REFERENCE_TABLES:
            self._reset_sequence(cursor, schema_name, table_name)

    def _reset_sequence(self, cursor, schema_name, table_name):
        qualified_name = f"{schema_name}.{table_name}"
        cursor.execute("SELECT pg_get_serial_sequence(%s, 'id')", [qualified_name])
        sequence_name = cursor.fetchone()[0]
        if not sequence_name:
            return
        max_id = self._max_id(cursor, schema_name, table_name)
        if not max_id:
            return
        cursor.execute("SELECT setval(%s, %s, true)", [sequence_name, max_id])

    def _qualified_table(self, schema_name, table_name):
        return f"{connection.ops.quote_name(schema_name)}.{connection.ops.quote_name(table_name)}"
