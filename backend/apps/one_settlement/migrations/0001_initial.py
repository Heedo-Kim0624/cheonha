from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_one_shipper(apps, schema_editor):
    Shipper = apps.get_model("accounts", "Shipper")
    CompanyApp = apps.get_model("accounts", "CompanyApp")

    Shipper.objects.update_or_create(
        code="one",
        defaults={
            "name": "오네",
            "status": "ACTIVE",
            "upload_type": "FILE",
            "upload_profile": "one",
            "operation_report_profile": "generic",
            "settlement_profile": "one",
            "default_enabled_tabs": ["settlement"],
            "available_tabs": ["settlement"],
            "sort_order": 30,
        },
    )

    companies = list(CompanyApp.objects.filter(code="new"))
    if not companies:
        companies = list(CompanyApp.objects.filter(name="새회사"))
    for company in companies:
        enabled_shippers = list(company.enabled_shippers or [])
        if "one" not in enabled_shippers:
            enabled_shippers.append("one")
        enabled_tabs = list(company.enabled_tabs or [])
        if "settlement" not in enabled_tabs:
            enabled_tabs.append("settlement")
        company.enabled_shippers = enabled_shippers
        company.enabled_tabs = enabled_tabs
        company.save(update_fields=["enabled_shippers", "enabled_tabs", "updated_at"])


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0008_shipper_box_rate_adjustment"),
    ]

    operations = [
        migrations.CreateModel(
            name="OneDriver",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_app", models.CharField(db_index=True, max_length=40)),
                ("name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="OneSettlementUpload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_app", models.CharField(db_index=True, max_length=40)),
                ("shipper_code", models.CharField(db_index=True, default="one", max_length=40)),
                ("month", models.CharField(db_index=True, max_length=7)),
                ("delivery_date", models.DateField(blank=True, db_index=True, null=True)),
                ("file", models.FileField(upload_to="one/%Y/%m/%d/")),
                ("original_filename", models.CharField(blank=True, default="", max_length=500)),
                ("raw_hash", models.CharField(db_index=True, max_length=64)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("order_count", models.PositiveIntegerField(default=0)),
                ("mapped_order_count", models.PositiveIntegerField(default=0)),
                ("unmapped_order_count", models.PositiveIntegerField(default=0)),
                ("total_amount", models.DecimalField(decimal_places=0, default=0, max_digits=14)),
                ("validation_errors", models.JSONField(blank=True, default=list)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("IMPORTED", "Imported"),
                            ("NEEDS_REVIEW", "Needs review"),
                            ("ERROR", "Error"),
                        ],
                        db_index=True,
                        default="IMPORTED",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="one_settlement_uploads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-delivery_date", "-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="OneShipmentOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_app", models.CharField(db_index=True, max_length=40)),
                ("shipper_code", models.CharField(db_index=True, default="one", max_length=40)),
                ("month", models.CharField(db_index=True, max_length=7)),
                ("delivery_date", models.DateField(db_index=True)),
                ("driver_name", models.CharField(db_index=True, max_length=100)),
                ("order_number", models.CharField(db_index=True, max_length=80)),
                ("fee_name", models.CharField(db_index=True, max_length=200)),
                ("service_code", models.CharField(blank=True, db_index=True, default="", max_length=40)),
                ("category_code", models.CharField(blank=True, db_index=True, default="", max_length=40)),
                ("city", models.CharField(blank=True, default="", max_length=100)),
                ("boxes", models.PositiveIntegerField(default=0)),
                ("extra_boxes", models.PositiveIntegerField(default=0)),
                ("amount", models.DecimalField(decimal_places=0, default=0, max_digits=14)),
                ("base_amount", models.DecimalField(decimal_places=0, default=0, max_digits=14)),
                ("jongno_extra_amount", models.DecimalField(decimal_places=0, default=0, max_digits=14)),
                ("is_mapped", models.BooleanField(db_index=True, default=False)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shipment_orders",
                        to="one_settlement.onedriver",
                    ),
                ),
                (
                    "upload",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orders",
                        to="one_settlement.onesettlementupload",
                    ),
                ),
            ],
            options={
                "ordering": ["delivery_date", "driver_name", "fee_name", "order_number"],
            },
        ),
        migrations.CreateModel(
            name="OneDriverStatementOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company_app", models.CharField(db_index=True, max_length=40)),
                ("shipper_code", models.CharField(db_index=True, default="one", max_length=40)),
                ("month", models.CharField(db_index=True, max_length=7)),
                ("payment_due_date", models.DateField(blank=True, null=True)),
                ("manual_items", models.JSONField(blank=True, default=list)),
                ("memo", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statement_overrides",
                        to="one_settlement.onedriver",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="one_statement_overrides",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-month", "driver__name"],
            },
        ),
        migrations.AddConstraint(
            model_name="onedriver",
            constraint=models.UniqueConstraint(fields=("company_app", "name"), name="one_driver_company_name_uniq"),
        ),
        migrations.AddIndex(
            model_name="onedriver",
            index=models.Index(fields=["company_app", "name"], name="one_driver_company_name_idx"),
        ),
        migrations.AddConstraint(
            model_name="onesettlementupload",
            constraint=models.UniqueConstraint(
                fields=("company_app", "shipper_code", "raw_hash"),
                name="one_upload_company_shipper_raw_hash_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="onesettlementupload",
            index=models.Index(fields=["company_app", "shipper_code", "month"], name="one_upload_company_month_idx"),
        ),
        migrations.AddIndex(
            model_name="onesettlementupload",
            index=models.Index(fields=["company_app", "shipper_code", "delivery_date"], name="one_upload_company_date_idx"),
        ),
        migrations.AddIndex(
            model_name="oneshipmentorder",
            index=models.Index(fields=["company_app", "shipper_code", "month", "driver"], name="one_order_driver_month_idx"),
        ),
        migrations.AddIndex(
            model_name="oneshipmentorder",
            index=models.Index(fields=["company_app", "shipper_code", "delivery_date"], name="one_order_company_date_idx"),
        ),
        migrations.AddIndex(
            model_name="oneshipmentorder",
            index=models.Index(fields=["service_code", "category_code"], name="one_order_service_category_idx"),
        ),
        migrations.AddConstraint(
            model_name="onedriverstatementoverride",
            constraint=models.UniqueConstraint(
                fields=("company_app", "shipper_code", "month", "driver"),
                name="one_statement_override_uniq",
            ),
        ),
        migrations.RunPython(seed_one_shipper, migrations.RunPython.noop),
    ]

