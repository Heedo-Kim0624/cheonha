from django.contrib import admin

from .models import MobileAppUser


@admin.register(MobileAppUser)
class MobileAppUserAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "team_code",
        "status",
        "requested_at",
        "approved_at",
        "is_active",
    ]
    list_filter = ["status", "team_code", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["requested_at"]
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="선택한 요청을 승인합니다")
    def approve_selected(self, request, queryset):
        from django.utils import timezone

        queryset.update(
            status=MobileAppUser.Status.APPROVED,
            approved_at=timezone.now(),
            approved_by=request.user,
        )

    @admin.action(description="선택한 요청을 거절합니다")
    def reject_selected(self, request, queryset):
        queryset.update(status=MobileAppUser.Status.REJECTED)
