from django.contrib import admin

from .models import PointRedemption, PointTransaction


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("crew_member", "points", "kind", "work_date", "redemption", "created_at")
    list_filter = ("kind", "work_date", "crew_member__team")
    search_fields = ("crew_member__name", "crew_member__code", "memo")
    date_hierarchy = "created_at"


@admin.register(PointRedemption)
class PointRedemptionAdmin(admin.ModelAdmin):
    list_display = ("crew_member", "item_name", "cost_points", "status", "requested_at", "confirmed_at")
    list_filter = ("status", "crew_member__team")
    search_fields = ("crew_member__name", "crew_member__code", "item_name")
    date_hierarchy = "requested_at"
