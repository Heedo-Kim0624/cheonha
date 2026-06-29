from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vehicle_management', '0008_vehicle_registration_certificate'),
        ('field_manager', '0002_initial_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldManagerAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team_code', models.CharField(db_index=True, max_length=8, verbose_name='조')),
                ('phone', models.CharField(db_index=True, max_length=20, verbose_name='전화번호(정규화)')),
                ('display_phone', models.CharField(blank=True, default='', max_length=20, verbose_name='표시 전화번호')),
                ('name', models.CharField(blank=True, default='', max_length=32, verbose_name='이름')),
                ('memo', models.TextField(blank=True, default='', verbose_name='메모')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='사용')),
                ('last_login_at', models.DateTimeField(blank=True, null=True, verbose_name='마지막 로그인')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='field_manager_accounts', to='vehicle_management.company')),
            ],
            options={
                'db_table': 'field_mgr"."account',
                'ordering': ['company__sort_order', 'team_code', 'phone'],
            },
        ),
        migrations.AddField(
            model_name='fieldmanagersession',
            name='account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='field_manager.fieldmanageraccount'),
        ),
        migrations.AddConstraint(
            model_name='fieldmanageraccount',
            constraint=models.UniqueConstraint(fields=('company', 'team_code', 'phone'), name='fm_account_company_team_phone_unique'),
        ),
        migrations.AddIndex(
            model_name='fieldmanageraccount',
            index=models.Index(fields=['company', 'team_code', 'phone'], name='fm_acct_co_team_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='fieldmanageraccount',
            index=models.Index(fields=['is_active', 'company'], name='fm_acct_active_co_idx'),
        ),
    ]
