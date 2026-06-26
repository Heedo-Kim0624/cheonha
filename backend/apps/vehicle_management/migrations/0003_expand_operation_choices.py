"""Vehicle.operation_type choices 확장: SALE/OTHER → SALE/DIRECT/SUBSCRIPTION/OTHER."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vehicle_management', '0002_initial_models'),
    ]
    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='operation_type',
            field=models.CharField(
                choices=[
                    ('SALE',         '판매'),
                    ('DIRECT',       '직영'),
                    ('SUBSCRIPTION', '구독'),
                    ('OTHER',        '기타'),
                ],
                default='SALE',
                max_length=16,
                verbose_name='운영 구분',
            ),
        ),
    ]
