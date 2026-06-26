from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("one_settlement", "0002_perf_indexes"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX IF NOT EXISTS one_order_month_collect_idx "
                        "ON one_settlement_oneshipmentorder "
                        "(company_app, shipper_code, month, delivery_date, driver_name, "
                        "service_code, category_code, order_number, id)"
                    ),
                    reverse_sql="DROP INDEX IF EXISTS one_order_month_collect_idx",
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="oneshipmentorder",
                    index=models.Index(
                        fields=[
                            "company_app",
                            "shipper_code",
                            "month",
                            "delivery_date",
                            "driver_name",
                            "service_code",
                            "category_code",
                            "order_number",
                            "id",
                        ],
                        name="one_order_month_collect_idx",
                    ),
                ),
            ],
        ),
    ]
