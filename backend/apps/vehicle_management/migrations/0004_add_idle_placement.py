"""Vehicle.placement_status: IDLE(유휴) 추가."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vehicle_management', '0003_expand_operation_choices'),
    ]
    operations = [
        migrations.AlterField(
            model_name='vehicle',
            name='placement_status',
            field=models.CharField(
                choices=[
                    ('OPERATING', '운영중'),
                    ('REPAIRING', '수리/대기중'),
                    ('IDLE',      '유휴'),
                    ('NOT_SHIPPED', '미출고'),
                ],
                db_index=True, default='OPERATING', max_length=16, verbose_name='배치현황',
            ),
        ),
    ]
