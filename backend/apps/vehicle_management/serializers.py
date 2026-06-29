from rest_framework import serializers
from .models import (
    Company, Vehicle, PitRecord, CalendarEvent,
    SubscriptionRequest, SubscriptionRequestVehicle,
    ReturnRequest, ReturnRequestPhoto, ASRequest,
    FleetVehicleRecord, FleetVehicleDocument, FleetSubscriptionContract, FleetReturnRecord,
    FleetInsurancePolicy, FleetAccidentCase,
    FleetInspectionSchedule, FleetProfitRuleVersion, FleetProfitImportBatch,
    FleetProfitRawEntry, FleetProfitAdjustment, FleetProfitMonthlySnapshot,
    FleetMonthlyClose,
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'code', 'name', 'sort_order', 'is_active']


class VehicleSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    placement_status_display = serializers.CharField(source='get_placement_status_display', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    registration_certificate_url = serializers.SerializerMethodField()
    registration_certificate_file_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            'id', 'company', 'company_code', 'company_name',
            'vehicle_number', 'vehicle_number_short', 'vin_tid', 'model',
            'shipped_at', 'fleet', 'driver', 'hgi',
            'registration_certificate_url', 'registration_certificate_file_name',
            'registration_certificate_uploaded_at',
            'placement_status', 'placement_status_display',
            'operation_type', 'operation_type_display',
            'notes', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['vehicle_number_short', 'registration_certificate_uploaded_at']

    def get_registration_certificate_url(self, obj):
        if not obj.registration_certificate:
            return ''
        request = self.context.get('request')
        url = obj.registration_certificate.url
        return request.build_absolute_uri(url) if request else url

    def get_registration_certificate_file_name(self, obj):
        if not obj.registration_certificate:
            return ''
        return obj.registration_certificate.name.rsplit('/', 1)[-1]


class PitRecordSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    is_in_pit = serializers.BooleanField(read_only=True)
    vehicle_placement_status = serializers.CharField(source='vehicle.placement_status', read_only=True)
    vehicle_placement_status_display = serializers.CharField(source='vehicle.get_placement_status_display', read_only=True)

    class Meta:
        model = PitRecord
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_number_short',
            'in_date', 'out_date', 'reason', 'reason_display',
            'vehicle_placement_status', 'vehicle_placement_status_display',
            'note', 'note_highlight', 'is_in_pit',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        in_date = attrs.get('in_date') or getattr(self.instance, 'in_date', None)
        out_date = attrs.get('out_date') or getattr(self.instance, 'out_date', None)
        if in_date and out_date and out_date < in_date:
            raise serializers.ValidationError({'out_date': '출고일은 입고일 이후여야 합니다.'})
        return attrs


class CalendarEventSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'company', 'company_code', 'kind', 'kind_display',
            'event_date', 'event_time', 'title', 'body',
            'related_vehicle', 'related_pit_record',
            'related_subscription', 'related_return', 'related_as',
            'created_at',
        ]


class SubscriptionRequestVehicleSerializer(serializers.ModelSerializer):
    vehicle_number = serializers.CharField(source='vehicle.vehicle_number', read_only=True)

    class Meta:
        model = SubscriptionRequestVehicle
        fields = ['id', 'vehicle', 'vehicle_number']


class SubscriptionRequestSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    matched_vehicles = SubscriptionRequestVehicleSerializer(many=True, read_only=True)
    matched_count = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionRequest
        fields = [
            'id', 'company', 'company_code', 'team_code', 'phone',
            'requested_date', 'quantity',
            'status', 'status_display', 'reject_reason',
            'matched_vehicles', 'matched_count',
            'completed_at', 'created_at', 'updated_at',
        ]

    def get_matched_count(self, obj):
        return obj.matched_vehicles.count()

    def validate_quantity(self, v):
        if v < 1:
            raise serializers.ValidationError('대수는 1대 이상이어야 합니다.')
        return v


class AssignVehiclesSerializer(serializers.Serializer):
    """구독 요청에 차량 매칭 — 요청 대수와 일치해야 함."""
    vehicle_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class RejectSubscriptionSerializer(serializers.Serializer):
    reject_reason = serializers.CharField(required=False, allow_blank=True)


class ReturnRequestPhotoSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    file_name = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequestPhoto
        fields = ['id', 'kind', 'kind_display', 'file_name', 'image_url', 'created_at']

    def get_file_name(self, obj):
        return obj.image.name.rsplit('/', 1)[-1]

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class ReturnRequestSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    photos = ReturnRequestPhotoSerializer(many=True, read_only=True)
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'company', 'company_code', 'team_code', 'phone',
            'vehicle_number', 'reason',
            'hope_date', 'hope_time',
            'confirmed_date', 'confirmed_time',
            'block_reason', 'available_dates',
            'status', 'status_display',
            'photos', 'photo_count',
            'created_at', 'updated_at',
        ]

    def get_photo_count(self, obj):
        return obj.photos.count()

    def validate_hope_time(self, v):
        # 10:00 ~ 16:00 (앱에서도 검증되지만 서버 이중 검증)
        if v.hour < 10 or v.hour >= 17:
            raise serializers.ValidationError('희망 시간은 10:00~16:00 사이여야 합니다.')
        if v.hour == 16 and v.minute > 0:
            raise serializers.ValidationError('희망 시간은 16:00 까지입니다.')
        return v


class ConfirmReturnSerializer(serializers.Serializer):
    confirmed_date = serializers.DateField()
    confirmed_time = serializers.TimeField()


class AdjustReturnSerializer(serializers.Serializer):
    block_reason = serializers.CharField()
    available_dates = serializers.CharField(max_length=128)


class ASRequestSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ASRequest
        fields = [
            'id', 'company', 'company_code', 'team_code', 'phone',
            'vehicle_number', 'owner_name', 'owner_phone', 'reason',
            'admin_comment', 'calendar_note',
            'status', 'status_display',
            'completed_at', 'created_at', 'updated_at',
        ]


class CompleteASSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['REPAIRING', 'OPERATING'])
    admin_comment = serializers.CharField(required=False, allow_blank=True)
    calendar_note = serializers.CharField(required=False, allow_blank=True)


class FleetSubscriptionContractSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    vehicle_number_display = serializers.CharField(source='vehicle.vehicle_number', read_only=True)
    vehicle_vin = serializers.CharField(source='vehicle.vin_tid', read_only=True)
    vehicle_record_vin = serializers.CharField(source='vehicle_record.vin', read_only=True)
    contract_file_name = serializers.SerializerMethodField()
    contract_file_url = serializers.SerializerMethodField()
    clear_contract_file = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = FleetSubscriptionContract
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record', 'vehicle_number',
            'vehicle_number_display', 'vehicle_vin', 'vehicle_record_vin', 'customer', 'contact',
            'start_date', 'end_date', 'monthly_fee', 'deposit',
            'status', 'sign_status', 'contract_file', 'contract_file_name',
            'contract_file_url', 'clear_contract_file', 'note', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_contract_file_name(self, obj):
        if not obj.contract_file:
            return ''
        return obj.contract_file.name.rsplit('/', 1)[-1]

    def get_contract_file_url(self, obj):
        if not obj.contract_file:
            return ''
        request = self.context.get('request')
        url = obj.contract_file.url
        return request.build_absolute_uri(url) if request else url


class FleetVehicleRecordSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    vehicle_number_display = serializers.CharField(source='vehicle.vehicle_number', read_only=True)

    class Meta:
        model = FleetVehicleRecord
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_number',
            'vehicle_number_display', 'vin', 'model', 'start_date', 'end_date',
            'status', 'certificate_name', 'certificate_uploaded_at', 'note',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetVehicleDocumentSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FleetVehicleDocument
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record',
            'vehicle_number', 'document_type', 'file', 'file_name',
            'file_url', 'note', 'created_at', 'uploaded_at',
        ]
        read_only_fields = ['created_at', 'uploaded_at']

    def get_file_name(self, obj):
        if not obj.file:
            return ''
        return obj.file.name.rsplit('/', 1)[-1]

    def get_file_url(self, obj):
        if not obj.file:
            return ''
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class FleetReturnRecordSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    subscription_contract_id = serializers.IntegerField(source='subscription.id', read_only=True)
    vehicle_vin = serializers.CharField(source='vehicle.vin_tid', read_only=True)
    vehicle_record_vin = serializers.CharField(source='vehicle_record.vin', read_only=True)

    class Meta:
        model = FleetReturnRecord
        fields = [
            'id', 'company', 'company_code', 'subscription', 'subscription_contract_id',
            'vehicle', 'vehicle_record', 'vehicle_number', 'vehicle_vin', 'vehicle_record_vin', 'customer',
            'scheduled_at', 'actual_at', 'location', 'status',
            'photos', 'checks', 'note', 'repairs', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetInsurancePolicySerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    vehicle_vin = serializers.CharField(source='vehicle.vin_tid', read_only=True)
    vehicle_record_vin = serializers.CharField(source='vehicle_record.vin', read_only=True)

    class Meta:
        model = FleetInsurancePolicy
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record', 'vehicle_number',
            'vehicle_vin', 'vehicle_record_vin', 'insurer', 'policy_no', 'start_date', 'end_date',
            'previous_rate', 'current_rate', 'status', 'payments',
            'note', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetAccidentCaseSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = FleetAccidentCase
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record', 'vehicle_number',
            'source_key', 'vehicle_vin', 'driver', 'accident_at', 'location', 'description',
            'coverage', 'victim', 'compensation', 'personal_compensation',
            'property_compensation', 'paid', 'manager', 'status',
            'compensation_note', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetInspectionScheduleSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    vehicle_vin = serializers.CharField(source='vehicle.vin_tid', read_only=True)
    vehicle_record_vin = serializers.CharField(source='vehicle_record.vin', read_only=True)

    class Meta:
        model = FleetInspectionSchedule
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record',
            'vehicle_number', 'vehicle_vin', 'vehicle_record_vin',
            'scheduled_date', 'completed_date', 'status', 'memo',
            'source_key', 'raw', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetProfitRuleVersionSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = FleetProfitRuleVersion
        fields = [
            'id', 'company', 'company_code', 'version', 'title',
            'rules', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class FleetProfitImportBatchSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = FleetProfitImportBatch
        fields = [
            'id', 'company', 'company_code', 'source_file', 'file_hash',
            'status', 'summary', 'created_at',
        ]
        read_only_fields = ['created_at']


class FleetProfitRawEntrySerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = FleetProfitRawEntry
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record',
            'batch', 'entry_type', 'source_sheet', 'source_row',
            'source_key', 'vehicle_number', 'period_month', 'amount',
            'raw', 'created_at',
        ]
        read_only_fields = ['created_at']


class FleetProfitAdjustmentSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    evidence_file_name = serializers.SerializerMethodField()
    evidence_file_url = serializers.SerializerMethodField()

    class Meta:
        model = FleetProfitAdjustment
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record',
            'vehicle_number', 'period_month', 'category', 'description',
            'amount', 'evidence_file', 'evidence_file_name', 'evidence_file_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_evidence_file_name(self, obj):
        if not obj.evidence_file:
            return ''
        return obj.evidence_file.name.rsplit('/', 1)[-1]

    def get_evidence_file_url(self, obj):
        if not obj.evidence_file:
            return ''
        request = self.context.get('request')
        url = obj.evidence_file.url
        return request.build_absolute_uri(url) if request else url


class FleetProfitMonthlySnapshotSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)
    rule_version_code = serializers.CharField(source='rule_version.version', read_only=True)

    class Meta:
        model = FleetProfitMonthlySnapshot
        fields = [
            'id', 'company', 'company_code', 'vehicle', 'vehicle_record',
            'rule_version', 'rule_version_code', 'vehicle_number', 'period_month',
            'revenue', 'subscription_revenue', 'customer_charges',
            'depreciation_cost', 'insurance_cost', 'repair_cost', 'accident_cost',
            'other_cost', 'operating_profit', 'net_profit', 'calculation',
            'is_closed', 'closed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class FleetMonthlyCloseSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source='company.code', read_only=True)

    class Meta:
        model = FleetMonthlyClose
        fields = [
            'id', 'company', 'company_code', 'period_month', 'target',
            'status', 'memo', 'closed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
