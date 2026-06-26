from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobile", "0005_mobileappuser_location_terms_agreed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileappuser",
            name="marketing_event_agreed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="마케팅 및 이벤트 정보 수신 동의 시각",
            ),
        ),
    ]
