from django.contrib import admin
from .models import CrewMember, OvertimeSetting, YongchaPayGroup


@admin.register(YongchaPayGroup)
class YongchaPayGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "company_app", "exclude_base_pay_on_multi_round", "is_active", "updated_at")
    list_filter = ("company_app", "exclude_base_pay_on_multi_round", "is_active")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(CrewMember)
class CrewMemberAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'team', 'partner', 'phone', 'vehicle_number', 'vehicle_inspection_date', 'is_yongcha', 'is_active', 'is_new')
    list_filter = ('team', 'partner', 'is_yongcha', 'is_active', 'is_new')
    search_fields = ('code', 'name', 'phone', 'vehicle_number')
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'phone', 'vehicle_number')
        }),
        ('급여/차량 관리', {
            'fields': ('bank_name', 'bank_account_number', 'bank_account_holder', 'vehicle_inspection_date')
        }),
        ('소속 정보', {
            'fields': ('team', 'partner', 'region')
        }),
        ('상태', {
            'fields': ('is_active', 'is_new', 'is_yongcha')
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
