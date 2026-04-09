from django.contrib import admin
from .models import CrewMember, OvertimeSetting


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'team', 'partner', 'phone', 'is_active', 'is_new')
    list_filter = ('team', 'partner', 'is_active', 'is_new')
    search_fields = ('code', 'name', 'phone', 'vehicle_number')
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'phone', 'vehicle_number')
        }),
        ('소속 정보', {
            'fields': ('team', 'partner', 'region')
        }),
        ('상태', {
            'fields': ('is_active', 'is_new')
        }),
        ('메모', {
            'fields': ('note',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    ordering = ('code',)


@admin.register(OvertimeSetting)
class OvertimeSettingAdmin(admin.ModelAdmin):
    list_display = ('dispatch_upload', 'crew_member', 'is_overtime', 'overtime_cost')
    list_filter = ('is_overtime', 'dispatch_upload__upload_date')
    search_fields = ('crew_member__code', 'crew_member__name')
    fieldsets = (
        ('배치', {
            'fields': ('dispatch_upload', 'crew_member')
        }),
        ('연장근무', {
            'fields': ('is_overtime', 'overtime_cost')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    ordering = ('dispatch_upload', 'crew_member')
