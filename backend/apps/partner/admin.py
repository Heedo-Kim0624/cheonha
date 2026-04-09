from django.contrib import admin
from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_number', 'contract_start', 'contract_end', 'is_active')
    list_filter = ('is_active', 'contract_start', 'contract_end')
    search_fields = ('name', 'business_number')
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'business_number')
        }),
        ('계약 정보', {
            'fields': ('contract_start', 'contract_end')
        }),
        ('상태', {
            'fields': ('is_active',)
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
    ordering = ('name',)
