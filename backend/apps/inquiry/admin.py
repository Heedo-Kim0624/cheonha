from django.contrib import admin
from .models import SettlementInquiry, InquiryMessage


@admin.register(SettlementInquiry)
class SettlementInquiryAdmin(admin.ModelAdmin):
    list_display = ['crew_name', 'team_name', 'dispatch_date', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'team_name']
    search_fields = ['crew_name']


@admin.register(InquiryMessage)
class InquiryMessageAdmin(admin.ModelAdmin):
    list_display = ['inquiry', 'author_type', 'author_name', 'created_at']
