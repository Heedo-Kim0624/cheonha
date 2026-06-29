from django.conf import settings
from django.db import models

from apps.common.models import AuditMixin


class PointItem(AuditMixin):
    key = models.SlugField("항목 키", max_length=64, unique=True)
    name = models.CharField("항목명", max_length=100)
    cost_points = models.PositiveIntegerField("필요 포인트")
    sort_order = models.PositiveIntegerField("정렬 순서", default=0)
    is_active = models.BooleanField("사용 여부", default=True, db_index=True)

    class Meta:
        db_table = "points_point_items"
        verbose_name = "포인트 상점 항목"
        verbose_name_plural = "포인트 상점 항목"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name} ({self.cost_points}P)"


class PointTransaction(AuditMixin):
    class Kind(models.TextChoices):
        WORK_REWARD = "WORK_REWARD", "근무기록 적립"
        MANUAL_ADJUST = "MANUAL_ADJUST", "수동 수정"
        REDEMPTION_DEDUCT = "REDEMPTION_DEDUCT", "교환 차감"

    crew_member = models.ForeignKey(
        "crew.CrewMember",
        on_delete=models.CASCADE,
        related_name="point_transactions",
        verbose_name="배송원",
    )
    points = models.IntegerField("포인트")
    kind = models.CharField("유형", max_length=32, choices=Kind.choices)
    memo = models.CharField("메모", max_length=255, blank=True)
    work_date = models.DateField("근무일", null=True, blank=True, db_index=True)
    tracking_session = models.OneToOneField(
        "tracking.TrackingSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="point_transaction",
        verbose_name="근무기록",
    )
    redemption = models.ForeignKey(
        "points.PointRedemption",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="교환 요청",
    )

    class Meta:
        db_table = "points_point_transactions"
        verbose_name = "포인트 거래"
        verbose_name_plural = "포인트 거래"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["crew_member", "kind", "work_date"]),
            models.Index(fields=["kind", "created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.points >= 0 else ""
        return f"{self.crew_member} {sign}{self.points}P"


class PointRedemption(AuditMixin):
    class Status(models.TextChoices):
        PENDING = "PENDING", "사용 대기"
        CONFIRMED = "CONFIRMED", "사용 확인"
        CANCELLED = "CANCELLED", "취소"

    crew_member = models.ForeignKey(
        "crew.CrewMember",
        on_delete=models.CASCADE,
        related_name="point_redemptions",
        verbose_name="배송원",
    )
    item_key = models.CharField("항목 키", max_length=64)
    item_name = models.CharField("항목명", max_length=100)
    cost_points = models.PositiveIntegerField("사용 포인트")
    status = models.CharField(
        "상태",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    requested_at = models.DateTimeField("요청일시", auto_now_add=True)
    confirmed_at = models.DateTimeField("확인일시", null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_point_redemptions",
        verbose_name="확인자",
    )
    note = models.CharField("비고", max_length=255, blank=True)

    class Meta:
        db_table = "points_point_redemptions"
        verbose_name = "포인트 교환 요청"
        verbose_name_plural = "포인트 교환 요청"
        ordering = ["status", "-requested_at", "-id"]
        indexes = [
            models.Index(fields=["status", "requested_at"]),
            models.Index(fields=["crew_member", "status"]),
        ]

    def __str__(self):
        return f"{self.crew_member} - {self.item_name} ({self.get_status_display()})"
