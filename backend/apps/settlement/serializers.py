from rest_framework import serializers
from django.db.models import Sum
from apps.accounts.models import Shipper
from apps.dispatch.date_utils import date_iso, to_work_date
from .models import Settlement, SettlementDetail


class SettlementDetailSerializer(serializers.ModelSerializer):
    crew_member_name = serializers.CharField(source='crew_member.name', read_only=True, default='')
    crew_member_code = serializers.CharField(source='crew_member.code', read_only=True, default='')
    upload_filename = serializers.CharField(source='dispatch_upload.original_filename', read_only=True, default='')
    upload_time = serializers.DateTimeField(source='dispatch_upload.upload_date', read_only=True)
    dispatch_date = serializers.DateField(source='dispatch_upload.dispatch_date', read_only=True)

    class Meta:
        model = SettlementDetail
        fields = [
            'id', 'dispatch_upload', 'upload_filename', 'upload_time', 'dispatch_date',
            'shipper_code', 'crew_member', 'crew_member_code', 'crew_member_name', 'is_yongcha',
            'region', 'delivery_type', 'boxes', 'receive_amount', 'pay_amount',
            'overtime_cost', 'other_cost', 'profit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        delivery_date = instance.dispatch_upload.dispatch_date if instance.dispatch_upload_id else None
        work_date = to_work_date(delivery_date)
        data['work_date'] = date_iso(work_date)
        data['delivery_date'] = date_iso(delivery_date)
        data['dispatch_date'] = date_iso(delivery_date)
        return data


class SettlementSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    details = SettlementDetailSerializer(many=True, read_only=True)
    regular_total_receive = serializers.SerializerMethodField()
    regular_total_pay = serializers.SerializerMethodField()
    regular_total_overtime = serializers.SerializerMethodField()
    regular_total_other_cost = serializers.SerializerMethodField()
    regular_total_profit = serializers.SerializerMethodField()
    yongcha_total_receive = serializers.SerializerMethodField()
    yongcha_total_pay = serializers.SerializerMethodField()
    yongcha_total_profit = serializers.SerializerMethodField()
    yongcha_total_boxes = serializers.SerializerMethodField()
    shipper_name = serializers.SerializerMethodField()

    class Meta:
        model = Settlement
        fields = [
            'id', 'period_start', 'period_end', 'team', 'team_name', 'shipper_code', 'shipper_name',
            'status', 'total_receive', 'total_pay', 'total_overtime', 'total_other_cost', 'total_profit',
            'regular_total_receive', 'regular_total_pay', 'regular_total_overtime',
            'regular_total_other_cost', 'regular_total_profit',
            'yongcha_total_receive', 'yongcha_total_pay', 'yongcha_total_profit', 'yongcha_total_boxes',
            'confirmed_by', 'confirmed_by_name', 'confirmed_at', 'note',
            'details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['confirmed_by', 'confirmed_at', 'created_at', 'updated_at']

    def get_fields(self):
        fields = super().get_fields()
        if self.context.get('include_details') is False:
            fields.pop('details', None)
        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        delivery_start = instance.period_start
        delivery_end = instance.period_end
        work_start = to_work_date(delivery_start)
        work_end = to_work_date(delivery_end)
        data['work_period_start'] = date_iso(work_start)
        data['work_period_end'] = date_iso(work_end)
        data['delivery_period_start'] = date_iso(delivery_start)
        data['delivery_period_end'] = date_iso(delivery_end)
        data['period_start'] = date_iso(delivery_start)
        data['period_end'] = date_iso(delivery_end)
        return data

    def get_shipper_name(self, obj):
        if not obj.shipper_code:
            return 'kurly'
        cache = getattr(self, '_shipper_name_cache', None)
        if cache is None:
            cache = {
                row.code: row.name
                for row in Shipper.objects.all()
            }
            setattr(self, '_shipper_name_cache', cache)
        return cache.get(obj.shipper_code, obj.shipper_code)

    def _aggregate_totals(self, obj):
        cached = getattr(obj, '_settlement_serializer_totals', None)
        if cached is not None:
            return cached

        totals = {
            False: {'receive': 0, 'pay': 0, 'overtime': 0, 'other': 0, 'profit': 0, 'boxes': 0},
            True: {'receive': 0, 'pay': 0, 'overtime': 0, 'other': 0, 'profit': 0, 'boxes': 0},
        }
        annotated_attrs = {
            False: {
                'receive': 'regular_total_receive_agg',
                'pay': 'regular_total_pay_agg',
                'overtime': 'regular_total_overtime_agg',
                'other': 'regular_total_other_cost_agg',
                'profit': 'regular_total_profit_agg',
                'boxes': 'regular_total_boxes_agg',
            },
            True: {
                'receive': 'yongcha_total_receive_agg',
                'pay': 'yongcha_total_pay_agg',
                'overtime': 'yongcha_total_overtime_agg',
                'other': 'yongcha_total_other_cost_agg',
                'profit': 'yongcha_total_profit_agg',
                'boxes': 'yongcha_total_boxes_agg',
            },
        }

        has_annotations = any(
            hasattr(obj, attr)
            for attrs in annotated_attrs.values()
            for attr in attrs.values()
        )
        if has_annotations:
            for is_yongcha, attrs in annotated_attrs.items():
                for key, attr in attrs.items():
                    totals[is_yongcha][key] = getattr(obj, attr, None) or 0
        else:
            rows = obj.details.values('is_yongcha').annotate(
                receive=Sum('receive_amount'),
                pay=Sum('pay_amount'),
                overtime=Sum('overtime_cost'),
                other=Sum('other_cost'),
                profit=Sum('profit'),
                boxes=Sum('boxes'),
            )
            for row in rows:
                totals[bool(row['is_yongcha'])] = {
                    'receive': row['receive'] or 0,
                    'pay': row['pay'] or 0,
                    'overtime': row['overtime'] or 0,
                    'other': row['other'] or 0,
                    'profit': row['profit'] or 0,
                    'boxes': row['boxes'] or 0,
                }

        setattr(obj, '_settlement_serializer_totals', totals)
        return totals

    def _aggregate(self, obj, is_yongcha):
        return self._aggregate_totals(obj)[bool(is_yongcha)]

    def _int_value(self, value):
        return int(value or 0)

    def get_regular_total_receive(self, obj):
        return self._int_value(self._aggregate(obj, False)['receive'])

    def get_regular_total_pay(self, obj):
        return self._int_value(self._aggregate(obj, False)['pay'])

    def get_regular_total_overtime(self, obj):
        return self._int_value(self._aggregate(obj, False)['overtime'])

    def get_regular_total_other_cost(self, obj):
        return self._int_value(self._aggregate(obj, False)['other'])

    def get_regular_total_profit(self, obj):
        return self._int_value(self._aggregate(obj, False)['profit'])

    def get_yongcha_total_receive(self, obj):
        return self._int_value(self._aggregate(obj, True)['receive'])

    def get_yongcha_total_pay(self, obj):
        return self._int_value(self._aggregate(obj, True)['pay'])

    def get_yongcha_total_profit(self, obj):
        return self._int_value(self._aggregate(obj, True)['profit'])

    def get_yongcha_total_boxes(self, obj):
        return self._int_value(self._aggregate(obj, True)['boxes'])


class SettlementCreateSerializer(serializers.ModelSerializer):
    """정산 생성 serializer"""

    class Meta:
        model = Settlement
        fields = ['period_start', 'period_end', 'team', 'shipper_code', 'note']



class SettlementConfirmSerializer(serializers.Serializer):
    """정산 확정 serializer"""
    settlement_id = serializers.IntegerField()
