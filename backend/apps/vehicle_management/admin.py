from django.contrib import admin
from .models import (
    Company, Vehicle, PitRecord, CalendarEvent,
    SubscriptionRequest, SubscriptionRequestVehicle,
    ReturnRequest, ASRequest,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'company', 'fleet', 'driver', 'hgi',
                    'placement_status', 'operation_type')
    list_filter = ('company', 'placement_status', 'operation_type', 'fleet')
    search_fields = ('vehicle_number', 'vin_tid', 'driver', 'hgi')


@admin.register(PitRecord)
class PitRecordAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number_short', 'company', 'reason', 'in_date',
                    'out_date', 'is_in_pit', 'note_highlight')
    list_filter = ('company', 'reason', 'note_highlight')
    search_fields = ('vehicle_number_short', 'note')
    raw_id_fields = ('vehicle', 'created_by')


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('event_date', 'event_time', 'company', 'kind', 'title')
    list_filter = ('company', 'kind', 'event_date')
    search_fields = ('title', 'body')


@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = ('team_code', 'phone', 'company', 'requested_date',
                    'quantity', 'status')
    list_filter = ('company', 'status')


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('team_code', 'phone', 'company', 'vehicle_number',
                    'hope_date', 'hope_time', 'status')
    list_filter = ('company', 'status')


@admin.register(ASRequest)
class ASRequestAdmin(admin.ModelAdmin):
    list_display = ('team_code', 'phone', 'company', 'vehicle_number', 'status')
    list_filter = ('company', 'status')


admin.site.register(SubscriptionRequestVehicle)
