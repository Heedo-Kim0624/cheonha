from django.contrib import admin
from .models import Region, RegionPrice, PriceHistory


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'team', 'is_active')
    list_filter = ('team', 'is_active')
    search_fields = ('code', 'name')
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'team')
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
    ordering = ('team', 'code')


@admin.register(RegionPrice)
class RegionPriceAdmin(admin.ModelAdmin):
    list_display = ('region', 'delivery_type', 'receive_price', 'pay_price', 'start_date', 'end_date')
    list_filter = ('delivery_type', 'start_date', 'region__team')
    search_fields = ('region__code', 'region__name')
    fieldsets = (
        ('기본 정보', {
            'fields': ('region', 'delivery_type')
        }),
        ('단가', {
            'fields': ('receive_price', 'pay_price')
        }),
        ('기간', {
            'fields': ('start_date', 'end_date')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    ordering = ('-start_date', 'region')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('region_price', 'field_changed', 'old_value', 'new_value', 'changed_by', 'changed_at')
    list_filter = ('field_changed', 'changed_at')
    search_fields = ('region_price__region__code', 'changed_by__username')
    readonly_fields = ('changed_at', 'changed_by')
    ordering = ('-changed_at',)
    fieldsets = (
        ('이력 정보', {
            'fields': ('region_price', 'field_changed', 'old_value', 'new_value')
        }),
        ('변경 정보', {
            'fields': ('changed_by', 'changed_at')
        }),
    )
