from django.conf import settings
from django.db import models

from .app_messages import merge_mobile_app_messages


LEGAL_DOCUMENT_VERSION = "2026-06-04"
LEGAL_DOCUMENTS = {
    "web_terms": ("WEB", "CLEVER 관리자 회원 서비스 이용약관", "/terms/"),
    "app_terms": ("APP", "CLEVER 배송원 회원 서비스 이용약관", "/driver-terms/"),
    "privacy_policy": ("WEB/APP", "개인정보 처리방침", "/privacy/"),
    "location_terms": ("WEB/APP", "위치기반서비스 이용약관", "/location-terms/"),
    "data_processing": ("WEB/APP", "제3자 정보제공 동의", "/data-processing/"),
    "marketing_consent": ("WEB/APP", "마케팅 및 이벤트 정보 수신 동의", "/marketing-consent/"),
}


class MobileAppUser(models.Model):
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
    device_token = models.CharField("푸시 토큰", max_length=255, blank=True, null=True)
    last_app_version = models.CharField("앱 버전", max_length=40, blank=True)
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
    last_login_at = models.DateTimeField("최근 로그인", blank=True, null=True)
    is_active = models.BooleanField("활성 상태", default=True)
    signup_completed = models.BooleanField("회원가입 완료", default=False)
    signup_completed_at = models.DateTimeField("회원가입 완료 시각", blank=True, null=True)
    privacy_policy_agreed_at = models.DateTimeField(
        "개인정보처리방침 동의 시각",
        blank=True,
        null=True,
    )
    terms_agreed_at = models.DateTimeField(
        "이용약관 동의 시각",
        blank=True,
        null=True,
    )

    third_party_information_agreed_at = models.DateTimeField(
        "제3자 정보제공 동의 시각",
        blank=True,
        null=True,
    )
    location_terms_agreed_at = models.DateTimeField(
        "위치정보기반 서비스 이용약관 동의 시각",
        blank=True,
        null=True,
    )
    marketing_event_agreed_at = models.DateTimeField(
        "마케팅 및 이벤트 정보 수신 동의 시각",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "mobile_app_users"
        verbose_name = "모바일 앱 사용자"
        verbose_name_plural = "모바일 앱 사용자"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.name} ({self.team_code}조 - {self.get_status_display()})"


class MobilePassword(models.Model):
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


class MobileAppMessageConfig(models.Model):
    message_overrides = models.JSONField("앱 메시지 덮어쓰기", default=dict, blank=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        db_table = "mobile_app_message_config"
        verbose_name = "모바일 앱 메시지 설정"
        verbose_name_plural = "모바일 앱 메시지 설정"

    def __str__(self):
        return "모바일 앱 메시지 설정"

    @classmethod
    def get_solo(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance

    @property
    def merged_messages(self):
        return merge_mobile_app_messages(self.message_overrides)


class MobileWorkSessionCheckpoint(models.Model):
    crew_member = models.OneToOneField(
        "crew.CrewMember",
        on_delete=models.CASCADE,
        related_name="mobile_work_session_checkpoint",
    )
    vehicle_number = models.CharField(max_length=20, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    csv_path = models.CharField(max_length=500, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    csv_bytes = models.PositiveIntegerField(default=0)
    app_version = models.CharField(max_length=40, blank=True)
    background_location_granted = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mobile_work_session_checkpoints"
        verbose_name = "모바일 근무 세션 임시 저장"
        verbose_name_plural = "모바일 근무 세션 임시 저장"
        ordering = ["-last_synced_at"]

    def __str__(self):
        return f"{self.crew_member} checkpoint {self.sample_count} rows"


class LegalDocumentVersionLog(models.Model):
    document_key = models.CharField(max_length=50, db_index=True)
    audience = models.CharField(max_length=20, db_index=True)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=20, db_index=True)
    public_url = models.CharField(max_length=255)
    source_filename = models.CharField(max_length=255, blank=True)
    effective_date = models.DateField()
    change_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "legal_document_version_logs"
        ordering = ["-effective_date", "document_key"]
        unique_together = [("document_key", "version")]

    def __str__(self):
        return f"{self.document_key} {self.version}"


class LegalConsentHistory(models.Model):
    class SubjectType(models.TextChoices):
        MOBILE_USER = "MOBILE_USER", "Mobile user"
        COMPANY_APP = "COMPANY_APP", "Company app"

    subject_type = models.CharField(max_length=20, choices=SubjectType.choices, db_index=True)
    subject_identifier = models.CharField(max_length=120, db_index=True)
    mobile_user = models.ForeignKey(
        "mobile.MobileAppUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legal_consent_histories",
    )
    company_app = models.ForeignKey(
        "accounts.CompanyApp",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legal_consent_histories",
    )
    agreement_key = models.CharField(max_length=60, db_index=True)
    document_key = models.CharField(max_length=50, db_index=True)
    document_version = models.CharField(max_length=20, db_index=True)
    agreed = models.BooleanField(default=True)
    agreed_at = models.DateTimeField(db_index=True)
    app_version = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "legal_consent_histories"
        ordering = ["-agreed_at", "-id"]

    def __str__(self):
        return f"{self.subject_identifier} {self.agreement_key} {self.document_version}"


def ensure_legal_document_version_logs():
    from datetime import date

    source_files = {
        "web_terms": "260604 CLEVER 관리자 회원 서비스 이용약관.docx",
        "app_terms": "260604 CLEVER 배송원 회원 서비스 이용약관.docx",
        "privacy_policy": "260604 이브이앤솔루션 개인정보 처리방침.docx",
        "location_terms": "260604 이브이앤솔루션 위치기반서비스 이용약관.docx",
        "data_processing": "260604 이브이앤솔루션 개인정보 처리방침.docx",
        "marketing_consent": "260604 이브이앤솔루션 개인정보 처리방침.docx",
    }
    for document_key, (audience, title, public_url) in LEGAL_DOCUMENTS.items():
        LegalDocumentVersionLog.objects.get_or_create(
            document_key=document_key,
            version=LEGAL_DOCUMENT_VERSION,
            defaults={
                "audience": audience,
                "title": title,
                "public_url": public_url,
                "source_filename": source_files.get(document_key, ""),
                "effective_date": date(2026, 6, 4),
                "change_note": "260604 이용약관 및 개인정보처리방침 최종본 반영",
            },
        )


def record_legal_consent_history(
    *,
    subject_type,
    subject_identifier,
    agreement_key,
    document_key,
    agreed_at,
    agreed=True,
    mobile_user=None,
    company_app=None,
    app_version="",
    request=None,
):
    ip_address = None
    user_agent = ""
    if request is not None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (forwarded_for.split(",", 1)[0].strip() or request.META.get("REMOTE_ADDR") or None)
        user_agent = request.META.get("HTTP_USER_AGENT", "")
    ensure_legal_document_version_logs()
    return LegalConsentHistory.objects.create(
        subject_type=subject_type,
        subject_identifier=subject_identifier,
        mobile_user=mobile_user,
        company_app=company_app,
        agreement_key=agreement_key,
        document_key=document_key,
        document_version=LEGAL_DOCUMENT_VERSION,
        agreed=agreed,
        agreed_at=agreed_at,
        app_version=app_version or "",
        ip_address=ip_address,
        user_agent=user_agent,
    )
