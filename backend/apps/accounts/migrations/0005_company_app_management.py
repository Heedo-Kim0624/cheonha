from django.conf import settings
from django.db import migrations, models
import apps.accounts.models
import django.db.models.deletion


def seed_company_apps(apps, schema_editor):
    CompanyApp = apps.get_model("accounts", "CompanyApp")
    User = apps.get_model("accounts", "User")

    CompanyApp.objects.update_or_create(
        code="cheonha",
        defaults={
            "name": "천하운수",
            "status": "ACTIVE",
            "enabled_tabs": [
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
    CompanyApp.objects.update_or_create(
        code="abc",
        defaults={
            "name": "ABC",
            "status": "ACTIVE",
            "enabled_tabs": [
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

    for user in User.objects.filter(team__isnull=False).select_related("team"):
        user.company_app = user.team.company_app
        user.save(update_fields=["company_app"])
    User.objects.filter(username="admin2").update(company_app="abc")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_team_yongcha_round_prices"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyApp",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(db_index=True, max_length=40, unique=True)),
                ("name", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("INVITED", "Invited"),
                            ("PENDING_APPROVAL", "Pending approval"),
                            ("ACTIVE", "Active"),
                            ("REJECTED", "Rejected"),
                            ("DELETED", "Deleted"),
                        ],
                        db_index=True,
                        default="INVITED",
                        max_length=24,
                    ),
                ),
                ("enabled_tabs", models.JSONField(blank=True, default=apps.accounts.models.default_company_tabs)),
                ("signup_token", models.CharField(db_index=True, default=apps.accounts.models.new_company_signup_token, max_length=64, unique=True)),
                ("invited_at", models.DateTimeField(auto_now_add=True)),
                ("signup_submitted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("delete_retention_until", models.DateTimeField(blank=True, null=True)),
                ("restored_at", models.DateTimeField(blank=True, null=True)),
                ("terms_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("privacy_policy_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("location_terms_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("data_processing_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("marketing_agreed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_company_apps", to=settings.AUTH_USER_MODEL)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_company_apps", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="deleted_company_apps", to=settings.AUTH_USER_MODEL)),
                ("rejected_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rejected_company_apps", to=settings.AUTH_USER_MODEL)),
                ("representative_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="representative_company_apps", to=settings.AUTH_USER_MODEL)),
                ("restored_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="restored_company_apps", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name", "code"],
            },
        ),
        migrations.AddField(
            model_name="user",
            name="company_app",
            field=models.CharField(db_index=True, default="cheonha", max_length=40, verbose_name="Company app code"),
        ),
        migrations.AlterField(
            model_name="team",
            name="company_app",
            field=models.CharField(db_index=True, default="cheonha", max_length=40, verbose_name="회사 앱 코드"),
        ),
        migrations.RunPython(seed_company_apps, migrations.RunPython.noop),
    ]
