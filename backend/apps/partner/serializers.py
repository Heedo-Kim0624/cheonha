from rest_framework import serializers
from .models import Partner


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'business_number', 'contract_start', 'contract_end',
            'is_active', 'note', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
