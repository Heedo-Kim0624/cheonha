from django.db import migrations, models
import django.db.models.deletion


def tenant_schema_name(company_code):
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(company_code or "").lower())
    safe = (safe or "company")[:56]
    return f"tenant_{safe}"


def seed_company_tenants(apps, schema_editor):
    CompanyApp = apps.get_model("accounts", "CompanyApp")
    CompanyTenant = apps.get_model("accounts", "CompanyTenant")

    for company in CompanyApp.objects.all():
        CompanyTenant.objects.get_or_create(
            company_app=company,
            defaults={
                "schema_name": tenant_schema_name(company.code),
                "status": "PLANNED",
                "routing_enabled": False,
                "notes": "Seeded for future tenant schema separation. Routing is disabled.",
            },
        )


def unseed_company_tenants(apps, schema_editor):
    CompanyTenant = apps.get_model("accounts", "CompanyTenant")
    CompanyTenant.objects.filter(routing_enabled=False, status="PLANNED").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_shipper_company_app"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyTenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("schema_name", models.CharField(db_index=True, max_length=63, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PLANNED", "Planned"),
                            ("READY", "Ready"),
                            ("ACTIVE", "Active"),
                            ("ERROR", "Error"),
                            ("DISABLED", "Disabled"),
                        ],
                        db_index=True,
                        default="PLANNED",
                        max_length=16,
                    ),
                ),
                ("routing_enabled", models.BooleanField(db_index=True, default=False)),
                ("last_migrated_at", models.DateTimeField(blank=True, null=True)),
                ("last_verified_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company_app",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tenant",
                        to="accounts.companyapp",
                    ),
                ),
            ],
            options={
                "ordering": ["company_app__code"],
            },
        ),
        migrations.RunPython(seed_company_tenants, unseed_company_tenants),
    ]
