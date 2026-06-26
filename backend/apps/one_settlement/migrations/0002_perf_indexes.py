from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("one_settlement", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX IF NOT EXISTS one_order_month_date_id_idx "
                        "ON one_settlement_oneshipmentorder "
                        "(company_app, shipper_code, month, delivery_date, id)"
                    ),
                    reverse_sql="DROP INDEX IF EXISTS one_order_month_date_id_idx",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX IF NOT EXISTS one_order_month_svc_cat_idx "
                        "ON one_settlement_oneshipmentorder "
                        "(company_app, shipper_code, month, service_code, category_code)"
                    ),
                    reverse_sql="DROP INDEX IF EXISTS one_order_month_svc_cat_idx",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX IF NOT EXISTS one_order_month_driver_svc_idx "
                        "ON one_settlement_oneshipmentorder "
                        "(company_app, shipper_code, month, driver_id, service_code, category_code)"
                    ),
                    reverse_sql="DROP INDEX IF EXISTS one_order_month_driver_svc_idx",
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="oneshipmentorder",
                    index=models.Index(
                        fields=["company_app", "shipper_code", "month", "delivery_date", "id"],
                        name="one_order_month_date_id_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="oneshipmentorder",
                    index=models.Index(
                        fields=["company_app", "shipper_code", "month", "service_code", "category_code"],
                        name="one_order_month_svc_cat_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="oneshipmentorder",
                    index=models.Index(
                        fields=["company_app", "shipper_code", "month", "driver", "service_code", "category_code"],
                        name="one_order_month_driver_svc_idx",
                    ),
                ),
            ],
        ),
    ]
