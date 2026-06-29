from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crew", "0005_yongcha_pay_group_multi_round_policy"),
        ("mobile", "0008_legal_document_logs_and_consent_history"),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileWorkSessionCheckpoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_number", models.CharField(blank=True, max_length=20)),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("csv_path", models.CharField(blank=True, max_length=500)),
                ("sample_count", models.PositiveIntegerField(default=0)),
                ("csv_bytes", models.PositiveIntegerField(default=0)),
                ("app_version", models.CharField(blank=True, max_length=40)),
                ("background_location_granted", models.BooleanField(default=False)),
                ("last_synced_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "crew_member",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mobile_work_session_checkpoint",
                        to="crew.crewmember",
                    ),
                ),
            ],
            options={
                "db_table": "mobile_work_session_checkpoints",
                "verbose_name": "모바일 근무 세션 임시 저장",
                "verbose_name_plural": "모바일 근무 세션 임시 저장",
                "ordering": ["-last_synced_at"],
            },
        ),
    ]
