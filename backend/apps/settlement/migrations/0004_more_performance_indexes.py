from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('settlement', '0003_performance_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'dispatch_upload_report_idx '
                'ON dispatch_dispatchupload (dispatch_date, team_id, status);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS dispatch_upload_report_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'dispatch_upload_team_date_idx '
                'ON dispatch_dispatchupload (team_id, dispatch_date);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS dispatch_upload_team_date_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'dispatch_record_upload_valid_manager_idx '
                'ON dispatch_dispatchrecord (upload_id, is_valid, manager_name);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS dispatch_record_upload_valid_manager_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'dispatch_record_upload_valid_yongcha_idx '
                'ON dispatch_dispatchrecord (upload_id, is_valid, is_yongcha);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS dispatch_record_upload_valid_yongcha_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'dispatch_record_upload_valid_region_idx '
                'ON dispatch_dispatchrecord (upload_id, is_valid, sub_region);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS dispatch_record_upload_valid_region_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_period_team_status_idx '
                'ON settlement_settlement (period_start, team_id, status);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_period_team_status_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_team_period_idx '
                'ON settlement_settlement (team_id, period_start, period_end);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_team_period_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_detail_settlement_yongcha_idx '
                'ON settlement_settlementdetail (settlement_id, is_yongcha);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_detail_settlement_yongcha_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'settlement_detail_upload_crew_idx '
                'ON settlement_settlementdetail (dispatch_upload_id, crew_member_id);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS settlement_detail_upload_crew_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'crew_member_team_code_idx '
                'ON crew_crewmember (team_id, code);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS crew_member_team_code_idx;',
        ),
        migrations.RunSQL(
            sql=(
                'CREATE INDEX CONCURRENTLY IF NOT EXISTS '
                'crew_member_team_yongcha_active_idx '
                'ON crew_crewmember (team_id, is_yongcha, is_active);'
            ),
            reverse_sql='DROP INDEX CONCURRENTLY IF EXISTS crew_member_team_yongcha_active_idx;',
        ),
    ]
