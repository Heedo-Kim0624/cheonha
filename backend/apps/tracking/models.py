from django.db import models
from apps.common.models import AuditMixin
from apps.crew.models import CrewMember


STATE_IN_VEHICLE = 'IV'
STATE_SEARCHING = 'SR'
STATE_DELIVERING = 'DL'
STATE_CHOICES = [
    (STATE_IN_VEHICLE, 'In Vehicle'),
    (STATE_SEARCHING, 'Searching'),
    (STATE_DELIVERING, 'Delivering'),
]


class TrackingSession(AuditMixin):
    """배송원 하루치 추적 세션"""
    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name='tracking_sessions',
        verbose_name='배송원',
    )
    session_date = models.DateField('세션 날짜', db_index=True)
    started_at = models.DateTimeField('시작 시각')
    ended_at = models.DateTimeField('종료 시각')
    device_id = models.CharField('단말 ID', max_length=64, blank=True)
    app_version = models.CharField('앱 버전', max_length=40, blank=True)

    # 집계값 (seed/재계산 시 채움)
    total_seconds = models.PositiveIntegerField('총 시간(초)', default=0)
    iv_seconds = models.PositiveIntegerField('In Vehicle 시간(초)', default=0)
    sr_seconds = models.PositiveIntegerField('Searching 시간(초)', default=0)
    dl_seconds = models.PositiveIntegerField('Delivering 시간(초)', default=0)
    distance_m = models.FloatField('이동 거리(m)', default=0)
    cycle_count = models.PositiveIntegerField('사이클 수', default=0)

    # 지도 viewport (zoom-to-layer 용)
    bbox_min_lat = models.FloatField(null=True, blank=True)
    bbox_min_lon = models.FloatField(null=True, blank=True)
    bbox_max_lat = models.FloatField(null=True, blank=True)
    bbox_max_lon = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = '추적 세션'
        verbose_name_plural = '추적 세션'
        ordering = ['-session_date', '-started_at', '-created_at', 'crew_member__code']

    def __str__(self):
        return f'{self.session_date} - {self.crew_member}'


class LocationPoint(models.Model):
    """GPS/Kalman 위치 포인트 (1Hz)"""
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name='points',
    )
    recorded_at = models.DateTimeField(db_index=True)
    lat = models.FloatField()
    lon = models.FloatField()
    accuracy_m = models.FloatField(default=0)
    speed_kmh = models.FloatField(default=0)
    state = models.CharField(max_length=2, choices=STATE_CHOICES, default=STATE_IN_VEHICLE)
    cycle_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['recorded_at']
        indexes = [
            models.Index(fields=['session', 'recorded_at']),
        ]


class BleLog(models.Model):
    """BLE RSSI 로그"""
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name='ble_logs',
    )
    recorded_at = models.DateTimeField(db_index=True)
    rssi = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['recorded_at']


class CameraCapture(models.Model):
    """
    촬영 이벤트.
    - started_at  : camera_start_time
    - captured_at : camera_end_time (촬영 완료 시각)
    - lat / lon   : started_at 과 captured_at 사이를 4:1 로 내분한 시점의 GPS 좌표
                    (배송 사진을 실제로 찍은 순간에 가깝도록 end 쪽으로 80% 이동)
    """
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name='captures',
    )
    started_at = models.DateTimeField(db_index=True, null=True, blank=True)
    captured_at = models.DateTimeField(db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)
    device = models.CharField(max_length=64, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    cycle_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['captured_at']


class Cycle(models.Model):
    """분석된 배송 사이클"""
    session = models.ForeignKey(
        TrackingSession,
        on_delete=models.CASCADE,
        related_name='cycles',
    )
    cycle_no = models.PositiveIntegerField('사이클 번호')
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    sr_seconds = models.PositiveIntegerField(default=0)
    dl_seconds = models.PositiveIntegerField(default=0)
    distance_m = models.FloatField(default=0)
    avg_speed_kmh = models.FloatField(default=0)
    avg_accuracy_m = models.FloatField(default=0)
    capture_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['cycle_no']
        unique_together = ('session', 'cycle_no')


class LiveWorkSessionStatus(models.Model):
    class Status(models.TextChoices):
        STOPPED = "STOPPED", "Stopped"
        RUNNING = "RUNNING", "Running"

    crew_member = models.OneToOneField(
        CrewMember,
        on_delete=models.CASCADE,
        related_name="live_work_status",
        verbose_name="배송원",
    )
    status = models.CharField(
        "근무 상태",
        max_length=16,
        choices=Status.choices,
        default=Status.STOPPED,
        db_index=True,
    )
    current_vehicle_number = models.CharField("현재 차량번호", max_length=20, blank=True)
    session_started_at = models.DateTimeField("근무 시작 시각", null=True, blank=True)
    session_ended_at = models.DateTimeField("근무 종료 시각", null=True, blank=True)
    last_seen_at = models.DateTimeField("마지막 앱 신호", null=True, blank=True, db_index=True)
    background_location_granted = models.BooleanField("항상 허용 여부", default=False)
    last_app_version = models.CharField("앱 버전", max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tracking_live_work_session_status"
        verbose_name = "실시간 근무 상태"
        verbose_name_plural = "실시간 근무 상태"
        ordering = ["crew_member__team__code", "crew_member__name"]

    def __str__(self):
        return f"{self.crew_member} - {self.status}"
