from django.contrib import admin
from .models import TrackingSession, LocationPoint, BleLog, CameraCapture, Cycle


@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ('session_date', 'crew_member', 'started_at', 'ended_at', 'cycle_count', 'total_seconds')
    list_filter = ('session_date', 'crew_member__team')
    search_fields = ('crew_member__name', 'crew_member__code', 'crew_member__vehicle_number')
    date_hierarchy = 'session_date'


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ('session', 'cycle_no', 'started_at', 'ended_at', 'sr_seconds', 'dl_seconds', 'capture_count')
    list_filter = ('session__session_date',)


admin.site.register(LocationPoint)
admin.site.register(BleLog)
admin.site.register(CameraCapture)
