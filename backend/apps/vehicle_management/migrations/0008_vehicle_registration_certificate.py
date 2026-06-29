from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vehicle_management", "0007_return_request_photos_and_reject_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="registration_certificate",
            field=models.FileField(
                "자동차등록증",
                blank=True,
                default="",
                upload_to="vehicle_registrations/%Y/%m/%d/",
            ),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="registration_certificate_uploaded_at",
            field=models.DateTimeField(
                "자동차등록증 업로드 시각",
                blank=True,
                null=True,
            ),
        ),
    ]
