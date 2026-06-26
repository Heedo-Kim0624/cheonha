"""현장관리자 세션 테이블 (field_mgr 스키마)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ('field_manager', '0001_create_schema'),
    ]
    operations = [
        migrations.CreateModel(
            name='FieldManagerSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('company_code', models.CharField(db_index=True, help_text='YUHAN / CHEONHA / PERSONAL', max_length=16, verbose_name='회사 코드')),
                ('team_code', models.CharField(db_index=True, max_length=8, verbose_name='조')),
                ('phone', models.CharField(db_index=True, max_length=20, verbose_name='전화번호')),
                ('user_agent', models.CharField(blank=True, default='', max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('logged_in_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'field_mgr"."session',
                'ordering': ['-logged_in_at'],
            },
        ),
        migrations.AddIndex(
            model_name='fieldmanagersession',
            index=models.Index(fields=['team_code', 'phone'], name='fm_sess_tc_ph_idx'),
        ),
    ]
