from rest_framework import serializers
from .models import DispatchUpload, DispatchRecord
from .date_utils import date_iso, to_work_date


class DispatchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchRecord
        fields = [
            'id', 'row_num', 'delivery_type', 'partner_name', 'manager_name',
            'sub_region', 'detail_region', 'households', 'boxes',
            'original_boxes', 'is_split', 'split_group',
            'is_overtime', 'is_yongcha', 'is_valid', 'error_message', 'created_at'
        ]
        read_only_fields = ['created_at']


class DispatchUploadSerializer(serializers.ModelSerializer):
    records = DispatchRecordSerializer(many=True, read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = DispatchUpload
        fields = [
            'id', 'file', 'original_filename', 'shipper_code', 'input_type', 'raw_text', 'dispatch_date',
            'source_date', 'dispatch_time', 'round_no',
            'mor_total_boxes', 'mor_regular_crew_count', 'mor_yongcha_crew_count',
            'uploaded_by', 'uploaded_by_name', 'team', 'team_name',
            'upload_date', 'total_rows', 'success_rows', 'error_rows',
            'status', 'note', 'records', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uploaded_by', 'upload_date', 'total_rows', 'success_rows', 'error_rows',
            'source_date', 'dispatch_time', 'round_no',
            'input_type', 'raw_text',
            'mor_total_boxes', 'mor_regular_crew_count', 'mor_yongcha_crew_count',
            'created_at', 'updated_at'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        delivery_date = instance.dispatch_date
        work_date = to_work_date(delivery_date)
        data['work_date'] = date_iso(work_date)
        data['delivery_date'] = date_iso(delivery_date)
        data['dispatch_date'] = date_iso(delivery_date)
        return data


class DispatchUploadSummarySerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = DispatchUpload
        fields = [
            'id', 'original_filename', 'shipper_code', 'input_type', 'dispatch_date',
            'source_date', 'dispatch_time', 'round_no',
            'mor_total_boxes', 'mor_regular_crew_count', 'mor_yongcha_crew_count',
            'uploaded_by', 'uploaded_by_name', 'team', 'team_name',
            'upload_date', 'total_rows', 'success_rows', 'error_rows',
            'status', 'note', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        delivery_date = instance.dispatch_date
        work_date = to_work_date(delivery_date)
        data['work_date'] = date_iso(work_date)
        data['delivery_date'] = date_iso(delivery_date)
        data['dispatch_date'] = date_iso(delivery_date)
        return data


class DispatchUploadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispatchUpload
        fields = ['file', 'team', 'note', 'shipper_code']
        extra_kwargs = {
            'team': {'required': False, 'allow_null': True},
            'shipper_code': {'required': False},
        }


class DispatchValidationSerializer(serializers.Serializer):
    upload_id = serializers.IntegerField()
    validate_all = serializers.BooleanField(default=True)
