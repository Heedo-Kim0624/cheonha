from django.conf import settings
from django.db import models


class MobileAppUser(models.Model):
    """기사의 앱 가입 요청 및 승인 상태를 관리하는 모델"""

    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        APPROVED = "APPROVED", "승인"
        REJECTED = "REJECTED", "거절"

    crew_member = models.OneToOneField(
        "crew.CrewMember",
        on_delete=models.CASCADE,
        related_name="mobile_app_user",
        verbose_name="기사",
    )
    name = models.CharField("이름", max_length=50)
    team_code = models.CharField("조 코드", max_length=1)
    status = models.CharField(
        "상태",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    device_token = models.CharField(
        "푸시 토큰", max_length=255, blank=True, null=True
    )
    requested_at = models.DateTimeField("요청일시", auto_now_add=True)
    approved_at = models.DateTimeField("승인일시", blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="mobile_approvals",
        verbose_name="승인자",
    )
    last_login_at = models.DateTimeField(
        "최근 로그인", blank=True, null=True
    )
    is_active = models.BooleanField("활성 상태", default=True)

    class Meta:
        db_table = "mobile_app_users"
        verbose_name = "모바일 앱 사용자"
        verbose_name_plural = "모바일 앱 사용자"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.name} ({self.team_code}조) - {self.get_status_display()}"


class MobilePassword(models.Model):
    """모바일 앱 비밀번호(4자리 숫자)를 관리하는 모델"""

    mobile_user = models.OneToOneField(
        "mobile.MobileAppUser",
        on_delete=models.CASCADE,
        related_name="password_record",
        verbose_name="모바일 앱 사용자",
    )
    password_hash = models.CharField("비밀번호 해시", max_length=128)
    is_default = models.BooleanField("초기 비밀번호 여부", default=True)
    changed_at = models.DateTimeField("비밀번호 변경일시", blank=True, null=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        db_table = "mobile_passwords"
        verbose_name = "모바일 비밀번호"
        verbose_name_plural = "모바일 비밀번호"

    def __str__(self):
        return f"{self.mobile_user.name} ({self.mobile_user.team_code}조)"
