from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mobile", "0006_mobileappuser_marketing_event_agreed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobileappuser",
            name="last_app_version",
            field=models.CharField(blank=True, max_length=40, verbose_name="앱 버전"),
        ),
    ]
