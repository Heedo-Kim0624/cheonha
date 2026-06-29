from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicle_management', '0011_fleet_vehicle_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='fleetaccidentcase',
            name='source_key',
            field=models.CharField(blank=True, db_index=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='fleetaccidentcase',
            name='personal_compensation',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='fleetaccidentcase',
            name='property_compensation',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='fleetaccidentcase',
            name='compensation_note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddIndex(
            model_name='fleetaccidentcase',
            index=models.Index(fields=['company', 'source_key'], name='vehicle_mgm_company_8b6b47_idx'),
        ),
    ]
