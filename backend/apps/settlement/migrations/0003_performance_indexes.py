from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('settlement', '0002_settlementdetail_households'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_detail_region_idx '
                'ON settlement_settlementdetail (region);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_detail_region_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_detail_region_settlement_idx '
                'ON settlement_settlementdetail (region, settlement_id);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_detail_region_settlement_idx;',
        ),
    ]
