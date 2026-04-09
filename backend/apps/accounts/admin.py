from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'leader', 'default_overtime_cost', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('code',)
    fieldsets = (
        ('기본 정보', {
            'fields': ('code', 'name', 'leader')
        }),
        ('단가 설정', {
            'fields': ('default_overtime_cost',)
        }),
        ('상태', {
            'fields': ('is_active',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'team', 'is_active')
    list_filter = ('role', 'team', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        ('로그인 정보', {
            'fields': ('username', 'password')
        }),
        ('개인 정보', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('역할 및 팀', {
            'fields': ('role', 'team')
        }),
        ('권한 및 상태', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    ordering = ('-created_at',)
