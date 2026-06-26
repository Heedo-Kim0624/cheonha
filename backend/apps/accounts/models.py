import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


DEFAULT_COMPANY_TABS = ["dispatch", "crew", "region"]
OPTIONAL_COMPANY_TABS = [
    "dashboard",
    "operations",
    "settlement",
    "inquiry",
    "tracking",
    "manpower",
]
ALL_COMPANY_TABS = DEFAULT_COMPANY_TABS + OPTIONAL_COMPANY_TABS
CORE_COMPANY_APP_CODES = ("cheonha",)
DEFAULT_SHIPPER_CODES = ["kurly"]


def default_company_tabs():
    return list(DEFAULT_COMPANY_TABS)


def new_company_signup_token():
    return uuid.uuid4().hex


def default_enabled_shippers():
    return list(DEFAULT_SHIPPER_CODES)


def default_shipper_available_tabs():
    return list(ALL_COMPANY_TABS)


class Shipper(models.Model):
    """Cargo owner profile used by one or more carrier companies."""

    code = models.CharField(max_length=40, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=16,
        choices=(("ACTIVE", "Active"), ("INACTIVE", "Inactive")),
        default="ACTIVE",
        db_index=True,
    )
    upload_type = models.CharField(
        max_length=16,
        choices=(("FILE", "File"), ("TEXT", "Text")),
        default="FILE",
    )
    upload_profile = models.CharField(max_length=40, default="kurly")
    operation_report_profile = models.CharField(max_length=40, default="kurly")
    settlement_profile = models.CharField(max_length=40, default="kurly")
    daily_box_threshold = models.PositiveIntegerField(default=0)
    box_rate_adjustment_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    default_enabled_tabs = models.JSONField(default=default_company_tabs, blank=True)
    available_tabs = models.JSONField(default=default_shipper_available_tabs, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name", "code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class CompanyApp(models.Model):
    class Status(models.TextChoices):
        INVITED = "INVITED", "Invited"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"
        DELETED = "DELETED", "Deleted"

    code = models.CharField(max_length=40, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.INVITED,
        db_index=True,
    )
    enabled_tabs = models.JSONField(default=default_company_tabs, blank=True)
    enabled_shippers = models.JSONField(default=default_enabled_shippers, blank=True)
    enabled_shipper_tabs = models.JSONField(default=dict, blank=True)
    signup_token = models.CharField(
        max_length=64,
        default=new_company_signup_token,
        unique=True,
        db_index=True,
    )
    representative_user = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="representative_company_apps",
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    signup_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_company_apps",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_company_apps",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    delete_retention_until = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_company_apps",
    )
    restored_at = models.DateTimeField(null=True, blank=True)
    restored_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restored_company_apps",
    )
    terms_agreed_at = models.DateTimeField(null=True, blank=True)
    privacy_policy_agreed_at = models.DateTimeField(null=True, blank=True)
    location_terms_agreed_at = models.DateTimeField(null=True, blank=True)
    data_processing_agreed_at = models.DateTimeField(null=True, blank=True)
    marketing_agreed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_company_apps",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "code"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_core_company(self):
        return self.code in CORE_COMPANY_APP_CODES

    @property
    def is_active_company(self):
        return self.status == self.Status.ACTIVE and self.deleted_at is None


class CompanyTenant(models.Model):
    """Central registry for the future company tenant schema rollout."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        READY = "READY", "Ready"
        ACTIVE = "ACTIVE", "Active"
        ERROR = "ERROR", "Error"
        DISABLED = "DISABLED", "Disabled"

    company_app = models.OneToOneField(
        CompanyApp,
        on_delete=models.CASCADE,
        related_name="tenant",
    )
    schema_name = models.CharField(max_length=63, unique=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )
    routing_enabled = models.BooleanField(default=False, db_index=True)
    last_migrated_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company_app__code"]

    def __str__(self):
        return f"{self.company_app.code} -> {self.schema_name}"


class Team(models.Model):
    """조/팀 정보."""

    COMPANY_APP_CHOICES = (
        ("cheonha", "CHEONHA"),
        ("abc", "ABC"),
    )

    code = models.CharField("팀 코드", max_length=10)
    name = models.CharField("팀명", max_length=100)
    company_app = models.CharField(
        "회사 앱 코드",
        max_length=40,
        default="cheonha",
        db_index=True,
    )
    shipper_code = models.CharField(
        "Shipper code",
        max_length=40,
        default="kurly",
        db_index=True,
    )
    leader = models.OneToOneField(
        "User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="led_team",
        verbose_name="팀장",
    )
    receive_price = models.DecimalField(
        "수신단가(박스당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="고객사로부터 받는 박스당 금액",
    )
    pay_price = models.DecimalField(
        "지급단가(박스당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="정규 기사에게 지급하는 박스당 금액",
    )
    default_overtime_cost = models.DecimalField(
        "기본 조정비용",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="기사 1명당 기본 조정 비용",
    )
    yongcha_pay_price = models.DecimalField(
        "용차 기본 지급단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="기존 용차 기사 공통 fallback 지급단가",
    )
    round_1_yongcha_pay_price = models.DecimalField(
        "정규 배송원 1회차 용차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="정규 배송원이 1회차만 용차인 경우 적용할 가구당 단가",
    )
    round_2_yongcha_pay_price = models.DecimalField(
        "정규 배송원 2회차 용차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="정규 배송원이 2회차만 용차인 경우 적용할 가구당 단가",
    )
    round_3_yongcha_pay_price = models.DecimalField(
        "정규 배송원 3회차 용차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="정규 배송원이 3회차만 용차인 경우 적용할 가구당 단가",
    )
    yongcha_round_1_pay_price = models.DecimalField(
        "용차 배송원 1회차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="용차 배송원의 1회차 가구당 단가",
    )
    yongcha_round_2_pay_price = models.DecimalField(
        "용차 배송원 2회차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="용차 배송원의 2회차 가구당 단가",
    )
    yongcha_round_3_pay_price = models.DecimalField(
        "용차 배송원 3회차 단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=3000,
        help_text="용차 배송원의 3회차 가구당 단가",
    )
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "팀"
        verbose_name_plural = "팀"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company_app", "code"],
                name="accounts_team_company_app_code_uniq",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUserManager(BaseUserManager):
    """사용자 매니저."""

    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("사용자명은 필수입니다.")
        if not email:
            raise ValueError("이메일은 필수입니다.")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("슈퍼유저는 is_staff=True 여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("슈퍼유저는 is_superuser=True 여야 합니다.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """사용자 모델."""

    ROLE_CHOICES = (
        ("ADMIN", "관리자"),
        ("APPROVER", "확인자"),
        ("TEAM_LEADER", "팀장"),
        ("CREW", "배송원"),
    )

    role = models.CharField("역할", max_length=20, choices=ROLE_CHOICES, default="CREW")
    company_app = models.CharField(
        "Company app code",
        max_length=40,
        default="cheonha",
        db_index=True,
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="팀",
    )
    phone = models.CharField("전화번호", max_length=20, blank=True)
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    objects = CustomUserManager()

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def has_team(self):
        return self.team is not None

    def is_team_leader(self):
        return self.role == "TEAM_LEADER"

    def is_admin(self):
        return self.role == "ADMIN"

    def is_approver(self):
        return self.role == "APPROVER"
