from django.db import models

from apps.accounts.models import Team
from apps.common.models import AuditMixin
from apps.partner.models import Partner


class YongchaPayGroup(AuditMixin):
    """Reusable yongcha team pay rule."""

    company_app = models.CharField(max_length=40, default="cheonha", db_index=True)
    name = models.CharField(max_length=100)
    round_1_base_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    round_1_base_households = models.PositiveIntegerField(default=0)
    round_1_extra_household_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    round_2_base_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    round_2_base_households = models.PositiveIntegerField(default=0)
    round_2_extra_household_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    round_3_base_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    round_3_base_households = models.PositiveIntegerField(default=0)
    round_3_extra_household_pay = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    exclude_base_pay_on_multi_round = models.BooleanField(
        default=False,
        help_text="체크 시 같은 날 여러 용차 회차를 수행하면 기본급 없이 추가 착당 단가만 적용합니다.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "crew_yongcha_pay_group"
        ordering = ["company_app", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company_app", "name"],
                name="crew_yongcha_pay_group_company_name_uniq",
            )
        ]

    def __str__(self):
        return self.name


class CrewMember(AuditMixin):
    """배송원 관리."""

    code = models.CharField("배송원코드", max_length=50)
    name = models.CharField("배송원명", max_length=100)
    phone = models.CharField("전화번호", max_length=20, blank=True)
    vehicle_number = models.CharField("차량번호", max_length=20, blank=True)
    bank_name = models.CharField("급여 은행", max_length=50, blank=True)
    bank_account_number = models.CharField("급여 계좌번호", max_length=100, blank=True)
    bank_account_holder = models.CharField("예금주", max_length=50, blank=True)
    vehicle_inspection_date = models.DateField("자동차 검사일", null=True, blank=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="조",
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crew_members",
        verbose_name="파트너사",
    )
    pay_price = models.DecimalField(
        "지급단가(박스당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="정규 배송원에게 지급하는 박스당 금액",
    )
    yongcha_pay_price = models.DecimalField(
        "용차 기본 지급단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="기존 호환용 fallback 용차 단가",
    )
    yongcha_pay_group = models.ForeignKey(
        YongchaPayGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crew_members",
        verbose_name="용차 팀단가",
    )
    regular_round_1_base_pay = models.DecimalField("1회차 정규 고정급", max_digits=12, decimal_places=0, default=0)
    regular_round_2_base_pay = models.DecimalField("2회차 정규 고정급", max_digits=12, decimal_places=0, default=0)
    regular_round_3_base_pay = models.DecimalField("3회차 정규 고정급", max_digits=12, decimal_places=0, default=0)
    personal_round_1_yongcha_pay_price = models.DecimalField(
        "1회차 개인 용차 지급단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="개별 배송원의 1회차 용차 지급단가 override 값",
    )
    personal_round_2_yongcha_pay_price = models.DecimalField(
        "2회차 개인 용차 지급단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="개별 배송원의 2회차 용차 지급단가 override 값",
    )
    personal_round_3_yongcha_pay_price = models.DecimalField(
        "3회차 개인 용차 지급단가(가구당)",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="개별 배송원의 3회차 용차 지급단가 override 값",
    )
    round_1_is_yongcha = models.BooleanField("1회차 용차", default=False)
    round_2_is_yongcha = models.BooleanField("2회차 용차", default=False)
    round_3_is_yongcha = models.BooleanField("3회차 용차", default=False)
    region = models.CharField("권역", max_length=50, blank=True)
    is_active = models.BooleanField("활성화", default=True)
    is_new = models.BooleanField("신규", default=False)
    is_yongcha = models.BooleanField("용차 여부", default=False, db_index=True)
    two_insurance_percent = models.DecimalField(
        "2대보험 공제율(%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="정산 캘린더에서 지급금액 대비 실지급금액을 계산할 때 사용하는 공제율",
    )
    note = models.TextField("메모", blank=True)

    class Meta:
        verbose_name = "배송원"
        verbose_name_plural = "배송원"
        ordering = ["code"]
        db_table = "crew_crewmember"
        unique_together = ("code", "team")

    def __str__(self):
        return f"{self.code} - {self.name}"


class OvertimeSetting(AuditMixin):
    """연장근무 설정."""

    dispatch_upload = models.ForeignKey(
        "dispatch.DispatchUpload",
        on_delete=models.CASCADE,
        related_name="overtime_settings",
        verbose_name="배차 업로드",
    )
    crew_member = models.ForeignKey(
        CrewMember,
        on_delete=models.CASCADE,
        related_name="overtime_settings",
        verbose_name="배송원",
    )
    is_overtime = models.BooleanField("연장근무 여부", default=False)
    overtime_cost = models.DecimalField(
        "연장근무 비용",
        max_digits=12,
        decimal_places=0,
        default=0,
        help_text="원 단위",
    )

    class Meta:
        verbose_name = "연장근무 설정"
        verbose_name_plural = "연장근무 설정"
        ordering = ["dispatch_upload", "crew_member"]
        db_table = "crew_overtimesetting"
        unique_together = ("dispatch_upload", "crew_member")

    def __str__(self):
        return f"{self.dispatch_upload} - {self.crew_member}"
