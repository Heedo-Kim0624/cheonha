from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0003_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="trackingsession",
            name="app_version",
            field=models.CharField(blank=True, max_length=40, verbose_name="앱 버전"),
        ),
        migrations.AddField(
            model_name="liveworksessionstatus",
            name="last_app_version",
            field=models.CharField(blank=True, max_length=40, verbose_name="앱 버전"),
        ),
    ]
