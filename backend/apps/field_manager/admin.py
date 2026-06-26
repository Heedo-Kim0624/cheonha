from django.contrib import admin

from .models import FieldManagerAccount, FieldManagerSession


@admin.register(FieldManagerAccount)
class FieldManagerAccountAdmin(admin.ModelAdmin):
    list_display = (
        'company',
        'team_code',
        'display_phone',
        'name',
        'is_active',
        'last_login_at',
        'updated_at',
    )
    list_filter = ('company', 'team_code', 'is_active')
    search_fields = ('team_code', 'phone', 'display_phone', 'name', 'memo')
    readonly_fields = ('last_login_at', 'created_at', 'updated_at')


@admin.register(FieldManagerSession)
class FieldManagerSessionAdmin(admin.ModelAdmin):
    list_display = ('company_code', 'team_code', 'phone', 'account', 'ip_address', 'logged_in_at')
    list_filter = ('company_code', 'team_code')
    search_fields = ('company_code', 'team_code', 'phone', 'account__name', 'account__display_phone')
    readonly_fields = ('logged_in_at',)
