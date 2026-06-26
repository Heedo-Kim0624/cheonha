from rest_framework import serializers

from .constants import CATEGORY_LABELS, SERVICE_LABELS
from .models import OneDriver, OneDriverStatementOverride, OneSettlementUpload


class OneSettlementUploadSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True, default="")

    class Meta:
        model = OneSettlementUpload
        fields = [
            "id",
            "company_app",
            "shipper_code",
            "month",
            "delivery_date",
            "original_filename",
            "raw_hash",
            "total_rows",
            "order_count",
            "mapped_order_count",
            "unmapped_order_count",
            "total_amount",
            "validation_errors",
            "status",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["total_amount"] = int(instance.total_amount or 0)
        return data


class OneDriverSerializer(serializers.ModelSerializer):
    households = serializers.IntegerField(read_only=True)
    boxes = serializers.IntegerField(read_only=True)
    extra_boxes = serializers.IntegerField(read_only=True)
    amount = serializers.IntegerField(read_only=True)
    source_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = OneDriver
        fields = [
            "id",
            "name",
            "company_app",
            "is_active",
            "households",
            "boxes",
            "extra_boxes",
            "amount",
            "source_amount",
        ]
        read_only_fields = fields


class OneStatementOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneDriverStatementOverride
        fields = ["id", "payment_due_date", "manual_items", "memo", "updated_at"]
        read_only_fields = ["id", "updated_at"]


def enrich_statement_labels(statement):
    for row in statement.get("summary_rows", []):
        row["service_label"] = SERVICE_LABELS.get(row.get("service_code"), row.get("service_code"))
        row["category_label"] = CATEGORY_LABELS.get(row.get("category_code"), row.get("category_code"))
    return statement
