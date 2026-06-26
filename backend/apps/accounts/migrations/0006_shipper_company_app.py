from django.db import migrations, models
import apps.accounts.models


def seed_shippers(apps, schema_editor):
    Shipper = apps.get_model("accounts", "Shipper")
    CompanyApp = apps.get_model("accounts", "CompanyApp")
    Team = apps.get_model("accounts", "Team")

    shippers = [
        {
            "code": "kurly",
            "name": "\uceec\ub9ac",
            "upload_type": "FILE",
            "upload_profile": "kurly",
            "operation_report_profile": "kurly",
            "settlement_profile": "kurly",
            "sort_order": 10,
        },
        {
            "code": "coupang",
            "name": "\ucfe0\ud321",
            "upload_type": "TEXT",
            "upload_profile": "coupang_text",
            "operation_report_profile": "generic",
            "settlement_profile": "generic",
            "sort_order": 20,
        },
        {
            "code": "one",
            "name": "\uc624\ub124",
            "upload_type": "FILE",
            "upload_profile": "generic",
            "operation_report_profile": "generic",
            "settlement_profile": "generic",
            "sort_order": 30,
        },
    ]
    for row in shippers:
        Shipper.objects.update_or_create(
            code=row["code"],
            defaults={
                **row,
                "status": "ACTIVE",
                "default_enabled_tabs": ["dispatch", "crew", "region"],
                "available_tabs": [
                    "dispatch",
                    "crew",
                    "region",
                    "dashboard",
                    "operations",
                    "settlement",
                    "inquiry",
                    "tracking",
                    "manpower",
                ],
            },
        )

    for company in CompanyApp.objects.all():
        enabled = company.enabled_shippers or []
        if not enabled:
            company.enabled_shippers = ["kurly"]
            company.save(update_fields=["enabled_shippers", "updated_at"])

    Team.objects.filter(shipper_code="").update(shipper_code="kurly")


def _table_names(connection):
    return set(connection.introspection.table_names())


def _column_names(connection, table_name):
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }


def _add_column_if_missing(schema_editor, table_name, column_name, definition):
    connection = schema_editor.connection
    if table_name not in _table_names(connection):
        return
    if column_name in _column_names(connection, table_name):
        return
    schema_editor.execute(
        f"ALTER TABLE {connection.ops.quote_name(table_name)} "
        f"ADD COLUMN {connection.ops.quote_name(column_name)} {definition}"
    )


def _create_index_if_missing(schema_editor, table_name, index_name, columns, unique=False):
    connection = schema_editor.connection
    if table_name not in _table_names(connection):
        return
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_class WHERE relkind IN ('i', 'I') AND relname = %s",
                [index_name],
            )
            if cursor.fetchone():
                return
        mode = "UNIQUE " if unique else ""
        cols = ", ".join(connection.ops.quote_name(column) for column in columns)
        schema_editor.execute(
            f"CREATE {mode}INDEX CONCURRENTLY {index_name} "
            f"ON {connection.ops.quote_name(table_name)} ({cols})"
        )
        return

    mode = "UNIQUE " if unique else ""
    cols = ", ".join(connection.ops.quote_name(column) for column in columns)
    schema_editor.execute(
        f"CREATE {mode}INDEX IF NOT EXISTS {connection.ops.quote_name(index_name)} "
        f"ON {connection.ops.quote_name(table_name)} ({cols})"
    )


def _drop_old_settlement_unique(schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql" or "settlement_settlement" not in _table_names(connection):
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'settlement_settlement'
              AND c.contype = 'u'
            """
        )
        rows = cursor.fetchall()
    for constraint_name, definition in rows:
        normalized = str(definition or "").replace('"', "").lower()
        if (
            "team_id" in normalized
            and "period_start" in normalized
            and "period_end" in normalized
            and "shipper_code" not in normalized
        ):
            schema_editor.execute(
                f"ALTER TABLE settlement_settlement DROP CONSTRAINT {connection.ops.quote_name(constraint_name)}"
            )


def _add_postgres_settlement_unique(schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql" or "settlement_settlement" not in _table_names(connection):
        return
    constraint_name = "settlement_team_shipper_period_uniq"
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_constraint WHERE conname = %s", [constraint_name])
        if cursor.fetchone():
            return
    schema_editor.execute(
        """
        ALTER TABLE settlement_settlement
        ADD CONSTRAINT settlement_team_shipper_period_uniq
        UNIQUE (team_id, shipper_code, period_start, period_end)
        """
    )


def patch_legacy_dispatch_settlement_tables(apps, schema_editor):
    # dispatch and settlement are currently synchronized as unmigrated apps.
    # Existing production tables therefore need a direct, idempotent patch.
    _add_column_if_missing(schema_editor, "dispatch_dispatchupload", "shipper_code", "varchar(40) NOT NULL DEFAULT 'kurly'")
    _add_column_if_missing(schema_editor, "dispatch_dispatchupload", "input_type", "varchar(16) NOT NULL DEFAULT 'FILE'")
    _add_column_if_missing(schema_editor, "dispatch_dispatchupload", "raw_text", "text NOT NULL DEFAULT ''")
    _add_column_if_missing(schema_editor, "settlement_settlement", "shipper_code", "varchar(40) NOT NULL DEFAULT 'kurly'")
    _add_column_if_missing(schema_editor, "settlement_settlementdetail", "shipper_code", "varchar(40) NOT NULL DEFAULT 'kurly'")

    connection = schema_editor.connection
    if "dispatch_dispatchupload" in _table_names(connection):
        schema_editor.execute("UPDATE dispatch_dispatchupload SET shipper_code = 'kurly' WHERE shipper_code IS NULL OR shipper_code = ''")
        schema_editor.execute("UPDATE dispatch_dispatchupload SET input_type = 'FILE' WHERE input_type IS NULL OR input_type = ''")
        schema_editor.execute("UPDATE dispatch_dispatchupload SET raw_text = '' WHERE raw_text IS NULL")
    if "settlement_settlement" in _table_names(connection):
        schema_editor.execute("UPDATE settlement_settlement SET shipper_code = 'kurly' WHERE shipper_code IS NULL OR shipper_code = ''")
    if "settlement_settlementdetail" in _table_names(connection):
        schema_editor.execute("UPDATE settlement_settlementdetail SET shipper_code = 'kurly' WHERE shipper_code IS NULL OR shipper_code = ''")

    _drop_old_settlement_unique(schema_editor)
    _add_postgres_settlement_unique(schema_editor)
    _create_index_if_missing(schema_editor, "dispatch_dispatchupload", "dispatch_upload_shipper_code_idx", ["shipper_code"])
    _create_index_if_missing(schema_editor, "settlement_settlement", "settlement_shipper_code_idx", ["shipper_code"])
    _create_index_if_missing(schema_editor, "settlement_settlementdetail", "settlement_detail_shipper_code_idx", ["shipper_code"])
    if connection.vendor != "postgresql":
        _create_index_if_missing(
            schema_editor,
            "settlement_settlement",
            "settlement_team_shipper_period_uniq",
            ["team_id", "shipper_code", "period_start", "period_end"],
            unique=True,
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("accounts", "0005_company_app_management"),
    ]

    operations = [
        migrations.CreateModel(
            name="Shipper",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=40, unique=True)),
                ("name", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        db_index=True,
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                (
                    "upload_type",
                    models.CharField(
                        choices=[("FILE", "File"), ("TEXT", "Text")],
                        default="FILE",
                        max_length=16,
                    ),
                ),
                ("upload_profile", models.CharField(default="kurly", max_length=40)),
                ("operation_report_profile", models.CharField(default="kurly", max_length=40)),
                ("settlement_profile", models.CharField(default="kurly", max_length=40)),
                ("default_enabled_tabs", models.JSONField(blank=True, default=apps.accounts.models.default_company_tabs)),
                ("available_tabs", models.JSONField(blank=True, default=apps.accounts.models.default_shipper_available_tabs)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name", "code"],
            },
        ),
        migrations.AddField(
            model_name="companyapp",
            name="enabled_shippers",
            field=models.JSONField(blank=True, default=apps.accounts.models.default_enabled_shippers),
        ),
        migrations.AddField(
            model_name="team",
            name="shipper_code",
            field=models.CharField(db_index=True, default="kurly", max_length=40, verbose_name="Shipper code"),
        ),
        migrations.RunPython(seed_shippers, migrations.RunPython.noop),
        migrations.RunPython(patch_legacy_dispatch_settlement_tables, migrations.RunPython.noop),
    ]
