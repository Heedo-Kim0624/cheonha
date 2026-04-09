from rest_framework import serializers


class AuditSerializer(serializers.Serializer):
    """감시 정보 serializer"""
    created_by = serializers.StringRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
