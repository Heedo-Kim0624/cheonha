from django.contrib import admin
from .models import DispatchUpload, DispatchRecord


@admin.register(DispatchUpload)
class DispatchUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'team', 'uploaded_by', 'upload_date', 'total_rows', 'success_rows', 'error_rows', 'status')
    list_filter = ('status', 'team', 'upload_date')
    search_fields = ('team__name', 'uploaded_by__username')
    readonly_fields = ('upload_date', 'total_rows', 'success_rows', 'error_rows', 'created_at', 'updated_at')
    fieldsets = (
        ('기본 정보', {
            'fields': ('file', 'uploaded_by', 'team', 'upload_date')
        }),
        ('통계', {
            'fields': ('total_rows', 'success_rows', 'error_rows')
        }),
        ('상태', {
            'fields': ('status', 'note')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('-upload_date',)


@admin.register(DispatchRecord)
class DispatchRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'upload', 'row_num', 'delivery_type', 'partner_name', 'boxes', 'is_valid')
    list_filter = ('is_valid', 'delivery_type', 'upload__upload_date')
    search_fields = ('partner_name', 'manager_name', 'sub_region')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('기본 정보', {
            'fields': ('upload', 'row_num')
        }),
        ('배송 정보', {
            'fields': ('delivery_type', 'partner_name', 'manager_name', 'sub_region', 'detail_region', 'households', 'boxes')
        }),
        ('검증', {
            'fields': ('is_valid', 'error_message')
        }),
        ('시간 정보', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    ordering = ('upload', 'row_num')
