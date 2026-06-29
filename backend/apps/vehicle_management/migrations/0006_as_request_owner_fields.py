from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vehicle_management", "0005_calendar_company_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="asrequest",
            name="owner_name",
            field=models.CharField(
                "차량 소유자",
                max_length=32,
                blank=True,
                default="",
            ),
        ),
        migrations.AddField(
            model_name="asrequest",
            name="owner_phone",
            field=models.CharField(
                "운영 차주 전화번호",
                max_length=20,
                blank=True,
                default="",
            ),
        ),
    ]
