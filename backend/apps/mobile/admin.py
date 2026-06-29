from django.contrib import admin

from .models import (
    LegalConsentHistory,
    LegalDocumentVersionLog,
    MobileAppMessageConfig,
    MobileAppUser,
    MobileWorkSessionCheckpoint,
)


@admin.register(MobileAppUser)
class MobileAppUserAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "team_code",
        "status",
        "signup_completed",
        "third_party_information_agreed_at",
        "location_terms_agreed_at",
        "marketing_event_agreed_at",
        "requested_at",
        "approved_at",
        "is_active",
    ]
    list_filter = ["status", "team_code", "signup_completed", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["requested_at"]
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="선택한 요청을 승인합니다.")
    def approve_selected(self, request, queryset):
        from django.utils import timezone

        queryset.update(
            status=MobileAppUser.Status.APPROVED,
            approved_at=timezone.now(),
            approved_by=request.user,
        )

    @admin.action(description="선택한 요청을 거절합니다.")
    def reject_selected(self, request, queryset):
        queryset.update(status=MobileAppUser.Status.REJECTED)


@admin.register(MobileAppMessageConfig)
class MobileAppMessageConfigAdmin(admin.ModelAdmin):
    list_display = ["id", "updated_at", "created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(MobileWorkSessionCheckpoint)
class MobileWorkSessionCheckpointAdmin(admin.ModelAdmin):
    list_display = [
        "crew_member",
        "vehicle_number",
        "sample_count",
        "csv_bytes",
        "app_version",
        "last_synced_at",
        "updated_at",
    ]
    search_fields = ["crew_member__name", "crew_member__code", "vehicle_number", "file_name"]
    readonly_fields = ["created_at", "updated_at", "last_synced_at"]


@admin.register(LegalDocumentVersionLog)
class LegalDocumentVersionLogAdmin(admin.ModelAdmin):
    list_display = ["document_key", "audience", "version", "title", "effective_date", "public_url"]
    list_filter = ["audience", "version", "effective_date"]
    search_fields = ["document_key", "title", "source_filename", "public_url"]
    readonly_fields = ["created_at"]


@admin.register(LegalConsentHistory)
class LegalConsentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "subject_type",
        "subject_identifier",
        "agreement_key",
        "document_key",
        "document_version",
        "agreed",
        "agreed_at",
    ]
    list_filter = ["subject_type", "agreement_key", "document_key", "document_version", "agreed"]
    search_fields = ["subject_identifier", "agreement_key", "document_key"]
    readonly_fields = ["created_at"]
