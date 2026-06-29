import math

from rest_framework import serializers
from .models import TrackingSession, LocationPoint, BleLog, CameraCapture, Cycle


def _sanitize_json_value(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    return value


class SafeFloatRepresentationMixin:
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return _sanitize_json_value(data)


class SessionListSerializer(SafeFloatRepresentationMixin, serializers.ModelSerializer):
    """리스트용 경량 직렬화 (filter: team/date 결과)"""
    crew_name = serializers.CharField(source='crew_member.name', read_only=True)
    crew_code = serializers.CharField(source='crew_member.code', read_only=True)
    vehicle_number = serializers.CharField(source='crew_member.vehicle_number', read_only=True)
    team_id = serializers.IntegerField(source='crew_member.team_id', read_only=True)
    team_name = serializers.CharField(source='crew_member.team.name', read_only=True, default='')
    uploaded_at = serializers.DateTimeField(source='created_at', read_only=True)
    route_color = serializers.SerializerMethodField()
    csv_download_url = serializers.SerializerMethodField()
    capture_count = serializers.SerializerMethodField()
    has_rssi = serializers.SerializerMethodField()

    class Meta:
        model = TrackingSession
        fields = [
            'id', 'crew_member', 'crew_name', 'crew_code', 'vehicle_number',
            'team_id', 'team_name', 'session_date', 'uploaded_at', 'app_version',
            'started_at', 'ended_at', 'total_seconds',
            'iv_seconds', 'sr_seconds', 'dl_seconds',
            'distance_m', 'cycle_count', 'route_color',
            'bbox_min_lat', 'bbox_min_lon', 'bbox_max_lat', 'bbox_max_lon',
            'capture_count', 'has_rssi',
            'csv_download_url',
        ]

    # 오버뷰 모드용 고정 팔레트 (BLE 3-state 색과 충돌 없음)
    PALETTE = [
        '#8B5CF6', '#EC4899', '#06B6D4', '#D946EF',
        '#6366F1', '#DB2777', '#0891B2', '#7C3AED',
        '#059669', '#DC2626', '#2563EB', '#C026D3',
    ]

    def get_route_color(self, obj):
        return self.PALETTE[(obj.crew_member_id or 0) % len(self.PALETTE)]

    def get_csv_download_url(self, obj):
        path = f'/api/v1/tracking/sessions/{obj.pk}/download_csv/'
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def get_capture_count(self, obj):
        if hasattr(obj, "capture_count"):
            return int(obj.capture_count or 0)
        return obj.captures.count()

    def get_has_rssi(self, obj):
        if hasattr(obj, "has_rssi_count"):
            return bool(obj.has_rssi_count)
        return obj.ble_logs.filter(rssi__isnull=False).exists()


class LocationPointSerializer(SafeFloatRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = LocationPoint
        fields = ['recorded_at', 'lat', 'lon', 'accuracy_m', 'speed_kmh', 'state', 'cycle_id']


class BleLogSerializer(SafeFloatRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = BleLog
        fields = ['recorded_at', 'rssi', 'status']


class CameraCaptureSerializer(SafeFloatRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = CameraCapture
        fields = ['started_at', 'captured_at', 'duration_ms', 'device', 'lat', 'lon', 'cycle_id']


class CycleSerializer(SafeFloatRepresentationMixin, serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = [
            'id', 'cycle_no', 'started_at', 'ended_at',
            'sr_seconds', 'dl_seconds', 'distance_m',
            'avg_speed_kmh', 'avg_accuracy_m', 'capture_count',
        ]


class SessionDetailSerializer(SessionListSerializer):
    """상세용 — zoom-to-layer 시 인원 1명에 사용"""
    points = LocationPointSerializer(many=True, read_only=True)
    captures = CameraCaptureSerializer(many=True, read_only=True)
    cycles = CycleSerializer(many=True, read_only=True)
    settlement = serializers.SerializerMethodField()

    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + ['points', 'captures', 'cycles', 'settlement']

    def get_settlement(self, obj):
        """
        세션 날짜를 포함하는 SettlementDetail 을 찾아 요약 반환.
        같은 crew + (period_start <= session_date <= period_end) 기준.
        """
        try:
            from apps.settlement.models import SettlementDetail
        except Exception:
            return None
        qs = SettlementDetail.objects.filter(
            crew_member=obj.crew_member,
            settlement__period_start__lte=obj.session_date,
            settlement__period_end__gte=obj.session_date,
        ).select_related('settlement')
        items = list(qs)
        if not items:
            return None
        total_boxes = sum(int(d.boxes or 0) for d in items)
        total_receive = sum(int(d.receive_amount or 0) for d in items)
        total_pay = sum(int(d.pay_amount or 0) for d in items)
        total_overtime = sum(int(d.overtime_cost or 0) for d in items)
        return {
            'date': obj.session_date.isoformat(),
            'regions': [{
                'region': d.region, 'boxes': int(d.boxes or 0),
                'receive': int(d.receive_amount or 0),
                'pay': int(d.pay_amount or 0),
            } for d in items],
            'total_boxes': total_boxes,
            'total_receive': total_receive,
            'total_pay': total_pay,
            'total_overtime': total_overtime,
            'total_profit': total_receive - total_pay - total_overtime,
            'status': items[0].settlement.status if hasattr(items[0].settlement, 'status') else '',
        }
