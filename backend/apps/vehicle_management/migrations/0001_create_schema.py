"""PostgreSQL 'vehicle_mgmt' 스키마 생성 (sqlite는 no-op)."""
from django.db import migrations, connection


def create_schema(apps, schema_editor):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cur:
            cur.execute('CREATE SCHEMA IF NOT EXISTS vehicle_mgmt')


def drop_schema(apps, schema_editor):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cur:
            cur.execute('DROP SCHEMA IF EXISTS vehicle_mgmt CASCADE')


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunPython(create_schema, drop_schema),
    ]
