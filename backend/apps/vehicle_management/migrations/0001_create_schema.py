"""Vehicle management migration namespace placeholder.

The first implementation attempted to create a PostgreSQL-only schema and then
used quoted schema table names. That made the default sqlite development DB
fail with ``unknown database "vehicle_mgmt"``. Vehicle-management tables now use
portable ``vehicle_mgmt_*`` table names, so this migration intentionally keeps
the migration namespace without touching the database.
"""
from django.db import migrations


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunPython(noop, noop),
    ]
