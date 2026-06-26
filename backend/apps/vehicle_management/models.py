"""
차량 관리 도메인 모델 — schema='vehicle_mgmt'

- Vehicle              회사별 차량 마스터 (차량 현황_2026-04-28.xlsx 9컬럼 + 회사 구분)
- PitRecord            피트 입출고 이력 (입고일/출고일/입고사유/비고)
- CalendarEvent        통합 일정 (반납 불가 / 구독 요청 희망일 / 반납 희망/확정 / A/S / 피트 출고)
- SubscriptionRequest  현장관리자 구독 요청 (날짜+대수)
- SubscriptionRequestVehicle  요청에 매칭된 차량 (요청 대수만큼)
- ReturnRequest        구독 반납 요청 (차량/사유/희망일/희망시간/확정/조정)
- ASRequest            A/S 요청 (차량/사유 → 코멘트/캘린더 내용)
"""
from django.db import models
from django.conf import settings


# ── helper ────────────────────────────────────────────────────────────────────
class VMSchemaMixin:
    """모든 vehicle_management 테이블은 vehicle_mgmt 스키마에 생성."""
    pass


# ── 1. Company ────────────────────────────────────────────────────────────────
class Company(models.Model):
    """유한 / 천하 / 개인 (명세 6.2)"""
    CODE_CHOICES = [
        ('YUHAN',   '유한'),
        ('CHEONHA', '천하'),
        ('PERSONAL', '개인'),
    ]
    code = models.CharField(max_length=16, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=32)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicle_mgmt"."company'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.name} ({self.code})'


# ── 2. Vehicle (전체 차량현황) ────────────────────────────────────────────────
class Vehicle(models.Model):
    """차량 마스터 — 차량 현황_2026-04-28.xlsx 컬럼 그대로"""
    PLACEMENT_CHOICES = [
        ('OPERATING', '운영중'),
        ('REPAIRING', '수리/대기중'),
        ('IDLE',      '유휴'),
        ('NOT_SHIPPED', '미출고'),
    ]
    OPERATION_CHOICES = [
        ('SALE',         '판매'),
        ('DIRECT',       '직영'),
        ('SUBSCRIPTION', '구독'),
        ('OTHER',        '기타'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='vehicles')
    vehicle_number = models.CharField('차량번호', max_length=32, db_index=True)
    vehicle_number_short = models.CharField(
        '차량번호 끝 4자리', max_length=8, db_index=True,
        help_text='피트 차량현황 매칭용 (예: 4806)',
    )
    vin_tid = models.CharField('VIN(TID)', max_length=32, blank=True, default='', db_index=True)
    model = models.CharField('모델', max_length=64, blank=True, default='')
    shipped_at = models.DateField('차량 출고일', null=True, blank=True)
    fleet = models.CharField('플릿', max_length=64, blank=True, default='',
                             help_text='컬리/H, 컬리/R, 쿠팡/송파, 천하운수, 개인 등')
    driver = models.CharField('운전자', max_length=32, blank=True, default='')
    hgi = models.CharField('호기', max_length=16, blank=True, default='', db_index=True,
                            help_text='EV82, EV78 등')
    registration_certificate = models.FileField(
        '자동차등록증',
        upload_to='vehicle_registrations/%Y/%m/%d/',
        blank=True,
        default='',
    )
    registration_certificate_uploaded_at = models.DateTimeField(
        '자동차등록증 업로드 시각',
        null=True,
        blank=True,
    )
    placement_status = models.CharField('배치현황', max_length=16, choices=PLACEMENT_CHOICES,
                                         default='OPERATING', db_index=True)
    operation_type = models.CharField('운영 구분', max_length=16, choices=OPERATION_CHOICES,
                                       default='SALE')
    notes = models.TextField('비고', blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."vehicle'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'vehicle_number'],
                name='vm_vehicle_company_number_unique',
            ),
        ]
        indexes = [
            models.Index(fields=['company', 'placement_status']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} ({self.company.name})'

    def save(self, *args, **kwargs):
        if self.vehicle_number and not self.vehicle_number_short:
            digits = ''.join(c for c in self.vehicle_number if c.isdigit())
            self.vehicle_number_short = digits[-4:] if len(digits) >= 4 else digits
        super().save(*args, **kwargs)


# ── 3. PitRecord (피트 차량현황) ──────────────────────────────────────────────
class PitRecord(models.Model):
    """피트 입출고 이력 — 출고일이 없으면 현재 재실 중"""
    REASON_CHOICES = [
        ('SERVICE',   '서비스카'),
        ('REPAIR',    '수리입고'),
        ('ACCIDENT',  '사고입고'),
        ('RETURN',    '구독 반납'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='pit_records')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='pit_records',
                                 help_text='차량번호 끝 4자리로 자동 매칭')
    vehicle_number_short = models.CharField('차량번호(4자리)', max_length=8, db_index=True)
    in_date = models.DateField('입고일', db_index=True)
    out_date = models.DateField('출고일', null=True, blank=True, db_index=True)
    reason = models.CharField('입고사유', max_length=16, choices=REASON_CHOICES, db_index=True)
    note = models.TextField('비고', blank=True, default='')
    note_highlight = models.BooleanField('비고 강조 (노란색)', default=False)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."pit_record'
        ordering = ['-in_date', '-id']
        indexes = [
            models.Index(fields=['company', 'out_date']),
            models.Index(fields=['vehicle_number_short']),
        ]

    @property
    def is_in_pit(self) -> bool:
        return self.out_date is None

    def __str__(self):
        return f'{self.vehicle_number_short} · {self.get_reason_display()} · {self.in_date}'


# ── 4. CalendarEvent (통합 일정) ──────────────────────────────────────────────
class CalendarEvent(models.Model):
    """반납 불가 + 구독 요청 희망일 + 반납 희망/확정 + A/S + 피트 출고 통합 일정"""
    KIND_CHOICES = [
        ('BLOCK',       '반납 불가'),
        ('REQ_HOPE',    '구독 요청 희망일'),
        ('RET_HOPE',    '반납 희망일'),
        ('RET_CONFIRM', '반납 확정일'),
        ('AS_SCHED',    'A/S 일정'),
        ('PIT_OUT',     '피트 출고 예정'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                 related_name='calendar_events',
                                 null=True, blank=True,
                                 help_text='null = 전사 공통 일정 (반납 불가일 등)')
    kind = models.CharField('종류', max_length=16, choices=KIND_CHOICES, db_index=True)
    event_date = models.DateField('일자', db_index=True)
    event_time = models.TimeField('시간', null=True, blank=True)
    title = models.CharField('제목', max_length=128)
    body = models.TextField('내용', blank=True, default='')

    # 연결 (어떤 도메인에서 만들어졌는지)
    related_vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='+')
    related_pit_record = models.ForeignKey(PitRecord, on_delete=models.CASCADE,
                                            null=True, blank=True, related_name='calendar_events')
    related_subscription = models.ForeignKey('SubscriptionRequest', on_delete=models.CASCADE,
                                              null=True, blank=True, related_name='calendar_events')
    related_return = models.ForeignKey('ReturnRequest', on_delete=models.CASCADE,
                                        null=True, blank=True, related_name='calendar_events')
    related_as = models.ForeignKey('ASRequest', on_delete=models.CASCADE,
                                    null=True, blank=True, related_name='calendar_events')

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."calendar_event'
        ordering = ['event_date', 'event_time', 'id']
        indexes = [
            models.Index(fields=['company', 'event_date', 'kind']),
        ]

    def __str__(self):
        return f'[{self.get_kind_display()}] {self.event_date} · {self.title}'


# ── 5. SubscriptionRequest (구독 요청 — 날짜+대수) ────────────────────────────
class SubscriptionRequest(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED',         '요청 등록'),
        ('APPROVED',          '승인'),
        ('VEHICLES_SELECTED', '차량 선택 완료'),
        ('COMPLETED',         '완료'),
        ('REJECTED',          '거절'),
        ('CANCELLED',         '취소'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT,
                                 related_name='subscription_requests')
    team_code = models.CharField('조', max_length=8, db_index=True)
    phone = models.CharField('전화번호', max_length=20)
    requested_date = models.DateField('요청 날짜', db_index=True)
    quantity = models.PositiveIntegerField('요청 대수')
    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                               default='REQUESTED', db_index=True)
    reject_reason = models.TextField('거절 사유', blank=True, default='')
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."subscription_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['team_code', 'phone']),
        ]

    def __str__(self):
        return f'[요청] {self.team_code}조 · {self.requested_date} · {self.quantity}대'


class SubscriptionRequestVehicle(models.Model):
    """요청에 매칭된 차량 — 요청 대수만큼 (명세 7.2)"""
    request = models.ForeignKey(SubscriptionRequest, on_delete=models.CASCADE,
                                 related_name='matched_vehicles')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicle_mgmt"."subscription_request_vehicle'
        constraints = [
            models.UniqueConstraint(
                fields=['request', 'vehicle'],
                name='vm_subreq_vehicle_unique',
            ),
        ]


# ── 6. ReturnRequest (구독 반납) ──────────────────────────────────────────────
class ReturnRequest(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED',     '반납 요청 등록'),
        ('CONFIRMED',     '반납 확정'),
        ('NEEDS_ADJUST',  '반납 조정 필요'),
        ('COMPLETED',     '완료'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT,
                                 related_name='return_requests')
    team_code = models.CharField('조', max_length=8, db_index=True)
    phone = models.CharField('전화번호', max_length=20)
    vehicle_number = models.CharField('차량번호', max_length=32, db_index=True)
    reason = models.TextField('반납 사유')
    hope_date = models.DateField('반납 희망 날짜', db_index=True)
    hope_time = models.TimeField('반납 희망 시간',
                                  help_text='10:00~16:00 사이만 허용 (앱 측 검증)')

    confirmed_date = models.DateField('확정 반납 날짜', null=True, blank=True)
    confirmed_time = models.TimeField('확정 반납 시간', null=True, blank=True)
    block_reason = models.TextField('불가사유', blank=True, default='')
    available_dates = models.CharField('가능 날짜', max_length=128, blank=True, default='')

    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                               default='REQUESTED', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."return_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
        ]

    def __str__(self):
        return f'[반납] {self.team_code}조 · {self.vehicle_number} · {self.hope_date}'


class ReturnRequestPhoto(models.Model):
    KIND_CHOICES = [
        ('FRONT', '전면'),
        ('REAR', '후면'),
        ('LEFT', '좌측'),
        ('RIGHT', '우측'),
        ('DASHBOARD', '내부 대시보드'),
    ]

    request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='photos')
    kind = models.CharField('사진 구분', max_length=16, choices=KIND_CHOICES)
    image = models.FileField('사진 파일', upload_to='vehicle_returns/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vehicle_mgmt"."return_request_photo'
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['request', 'kind'],
                name='vm_return_request_photo_kind_unique',
            ),
        ]

    def __str__(self):
        return f'[{self.request_id}] {self.kind}'


# ── 7. ASRequest (A/S) ────────────────────────────────────────────────────────
class FleetVehicleRecord(models.Model):
    """Actual vehicle history under one user-facing vehicle number."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_vehicle_records')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_records')
    vehicle_number = models.CharField(max_length=32, db_index=True)
    vin = models.CharField(max_length=32, db_index=True)
    model = models.CharField(max_length=64, blank=True, default='')
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, default='운행중', db_index=True)
    certificate_name = models.CharField(max_length=255, blank=True, default='')
    certificate_uploaded_at = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_vehicle_record'
        ordering = ['vehicle_number', 'start_date', 'id']
        indexes = [
            models.Index(fields=['company', 'vehicle_number']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['vehicle', 'start_date']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} - {self.vin}'


class FleetVehicleDocument(models.Model):
    """Vehicle-number scoped documents used by /fleet-management/."""
    DOCUMENT_TYPE_CHOICES = [
        ('registration_certificate', '차량 등록증'),
        ('insurance_application', '보험 청약서'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_vehicle_documents')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_documents')
    vehicle_record = models.ForeignKey(FleetVehicleRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    vehicle_number = models.CharField(max_length=32, db_index=True)
    document_type = models.CharField(max_length=64, choices=DOCUMENT_TYPE_CHOICES, db_index=True)
    file = models.FileField(upload_to='fleet_vehicle_documents/%Y/%m/%d/')
    note = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_vehicle_document'
        ordering = ['vehicle_number', 'document_type', '-uploaded_at', '-id']
        indexes = [
            models.Index(fields=['company', 'vehicle_number']),
            models.Index(fields=['company', 'document_type']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} {self.document_type}'


class FleetSubscriptionContract(models.Model):
    """API-backed subscription contract used by /fleet-management/."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_subscription_contracts')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_subscription_contracts')
    vehicle_record = models.ForeignKey(FleetVehicleRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscription_contracts')
    vehicle_number = models.CharField(max_length=32, db_index=True)
    customer = models.CharField(max_length=128)
    contact = models.CharField(max_length=64, blank=True, default='')
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    monthly_fee = models.PositiveIntegerField(default=0)
    deposit = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=32, default='구독중', db_index=True)
    sign_status = models.CharField(max_length=32, default='서명완료')
    contract_file = models.FileField(upload_to='vehicle_contracts/%Y/%m/%d/', blank=True, default='')
    note = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_subscription_contract'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'vehicle_number']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} - {self.customer}'


class FleetReturnRecord(models.Model):
    """API-backed return, inspection, photo and repair summary used by /fleet-management/."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_return_records')
    subscription = models.ForeignKey(FleetSubscriptionContract, on_delete=models.SET_NULL, null=True, blank=True, related_name='return_records')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_return_records')
    vehicle_record = models.ForeignKey(FleetVehicleRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='return_records')
    vehicle_number = models.CharField(max_length=32, db_index=True)
    customer = models.CharField(max_length=128, blank=True, default='')
    scheduled_at = models.DateTimeField(db_index=True)
    actual_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=32, default='반납예정', db_index=True)
    photos = models.JSONField(default=list, blank=True)
    checks = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True, default='')
    repairs = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_return_record'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'vehicle_number']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} return {self.scheduled_at:%Y-%m-%d}'


class FleetInsurancePolicy(models.Model):
    """API-backed insurance schedule used by /fleet-management/."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_insurance_policies')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_insurance_policies')
    vehicle_record = models.ForeignKey(FleetVehicleRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='insurance_policies')
    vehicle_number = models.CharField(max_length=32, db_index=True)
    insurer = models.CharField(max_length=128)
    policy_no = models.CharField(max_length=128, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    previous_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    current_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(max_length=32, default='가입중', db_index=True)
    payments = models.JSONField(default=list, blank=True)
    note = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_insurance_policy'
        ordering = ['end_date', 'id']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'vehicle_number']),
        ]

    def __str__(self):
        return f'{self.vehicle_number} - {self.policy_no}'


class FleetAccidentCase(models.Model):
    """API-backed accident and compensation case used by /fleet-management/."""
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='fleet_accident_cases')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name='fleet_accident_cases')
    vehicle_record = models.ForeignKey(FleetVehicleRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='accident_cases')
    source_key = models.CharField(max_length=128, blank=True, default='', db_index=True)
    vehicle_number = models.CharField(max_length=32, db_index=True)
    vehicle_vin = models.CharField(max_length=32, blank=True, default='')
    driver = models.CharField(max_length=64, blank=True, default='')
    accident_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    coverage = models.CharField(max_length=128, blank=True, default='')
    victim = models.CharField(max_length=128, blank=True, default='')
    compensation = models.IntegerField(default=0)
    personal_compensation = models.IntegerField(default=0)
    property_compensation = models.IntegerField(default=0)
    paid = models.IntegerField(default=0)
    manager = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=32, default='진행중', db_index=True)
    compensation_note = models.TextField(blank=True, default='')
    items = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."fleet_accident_case'
        ordering = ['-accident_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'vehicle_number']),
            models.Index(fields=['company', 'source_key'], name='vehicle_mgm_company_8b6b47_idx'),
        ]

    def __str__(self):
        return f'{self.vehicle_number} accident {self.accident_at:%Y-%m-%d}'


class ASRequest(models.Model):
    STATUS_CHOICES = [
        ('REPAIRING', 'Repairing / waiting'),
        ('OPERATING', 'Operating'),
        ('REQUESTED', 'A/S 요청 등록'),
        ('COMPLETED', 'A/S 처리 완료'),
    ]

    company = models.ForeignKey(Company, on_delete=models.PROTECT,
                                 related_name='as_requests')
    team_code = models.CharField('조', max_length=8, db_index=True)
    phone = models.CharField('요청자 전화번호', max_length=20)
    vehicle_number = models.CharField('차량번호', max_length=32, db_index=True)
    owner_name = models.CharField('차량 소유자', max_length=32, blank=True, default='')
    owner_phone = models.CharField('운영 차주 전화번호', max_length=20, blank=True, default='')
    reason = models.TextField('A/S 사유')

    admin_comment = models.TextField('관리자 코멘트', blank=True, default='')
    calendar_note = models.TextField('캘린더 내용', blank=True, default='')

    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                               default='REQUESTED', db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_mgmt"."as_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
        ]

    def __str__(self):
        return f'[A/S] {self.team_code}조 · {self.vehicle_number}'
