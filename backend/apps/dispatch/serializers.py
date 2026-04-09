from rest_framework import serializers
from .models import DispatchUpload, DispatchRecord


class DispatchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchRecord
        fields = [
            'id', 'row_num', 'delivery_type', 'partner_name', 'manager_name',
            'sub_region', 'detail_region', 'households', 'boxes',
            'original_boxes', 'is_split', 'split_group',
            'is_overtime', 'is_valid', 'error_message', 'created_at'
        ]
        read_only_fields = ['created_at']


class DispatchUploadSerializer(serializers.ModelSerializer):
    records = DispatchRecordSerializer(many=True, read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = DispatchUpload
        fields = [
            'id', 'file', 'original_filename', 'dispatch_date',
            'uploaded_by', 'uploaded_by_name', 'team', 'team_name',
            'upload_date', 'total_rows', 'success_rows', 'error_rows',
            'status', 'note', 'records', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uploaded_by', 'upload_date', 'total_rows', 'success_rows', 'error_rows', 'created_at', 'updated_at']


class DispatchUploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchUpload
        fields = ['file', 'team', 'note']
        extra_kwargs = {
            'team': {'required': False, 'allow_null': True},
        }


class DispatchValidationSerializer(serializers.Serializer):
    upload_id = serializers.IntegerField()
    validate_all = serializers.BooleanField(default=True)
