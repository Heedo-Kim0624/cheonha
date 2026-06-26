from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("vehicle_management", "0006_as_request_owner_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionrequest",
            name="reject_reason",
            field=models.TextField("거절 사유", blank=True, default=""),
        ),
        migrations.CreateModel(
            name="ReturnRequestPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        "사진 구분",
                        choices=[
                            ("FRONT", "전면"),
                            ("REAR", "후면"),
                            ("LEFT", "좌측"),
                            ("RIGHT", "우측"),
                            ("DASHBOARD", "내부 대시보드"),
                        ],
                        max_length=16,
                    ),
                ),
                ("image", models.FileField("사진 파일", upload_to="vehicle_returns/%Y/%m/%d/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="vehicle_management.returnrequest",
                    ),
                ),
            ],
            options={
                "db_table": 'vehicle_mgmt_return_request_photo',
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("request", "kind"),
                        name="vm_return_request_photo_kind_unique",
                    )
                ],
            },
        ),
    ]
