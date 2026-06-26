from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_company_tenant"),
    ]

    operations = [
        migrations.AddField(
            model_name="shipper",
            name="daily_box_threshold",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="shipper",
            name="box_rate_adjustment_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
