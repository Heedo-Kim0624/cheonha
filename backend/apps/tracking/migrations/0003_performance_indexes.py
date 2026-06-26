from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("tracking", "0002_liveworksessionstatus"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                "tracking_cameracapture_lon_lat_notnull_idx "
                "ON tracking_cameracapture (lon, lat) "
                "WHERE lon IS NOT NULL AND lat IS NOT NULL;"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                "tracking_cameracapture_lon_lat_notnull_idx;"
            ),
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                "tracking_cameracapture_session_captured_idx "
                "ON tracking_cameracapture (session_id, captured_at);"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                "tracking_cameracapture_session_captured_idx;"
            ),
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                "tracking_cycle_session_started_ended_idx "
                "ON tracking_cycle (session_id, started_at, ended_at);"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                "tracking_cycle_session_started_ended_idx;"
            ),
        ),
    ]
