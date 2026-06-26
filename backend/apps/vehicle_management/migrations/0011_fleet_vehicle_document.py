from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vehicle_management', '0010_fleet_vehicle_record_history'),
    ]

    operations = [
        migrations.CreateModel(
            name='FleetVehicleDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vehicle_number', models.CharField(db_index=True, max_length=32)),
                ('document_type', models.CharField(choices=[('registration_certificate', '차량 등록증'), ('insurance_application', '보험 청약서')], db_index=True, max_length=64)),
                ('file', models.FileField(upload_to='fleet_vehicle_documents/%Y/%m/%d/')),
                ('note', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('uploaded_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fleet_vehicle_documents', to='vehicle_management.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('vehicle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fleet_documents', to='vehicle_management.vehicle')),
                ('vehicle_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='documents', to='vehicle_management.fleetvehiclerecord')),
            ],
            options={
                'db_table': 'vehicle_mgmt_fleet_vehicle_document',
                'ordering': ['vehicle_number', 'document_type', '-uploaded_at', '-id'],
                'indexes': [
                    models.Index(fields=['company', 'vehicle_number'], name='vehicle_mgm_company_78ed8d_idx'),
                    models.Index(fields=['company', 'document_type'], name='vehicle_mgm_company_90f545_idx'),
                ],
            },
        ),
    ]
