from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("vehicle_management", "0008_vehicle_registration_certificate"),
    ]

    operations = [
        migrations.CreateModel(
            name="FleetSubscriptionContract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(db_index=True, max_length=32)),
                ("customer", models.CharField(max_length=128)),
                ("contact", models.CharField(blank=True, default="", max_length=64)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(db_index=True)),
                ("monthly_fee", models.PositiveIntegerField(default=0)),
                ("deposit", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(db_index=True, default="구독중", max_length=32)),
                ("sign_status", models.CharField(default="서명완료", max_length=32)),
                ("contract_file", models.FileField(blank=True, default="", upload_to="vehicle_contracts/%Y/%m/%d/")),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fleet_subscription_contracts", to="vehicle_management.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fleet_subscription_contracts", to="vehicle_management.vehicle")),
            ],
            options={
                "db_table": 'vehicle_mgmt"."fleet_subscription_contract',
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FleetReturnRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(db_index=True, max_length=32)),
                ("customer", models.CharField(blank=True, default="", max_length=128)),
                ("scheduled_at", models.DateTimeField(db_index=True)),
                ("actual_at", models.DateTimeField(blank=True, null=True)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("status", models.CharField(db_index=True, default="반납예정", max_length=32)),
                ("photos", models.JSONField(blank=True, default=list)),
                ("checks", models.JSONField(blank=True, default=list)),
                ("note", models.TextField(blank=True, default="")),
                ("repairs", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fleet_return_records", to="vehicle_management.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("subscription", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="return_records", to="vehicle_management.fleetsubscriptioncontract")),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fleet_return_records", to="vehicle_management.vehicle")),
            ],
            options={
                "db_table": 'vehicle_mgmt"."fleet_return_record',
                "ordering": ["-scheduled_at"],
            },
        ),
        migrations.CreateModel(
            name="FleetInsurancePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(db_index=True, max_length=32)),
                ("insurer", models.CharField(max_length=128)),
                ("policy_no", models.CharField(db_index=True, max_length=128)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(db_index=True)),
                ("previous_rate", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("current_rate", models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ("status", models.CharField(db_index=True, default="가입중", max_length=32)),
                ("payments", models.JSONField(blank=True, default=list)),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fleet_insurance_policies", to="vehicle_management.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fleet_insurance_policies", to="vehicle_management.vehicle")),
            ],
            options={
                "db_table": 'vehicle_mgmt"."fleet_insurance_policy',
                "ordering": ["end_date", "id"],
            },
        ),
        migrations.CreateModel(
            name="FleetAccidentCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(db_index=True, max_length=32)),
                ("vehicle_vin", models.CharField(blank=True, default="", max_length=32)),
                ("driver", models.CharField(blank=True, default="", max_length=64)),
                ("accident_at", models.DateTimeField(db_index=True)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("coverage", models.CharField(blank=True, default="", max_length=128)),
                ("victim", models.CharField(blank=True, default="", max_length=128)),
                ("compensation", models.IntegerField(default=0)),
                ("paid", models.IntegerField(default=0)),
                ("manager", models.CharField(blank=True, default="", max_length=64)),
                ("status", models.CharField(db_index=True, default="진행중", max_length=32)),
                ("items", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fleet_accident_cases", to="vehicle_management.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fleet_accident_cases", to="vehicle_management.vehicle")),
            ],
            options={
                "db_table": 'vehicle_mgmt"."fleet_accident_case',
                "ordering": ["-accident_at"],
            },
        ),
        migrations.AddIndex(
            model_name="fleetsubscriptioncontract",
            index=models.Index(fields=["company", "status"], name="vehicle_mgm_company_d977ce_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetsubscriptioncontract",
            index=models.Index(fields=["company", "vehicle_number"], name="vehicle_mgm_company_33a51d_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetreturnrecord",
            index=models.Index(fields=["company", "status"], name="vehicle_mgm_company_e8f9ef_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetreturnrecord",
            index=models.Index(fields=["company", "vehicle_number"], name="vehicle_mgm_company_9ad4c5_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetinsurancepolicy",
            index=models.Index(fields=["company", "status"], name="vehicle_mgm_company_4d8ba6_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetinsurancepolicy",
            index=models.Index(fields=["company", "vehicle_number"], name="vehicle_mgm_company_99af27_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetaccidentcase",
            index=models.Index(fields=["company", "status"], name="vehicle_mgm_company_32e3ea_idx"),
        ),
        migrations.AddIndex(
            model_name="fleetaccidentcase",
            index=models.Index(fields=["company", "vehicle_number"], name="vehicle_mgm_company_f51e92_idx"),
        ),
    ]
