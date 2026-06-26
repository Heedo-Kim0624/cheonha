"""차량관리 도메인 테이블 (vehicle_mgmt 스키마)."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ('vehicle_management', '0001_create_schema'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('code', models.CharField(choices=[('YUHAN', '유한'), ('CHEONHA', '천하'), ('PERSONAL', '개인')], max_length=16, unique=True)),
                ('name', models.CharField(max_length=32)),
                ('sort_order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'vehicle_mgmt"."company',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('vehicle_number', models.CharField(db_index=True, max_length=32, verbose_name='차량번호')),
                ('vehicle_number_short', models.CharField(db_index=True, help_text='피트 차량현황 매칭용 (예: 4806)', max_length=8, verbose_name='차량번호 끝 4자리')),
                ('vin_tid', models.CharField(blank=True, db_index=True, default='', max_length=32, verbose_name='VIN(TID)')),
                ('model', models.CharField(blank=True, default='', max_length=64, verbose_name='모델')),
                ('shipped_at', models.DateField(blank=True, null=True, verbose_name='차량 출고일')),
                ('fleet', models.CharField(blank=True, default='', help_text='컬리/H, 컬리/R, 쿠팡/송파, 천하운수, 개인 등', max_length=64, verbose_name='플릿')),
                ('driver', models.CharField(blank=True, default='', max_length=32, verbose_name='운전자')),
                ('hgi', models.CharField(blank=True, db_index=True, default='', help_text='EV82, EV78 등', max_length=16, verbose_name='호기')),
                ('placement_status', models.CharField(choices=[('OPERATING', '운영중'), ('REPAIRING', '수리/대기중'), ('NOT_SHIPPED', '미출고')], db_index=True, default='OPERATING', max_length=16, verbose_name='배치현황')),
                ('operation_type', models.CharField(choices=[('SALE', '판매'), ('OTHER', '기타')], default='SALE', max_length=16, verbose_name='운영 구분')),
                ('notes', models.TextField(blank=True, default='', verbose_name='비고')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vehicles', to='vehicle_management.company')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."vehicle',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='vehicle',
            constraint=models.UniqueConstraint(fields=('company', 'vehicle_number'), name='vm_vehicle_company_number_unique'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['company', 'placement_status'], name='vm_vehicle_co_pl_idx'),
        ),
        migrations.CreateModel(
            name='SubscriptionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('team_code', models.CharField(db_index=True, max_length=8, verbose_name='조')),
                ('phone', models.CharField(max_length=20, verbose_name='전화번호')),
                ('requested_date', models.DateField(db_index=True, verbose_name='요청 날짜')),
                ('quantity', models.PositiveIntegerField(verbose_name='요청 대수')),
                ('status', models.CharField(choices=[('REQUESTED', '요청 등록'), ('VEHICLES_SELECTED', '차량 선택 완료'), ('COMPLETED', '완료'), ('CANCELLED', '취소')], db_index=True, default='REQUESTED', max_length=24)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscription_requests', to='vehicle_management.company')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."subscription_request',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='subscriptionrequest',
            index=models.Index(fields=['company', 'status'], name='vm_subreq_co_st_idx'),
        ),
        migrations.AddIndex(
            model_name='subscriptionrequest',
            index=models.Index(fields=['team_code', 'phone'], name='vm_subreq_tc_ph_idx'),
        ),
        migrations.CreateModel(
            name='SubscriptionRequestVehicle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matched_vehicles', to='vehicle_management.subscriptionrequest')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='vehicle_management.vehicle')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."subscription_request_vehicle',
            },
        ),
        migrations.AddConstraint(
            model_name='subscriptionrequestvehicle',
            constraint=models.UniqueConstraint(fields=('request', 'vehicle'), name='vm_subreq_vehicle_unique'),
        ),
        migrations.CreateModel(
            name='ReturnRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('team_code', models.CharField(db_index=True, max_length=8, verbose_name='조')),
                ('phone', models.CharField(max_length=20, verbose_name='전화번호')),
                ('vehicle_number', models.CharField(db_index=True, max_length=32, verbose_name='차량번호')),
                ('reason', models.TextField(verbose_name='반납 사유')),
                ('hope_date', models.DateField(db_index=True, verbose_name='반납 희망 날짜')),
                ('hope_time', models.TimeField(help_text='10:00~16:00 사이만 허용 (앱 측 검증)', verbose_name='반납 희망 시간')),
                ('confirmed_date', models.DateField(blank=True, null=True, verbose_name='확정 반납 날짜')),
                ('confirmed_time', models.TimeField(blank=True, null=True, verbose_name='확정 반납 시간')),
                ('block_reason', models.TextField(blank=True, default='', verbose_name='불가사유')),
                ('available_dates', models.CharField(blank=True, default='', max_length=128, verbose_name='가능 날짜')),
                ('status', models.CharField(choices=[('REQUESTED', '반납 요청 등록'), ('CONFIRMED', '반납 확정'), ('NEEDS_ADJUST', '반납 조정 필요'), ('COMPLETED', '완료')], db_index=True, default='REQUESTED', max_length=24)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_requests', to='vehicle_management.company')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."return_request',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='returnrequest',
            index=models.Index(fields=['company', 'status'], name='vm_retreq_co_st_idx'),
        ),
        migrations.CreateModel(
            name='ASRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('team_code', models.CharField(db_index=True, max_length=8, verbose_name='조')),
                ('phone', models.CharField(max_length=20, verbose_name='전화번호')),
                ('vehicle_number', models.CharField(db_index=True, max_length=32, verbose_name='차량번호')),
                ('reason', models.TextField(verbose_name='A/S 사유')),
                ('admin_comment', models.TextField(blank=True, default='', verbose_name='관리자 코멘트')),
                ('calendar_note', models.TextField(blank=True, default='', verbose_name='캘린더 내용')),
                ('status', models.CharField(choices=[('REQUESTED', 'A/S 요청 등록'), ('COMPLETED', 'A/S 처리 완료')], db_index=True, default='REQUESTED', max_length=16)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='as_requests', to='vehicle_management.company')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."as_request',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='asrequest',
            index=models.Index(fields=['company', 'status'], name='vm_asreq_co_st_idx'),
        ),
        migrations.CreateModel(
            name='PitRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('vehicle_number_short', models.CharField(db_index=True, max_length=8, verbose_name='차량번호(4자리)')),
                ('in_date', models.DateField(db_index=True, verbose_name='입고일')),
                ('out_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='출고일')),
                ('reason', models.CharField(choices=[('SERVICE', '서비스카'), ('REPAIR', '수리입고'), ('ACCIDENT', '사고입고'), ('RETURN', '구독 반납')], db_index=True, max_length=16, verbose_name='입고사유')),
                ('note', models.TextField(blank=True, default='', verbose_name='비고')),
                ('note_highlight', models.BooleanField(default=False, verbose_name='비고 강조 (노란색)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pit_records', to='vehicle_management.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('vehicle', models.ForeignKey(blank=True, help_text='차량번호 끝 4자리로 자동 매칭', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pit_records', to='vehicle_management.vehicle')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."pit_record',
                'ordering': ['-in_date', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='pitrecord',
            index=models.Index(fields=['company', 'out_date'], name='vm_pit_co_out_idx'),
        ),
        migrations.AddIndex(
            model_name='pitrecord',
            index=models.Index(fields=['vehicle_number_short'], name='vm_pit_vns_idx'),
        ),
        migrations.CreateModel(
            name='CalendarEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('BLOCK', '반납 불가'), ('REQ_HOPE', '구독 요청 희망일'), ('RET_HOPE', '반납 희망일'), ('RET_CONFIRM', '반납 확정일'), ('AS_SCHED', 'A/S 일정'), ('PIT_OUT', '피트 출고 예정')], db_index=True, max_length=16, verbose_name='종류')),
                ('event_date', models.DateField(db_index=True, verbose_name='일자')),
                ('event_time', models.TimeField(blank=True, null=True, verbose_name='시간')),
                ('title', models.CharField(max_length=128, verbose_name='제목')),
                ('body', models.TextField(blank=True, default='', verbose_name='내용')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='vehicle_management.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('related_as', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='vehicle_management.asrequest')),
                ('related_pit_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='vehicle_management.pitrecord')),
                ('related_return', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='vehicle_management.returnrequest')),
                ('related_subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='calendar_events', to='vehicle_management.subscriptionrequest')),
                ('related_vehicle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='vehicle_management.vehicle')),
            ],
            options={
                'db_table': 'vehicle_mgmt"."calendar_event',
                'ordering': ['event_date', 'event_time', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='calendarevent',
            index=models.Index(fields=['company', 'event_date', 'kind'], name='vm_cal_co_dt_kd_idx'),
        ),
    ]
