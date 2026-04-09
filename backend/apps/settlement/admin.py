from django.contrib import admin
from .models import Settlement, SettlementDetail


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('id', 'team', 'period_start', 'period_end', 'status', 'total_profit', 'confirmed_by')
    list_filter = ('status', 'team', 'period_start', 'confirmed_at')
    search_fields = ('team__name',)
    readonly_fields = ('total_receive', 'total_pay', 'total_overtime', 'total_profit', 'created_at', 'updated_at', 'confirmed_at')
    fieldsets = (
        ('기본 정보', {
            'fields': ('team', 'period_start', 'period_end')
        }),
        ('정산 액', {
            'fields': ('total_receive', 'total_pay', 'total_overtime', 'total_profit')
        }),
        ('상태', {
            'fields': ('status', 'confirmed_by', 'confirmed_at')
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
    ordering = ('-period_start',)


@admin.register(SettlementDetail)
class SettlementDetailAdmin(admin.ModelAdmin):
    list_display = ('settlement', 'crew_member', 'region', 'delivery_type', 'boxes', 'profit')
    list_filter = ('delivery_type', 'settlement__period_start')
    search_fields = ('crew_member__code', 'crew_member__name', 'region')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('정산 정보', {
            'fields': ('settlement', 'crew_member', 'region', 'delivery_type')
        }),
        ('수량', {
            'fields': ('boxes',)
        }),
        ('금액', {
            'fields': ('receive_amount', 'pay_amount', 'overtime_cost', 'profit')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    ordering = ('settlement', 'crew_member')
