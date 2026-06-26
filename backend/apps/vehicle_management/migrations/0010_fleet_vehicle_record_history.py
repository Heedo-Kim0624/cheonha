from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("vehicle_management", "0009_fleet_management_site_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="FleetVehicleRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(db_index=True, max_length=32)),
                ("vin", models.CharField(db_index=True, max_length=32)),
                ("model", models.CharField(blank=True, default="", max_length=64)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(db_index=True, default="운행중", max_length=32)),
                ("certificate_name", models.CharField(blank=True, default="", max_length=255)),
                ("certificate_uploaded_at", models.DateField(blank=True, null=True)),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fleet_vehicle_records", to="vehicle_management.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fleet_records", to="vehicle_management.vehicle")),
            ],
            options={
                "db_table": 'vehicle_mgmt"."fleet_vehicle_record',
                "ordering": ["vehicle_number", "start_date", "id"],
                "indexes": [
                    models.Index(fields=["company", "vehicle_number"], name="vehicle_mgm_company_b476bd_idx"),
                    models.Index(fields=["company", "status"], name="vehicle_mgm_company_027cf6_idx"),
                    models.Index(fields=["vehicle", "start_date"], name="vehicle_mgm_vehicle_f65d9e_idx"),
                ],
            },
        ),
        migrations.AddField(
            model_name="fleetsubscriptioncontract",
            name="vehicle_record",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="subscription_contracts", to="vehicle_management.fleetvehiclerecord"),
        ),
        migrations.AddField(
            model_name="fleetreturnrecord",
            name="vehicle_record",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="return_records", to="vehicle_management.fleetvehiclerecord"),
        ),
        migrations.AddField(
            model_name="fleetinsurancepolicy",
            name="vehicle_record",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="insurance_policies", to="vehicle_management.fleetvehiclerecord"),
        ),
        migrations.AddField(
            model_name="fleetaccidentcase",
            name="vehicle_record",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accident_cases", to="vehicle_management.fleetvehiclerecord"),
        ),
    ]
