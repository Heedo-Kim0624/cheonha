from django.contrib import admin

from .models import OneDriver, OneDriverStatementOverride, OneSettlementUpload, OneShipmentOrder


@admin.register(OneDriver)
class OneDriverAdmin(admin.ModelAdmin):
    list_display = ("name", "company_app", "is_active", "updated_at")
    list_filter = ("company_app", "is_active")
    search_fields = ("name",)


@admin.register(OneSettlementUpload)
class OneSettlementUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company_app",
        "shipper_code",
        "month",
        "delivery_date",
        "original_filename",
        "status",
        "order_count",
        "total_amount",
        "created_at",
    )
    list_filter = ("company_app", "shipper_code", "month", "status")
    search_fields = ("original_filename", "raw_hash")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OneShipmentOrder)
class OneShipmentOrderAdmin(admin.ModelAdmin):
    list_display = (
        "delivery_date",
        "driver_name",
        "fee_name",
        "service_code",
        "category_code",
        "boxes",
        "amount",
        "is_mapped",
    )
    list_filter = ("company_app", "month", "service_code", "category_code", "is_mapped")
    search_fields = ("driver_name", "order_number", "fee_name")


@admin.register(OneDriverStatementOverride)
class OneDriverStatementOverrideAdmin(admin.ModelAdmin):
    list_display = ("company_app", "month", "driver", "payment_due_date", "updated_at")
    list_filter = ("company_app", "month")
    search_fields = ("driver__name",)

