"""CalendarEvent.company를 nullable로 변경 (전사 공통 일정 허용)."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('vehicle_management', '0004_add_idle_placement'),
    ]
    operations = [
        migrations.AlterField(
            model_name='calendarevent',
            name='company',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='calendar_events',
                to='vehicle_management.company',
                help_text='null = 전사 공통 일정 (반납 불가일 등)',
            ),
        ),
    ]
