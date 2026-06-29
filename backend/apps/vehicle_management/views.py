"""차량 관리 도메인 API.

- /api/v1/vehicle/companies/                회사 (유한/천하/개인)
- /api/v1/vehicle/vehicles/                  전체 차량현황 CRUD (Excel 업로드 별도)
- /api/v1/vehicle/pit-records/               피트 차량현황 CRUD (인라인 편집)
- /api/v1/vehicle/calendar/                  통합 일정 (날짜 범위 / 회사 필터)
- /api/v1/vehicle/subscriptions/             구독 요청 list/create/assign/complete
- /api/v1/vehicle/returns/                   반납 요청 list/create/confirm/adjust
- /api/v1/vehicle/as-requests/               A/S 요청 list/create/complete
"""
import io
import math
import re
from datetime import datetime
from uuid import uuid4
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
import pandas as pd
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Company, Vehicle, PitRecord, CalendarEvent,
    SubscriptionRequest, SubscriptionRequestVehicle,
    ReturnRequest, ReturnRequestPhoto, ASRequest,
    FleetVehicleRecord, FleetVehicleDocument, FleetSubscriptionContract, FleetReturnRecord,
    FleetInsurancePolicy, FleetAccidentCase,
)
from .serializers import (
    CompanySerializer, VehicleSerializer, PitRecordSerializer, CalendarEventSerializer,
    SubscriptionRequestSerializer, AssignVehiclesSerializer, RejectSubscriptionSerializer,
    ReturnRequestSerializer, ConfirmReturnSerializer, AdjustReturnSerializer,
    ASRequestSerializer, CompleteASSerializer,
    FleetVehicleRecordSerializer, FleetVehicleDocumentSerializer,
    FleetSubscriptionContractSerializer, FleetReturnRecordSerializer,
    FleetInsurancePolicySerializer, FleetAccidentCaseSerializer,
)
from .holiday_utils import iter_public_holidays, holiday_dates_between
from .services.evdash_service import get_fleet_evdash, get_vehicle_evdash


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.filter(is_active=True)
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]


class CompanyScopedMixin:
    """?company=YUHAN/CHEONHA/PERSONAL 쿼리스트링 필터."""
    def get_queryset(self):
        qs = super().get_queryset()
        code = self.request.query_params.get('company')
        if code:
            qs = qs.filter(company__code=code)
        return qs


CATEGORY_FLEETS = {
    'DIRECT':       ['제조부문', '물류부문', 'DSV'],
    'SUBSCRIPTION': ['천하', '유한', '개인', '쿠팡'],
}

FLEET_OPERATION_STATUSES = {
    '유휴': ('IDLE', 'OTHER'),
    'A/S': ('REPAIRING', 'OTHER'),
    '판매': ('OPERATING', 'SALE'),
    '구독': ('OPERATING', 'SUBSCRIPTION'),
    '직영': ('OPERATING', 'DIRECT'),
}

FLEET_OPERATION_STATUS_ALIASES = {
    'AS': 'A/S',
    'A/S중': 'A/S',
    '수리': 'A/S',
    '수리중': 'A/S',
    '검수': 'A/S',
    '검수중': 'A/S',
    '대기': '유휴',
    '출고대기': '유휴',
    '미출고': '유휴',
    '구독중': '구독',
    '구독계약': '구독',
    '판매완료': '판매',
    '직영운행': '직영',
}


def _normalize_fleet_operation_status(value):
    label = str(value or '').strip()
    label = FLEET_OPERATION_STATUS_ALIASES.get(label, label)
    return label if label in FLEET_OPERATION_STATUSES else None


def _apply_fleet_operation_status(*, record=None, vehicle=None, status_value=None):
    label = _normalize_fleet_operation_status(status_value)
    if not label:
        return None
    placement_status, operation_type = FLEET_OPERATION_STATUSES[label]

    if vehicle:
        vehicle.placement_status = placement_status
        vehicle.operation_type = operation_type
        vehicle.save(update_fields=['placement_status', 'operation_type', 'updated_at'])

    if record:
        record.status = label
        record.save(update_fields=['status', 'updated_at'])

    return label


def _vehicle_number_short(value):
    digits = ''.join(c for c in str(value or '') if c.isdigit())
    return digits[-4:] if len(digits) >= 4 else digits


def _parse_request_date(value):
    if value in (None, ''):
        return None
    if hasattr(value, 'isoformat') and not isinstance(value, str):
        return value
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except ValueError:
        raise serializers.ValidationError({'shipped_at': 'Use YYYY-MM-DD format.'})


def _company_from_request_payload(data):
    company_id = data.get('company')
    company_code = data.get('company_code') or data.get('companyCode')
    if company_id:
        return Company.objects.filter(id=company_id).first()
    if company_code:
        return Company.objects.filter(code=company_code).first()
    return None


def _current_fleet_record_for_vehicle(vehicle, old_vehicle_number=None):
    numbers = [vehicle.vehicle_number]
    if old_vehicle_number and old_vehicle_number not in numbers:
        numbers.append(old_vehicle_number)
    qs = FleetVehicleRecord.objects.filter(company=vehicle.company).filter(
        Q(vehicle=vehicle) | Q(vehicle_number__in=numbers)
    )
    return qs.filter(end_date__isnull=True).order_by('-start_date', '-id').first() or qs.order_by('-start_date', '-id').first()


def _sync_vehicle_number_references(vehicle, old_vehicle_number, new_vehicle_number):
    if not old_vehicle_number or old_vehicle_number == new_vehicle_number:
        return
    related_models = [
        FleetVehicleRecord,
        FleetVehicleDocument,
        FleetSubscriptionContract,
        FleetReturnRecord,
        FleetInsurancePolicy,
        FleetAccidentCase,
    ]
    for model in related_models:
        model.objects.filter(
            company=vehicle.company,
        ).filter(
            Q(vehicle=vehicle) | Q(vehicle_number=old_vehicle_number)
        ).update(vehicle_number=new_vehicle_number)


def _vehicle_number_conflict_qs(company, vehicle_number, *, active=None, exclude_vehicle=None):
    qs = Vehicle.objects.filter(company=company, vehicle_number=vehicle_number)
    if active is not None:
        qs = qs.filter(is_active=active)
    if exclude_vehicle:
        qs = qs.exclude(pk=exclude_vehicle.pk)
    return qs


def _archive_vehicle_for_number_reuse(vehicle):
    """Archive an inactive master row before reusing its vehicle number.

    Vehicle.vehicle_number is unique per company, so a previously deleted/inactive
    master row can block a legitimate replacement. We preserve its old history by
    moving that stale number to a stable archive suffix instead of hard-deleting it.
    """
    company = vehicle.company
    old_number = vehicle.vehicle_number
    archived_number = f"{old_number[:22]}#old{vehicle.pk}"
    if archived_number == old_number:
        archived_number = f"old{vehicle.pk}-{old_number}"[:32]

    related_models = [
        FleetVehicleRecord,
        FleetVehicleDocument,
        FleetSubscriptionContract,
        FleetReturnRecord,
        FleetInsurancePolicy,
        FleetAccidentCase,
    ]
    for model in related_models:
        model.objects.filter(company=company).filter(
            Q(vehicle=vehicle) | Q(vehicle_number=old_number)
        ).update(vehicle_number=archived_number)

    vehicle.vehicle_number = archived_number
    vehicle.vehicle_number_short = _vehicle_number_short(archived_number)
    vehicle.is_active = False
    vehicle.save(update_fields=['vehicle_number', 'vehicle_number_short', 'is_active', 'updated_at'])
    return archived_number


def _archive_inactive_vehicle_number_conflicts(company, vehicle_number, *, exclude_vehicle=None):
    for conflict in _vehicle_number_conflict_qs(
        company,
        vehicle_number,
        active=False,
        exclude_vehicle=exclude_vehicle,
    ).select_for_update():
        _archive_vehicle_for_number_reuse(conflict)


def _ensure_vehicle_fleet_record(vehicle, request, status_value=None, old_vehicle_number=None):
    label = _normalize_fleet_operation_status(status_value) or status_value or '운행중'
    record = _current_fleet_record_for_vehicle(vehicle, old_vehicle_number=old_vehicle_number)
    if not record:
        record = FleetVehicleRecord.objects.create(
            company=vehicle.company,
            vehicle=vehicle,
            vehicle_number=vehicle.vehicle_number,
            vin=vehicle.vin_tid or '',
            model=vehicle.model or '',
            start_date=vehicle.shipped_at or timezone.localdate(),
            status=label,
            created_by=getattr(request, 'user', None) if getattr(request, 'user', None) and request.user.is_authenticated else None,
        )
        return record

    record.vehicle = vehicle
    record.vehicle_number = vehicle.vehicle_number
    record.vin = vehicle.vin_tid or record.vin or ''
    record.model = vehicle.model or record.model or ''
    if vehicle.shipped_at:
        record.start_date = vehicle.shipped_at
    if label:
        record.status = label
    record.save(update_fields=[
        'vehicle', 'vehicle_number', 'vin', 'model', 'start_date', 'status', 'updated_at',
    ])
    return record


class VehicleViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    """
    Filter params:
      - ?company=CHEONHA
      - ?category=DIRECT|REPAIRING|SUBSCRIPTION|SALE|IDLE   (5 카테고리)
      - ?fleet=제조부문    (하위탭, category=DIRECT/SUBSCRIPTION 일 때)
      - ?placement=OPERATING|REPAIRING|NOT_SHIPPED  (legacy)
      - ?op=SALE|DIRECT|SUBSCRIPTION|OTHER          (legacy)
    """
    queryset = Vehicle.objects.select_related('company').all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['vehicle_number', 'vin_tid', 'driver', 'hgi', 'fleet']
    ordering_fields = ['created_at', 'vehicle_number', 'shipped_at']

    def _apply_category(self, qs, category):
        """차량 1대당 정확히 1 카테고리 (합 = total).
        placement=NOT_SHIPPED → 미출고 탭만 / IDLE → 유휴 탭만 / REPAIRING → 수리 탭만.
        placement=OPERATING 차량만 fleet 기준으로 직영/구독/판매 분류."""
        if category == 'REPAIRING':
            return qs.filter(placement_status='REPAIRING')
        if category == 'IDLE':
            return qs.filter(placement_status='IDLE')
        if category == 'NOT_SHIPPED':
            return qs.filter(placement_status='NOT_SHIPPED')
        if category == 'SALE':
            return qs.filter(fleet='판매', placement_status='OPERATING')
        if category in ('DIRECT', 'SUBSCRIPTION'):
            return qs.filter(fleet__in=CATEGORY_FLEETS[category], placement_status='OPERATING')
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get('category')
        fleet    = self.request.query_params.get('fleet')
        placement = self.request.query_params.get('placement')
        op       = self.request.query_params.get('op')
        if category:
            qs = self._apply_category(qs, category)
        if fleet:
            qs = qs.filter(fleet=fleet)
        if placement:
            qs = qs.filter(placement_status=placement)
        if op:
            qs = qs.filter(operation_type=op)
        return qs

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='registration-certificate',
        parser_classes=[MultiPartParser, FormParser],
    )
    def registration_certificate(self, request, pk=None):
        """자동차등록증 업로드/삭제.

        POST multipart field: file
        DELETE: 기존 파일 제거
        """
        vehicle = self.get_object()

        if request.method == 'DELETE':
            if vehicle.registration_certificate:
                vehicle.registration_certificate.delete(save=False)
            vehicle.registration_certificate = ''
            vehicle.registration_certificate_uploaded_at = None
            vehicle.save(update_fields=[
                'registration_certificate',
                'registration_certificate_uploaded_at',
                'updated_at',
            ])
            return Response(self.get_serializer(vehicle).data)

        uploaded = request.FILES.get('file') or request.FILES.get('registration_certificate')
        if not uploaded:
            return Response({'detail': '업로드할 자동차등록증 파일을 선택해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        if uploaded.size > 20 * 1024 * 1024:
            return Response({'detail': '자동차등록증 파일은 20MB 이하만 업로드할 수 있습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext not in {'pdf', 'jpg', 'jpeg', 'png', 'webp'}:
            return Response({'detail': 'PDF, JPG, PNG, WEBP 파일만 업로드할 수 있습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if vehicle.registration_certificate:
            vehicle.registration_certificate.delete(save=False)
        vehicle.registration_certificate = uploaded
        vehicle.registration_certificate_uploaded_at = timezone.now()
        vehicle.save(update_fields=[
            'registration_certificate',
            'registration_certificate_uploaded_at',
            'updated_at',
        ])
        return Response(self.get_serializer(vehicle).data)

    @action(detail=True, methods=['get'], url_path='evdash')
    def evdash(self, request, pk=None):
        """EV Dashboard readonly DB에서 차량 최신 위치/상태를 조회한다."""
        vehicle = self.get_object()
        return Response(get_vehicle_evdash(vehicle))

    @action(detail=False, methods=['post'], url_path='fleet-create')
    @transaction.atomic
    def fleet_create(self, request):
        """Create a vehicle from the fleet-management screen and open a current record."""
        company = _company_from_request_payload(request.data)
        if not company:
            return Response({'detail': 'company is required.'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_number = str(request.data.get('vehicle_number') or '').strip()
        if not vehicle_number:
            return Response({'detail': 'vehicle_number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if _vehicle_number_conflict_qs(company, vehicle_number, active=True).exists():
            return Response({
                'detail': '이미 사용 중인 차량번호입니다. 현재 운행/관리 중인 차량번호는 중복 등록할 수 없습니다.',
            }, status=status.HTTP_400_BAD_REQUEST)
        _archive_inactive_vehicle_number_conflicts(company, vehicle_number)

        status_label = request.data.get('status') or '유휴'
        normalized_status = _normalize_fleet_operation_status(status_label)
        if status_label and not normalized_status:
            return Response(
                {'detail': 'status must be one of idle, A/S, sale, subscription, direct.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle = Vehicle.objects.create(
            company=company,
            vehicle_number=vehicle_number,
            vehicle_number_short=_vehicle_number_short(vehicle_number),
            vin_tid=str(request.data.get('vin_tid') or '').strip(),
            model=str(request.data.get('model') or '').strip(),
            shipped_at=_parse_request_date(request.data.get('shipped_at')),
            fleet=str(request.data.get('fleet') or '').strip(),
            driver=str(request.data.get('driver') or '').strip(),
            hgi=str(request.data.get('hgi') or '').strip(),
            notes=str(request.data.get('notes') or '').strip(),
            is_active=True,
        )
        record = _ensure_vehicle_fleet_record(
            vehicle,
            request,
            status_value=normalized_status,
        )
        _apply_fleet_operation_status(record=record, vehicle=vehicle, status_value=normalized_status)

        return Response({
            'record': _fleet_record_payload(record, request),
            'vehicle': self.get_serializer(vehicle).data,
            'open_subscription': normalized_status == '구독',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'patch'], url_path='fleet-info')
    @transaction.atomic
    def fleet_info(self, request, pk=None):
        """Update vehicle identity/basic info and keep fleet-management references aligned."""
        vehicle = self.get_object()
        old_vehicle_number = vehicle.vehicle_number
        new_vehicle_number = str(request.data.get('vehicle_number', old_vehicle_number) or '').strip()
        if not new_vehicle_number:
            return Response({'detail': 'vehicle_number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if _vehicle_number_conflict_qs(
            vehicle.company,
            new_vehicle_number,
            active=True,
            exclude_vehicle=vehicle,
        ).exists():
            return Response({
                'detail': '이미 사용 중인 차량번호입니다. 현재 운행/관리 중인 차량번호는 중복 등록할 수 없습니다.',
            }, status=status.HTTP_400_BAD_REQUEST)
        _archive_inactive_vehicle_number_conflicts(
            vehicle.company,
            new_vehicle_number,
            exclude_vehicle=vehicle,
        )

        status_label = request.data.get('status')
        normalized_status = None
        if status_label not in (None, ''):
            normalized_status = _normalize_fleet_operation_status(status_label)
            if not normalized_status:
                return Response(
                    {'detail': 'status must be one of idle, A/S, sale, subscription, direct.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        text_fields = ['vin_tid', 'model', 'fleet', 'driver', 'hgi', 'notes']
        for field in text_fields:
            if field in request.data:
                setattr(vehicle, field, str(request.data.get(field) or '').strip())

        vehicle.vehicle_number = new_vehicle_number
        vehicle.vehicle_number_short = _vehicle_number_short(new_vehicle_number)
        if 'shipped_at' in request.data:
            vehicle.shipped_at = _parse_request_date(request.data.get('shipped_at'))

        vehicle.save(update_fields=[
            'vehicle_number', 'vehicle_number_short', 'vin_tid', 'model',
            'shipped_at', 'fleet', 'driver', 'hgi', 'notes', 'updated_at',
        ])

        _sync_vehicle_number_references(vehicle, old_vehicle_number, new_vehicle_number)
        record = _ensure_vehicle_fleet_record(
            vehicle,
            request,
            status_value=normalized_status,
            old_vehicle_number=old_vehicle_number,
        )
        if normalized_status:
            _apply_fleet_operation_status(record=record, vehicle=vehicle, status_value=normalized_status)

        return Response({
            'record': _fleet_record_payload(record, request),
            'vehicle': self.get_serializer(vehicle).data,
            'open_subscription': normalized_status == '구독',
        })

    @action(detail=True, methods=['post', 'patch'], url_path='status')
    @transaction.atomic
    def status(self, request, pk=None):
        """차량 운영상태를 유휴/A-S/판매/구독/직영 중 하나로 변경한다."""
        vehicle = self.get_object()
        label = _normalize_fleet_operation_status(request.data.get('status'))
        if not label:
            return Response(
                {'detail': 'status must be one of 유휴, A/S, 판매, 구독, 직영.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = FleetVehicleRecord.objects.filter(
            company=vehicle.company,
            vehicle_number=vehicle.vehicle_number,
            end_date__isnull=True,
        ).order_by('-start_date', '-id').first()

        if not record:
            record = FleetVehicleRecord.objects.create(
                company=vehicle.company,
                vehicle=vehicle,
                vehicle_number=vehicle.vehicle_number,
                vin=vehicle.vin_tid or '',
                model=vehicle.model or '',
                start_date=vehicle.shipped_at or timezone.localdate(),
                status=label,
                created_by=request.user,
            )

        label = _apply_fleet_operation_status(record=record, vehicle=vehicle, status_value=label)
        return Response({
            'status': label,
            'open_subscription': label == '구독',
            'record': _fleet_record_payload(record, request),
            'vehicle': self.get_serializer(vehicle).data,
        })

    @action(detail=True, methods=['delete'], url_path='fleet-delete')
    @transaction.atomic
    def fleet_delete(self, request, pk=None):
        """Archive a vehicle from the fleet-management screen without deleting history."""
        vehicle = self.get_object()
        company = vehicle.company
        vehicle_number = vehicle.vehicle_number

        record_qs = FleetVehicleRecord.objects.filter(company=company).filter(
            Q(vehicle=vehicle) | Q(vehicle_number=vehicle_number)
        )
        record_ids = list(record_qs.values_list('id', flat=True))

        def related_queryset(model):
            lookup = Q(vehicle=vehicle) | Q(vehicle_number=vehicle_number)
            if record_ids:
                lookup |= Q(vehicle_record_id__in=record_ids)
            return model.objects.filter(company=company).filter(lookup)

        related_counts = {}
        related_models = [
            ('documents', FleetVehicleDocument),
            ('subscriptions', FleetSubscriptionContract),
            ('returns', FleetReturnRecord),
            ('insurances', FleetInsurancePolicy),
            ('accidents', FleetAccidentCase),
        ]
        for key, model in related_models:
            related_counts[key] = related_queryset(model).count()

        today = timezone.localdate()
        closed_records = record_qs.filter(end_date__isnull=True).update(
            end_date=today,
            status='보관',
        )
        related_counts['fleet_records'] = record_qs.count()

        vehicle.is_active = False
        vehicle.save(update_fields=['is_active', 'updated_at'])

        return Response({
            'vehicle_number': vehicle_number,
            'archived': True,
            'hard_deleted': False,
            'closed_fleet_records': closed_records,
            'related': related_counts,
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """KPI: 배치현황별 + 5 카테고리별 + 하위탭(fleet) 카운트."""
        from django.db.models import Count
        qs = super().get_queryset()  # company 필터까지만 적용 (category 없이)
        place = qs.values('placement_status').annotate(c=Count('id'))
        # 6 카테고리 카운트 (유휴 ≠ 미출고)
        cats = {}
        for c in ('DIRECT', 'REPAIRING', 'SUBSCRIPTION', 'SALE', 'IDLE', 'NOT_SHIPPED'):
            cats[c] = self._apply_category(qs, c).count()
        # 하위탭 (fleet) 카운트
        fleet_counts = dict(qs.values_list('fleet').annotate(c=Count('id')).values_list('fleet', 'c'))
        return Response({
            'total': qs.count(),
            'by_placement': {r['placement_status']: r['c'] for r in place},
            'by_category':  cats,
            'by_fleet':     fleet_counts,
        })


class PitRecordViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = PitRecord.objects.select_related('company', 'vehicle').all()
    serializer_class = PitRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number_short', 'note']

    def get_queryset(self):
        qs = super().get_queryset()
        reason = self.request.query_params.get('reason')
        in_pit = self.request.query_params.get('in_pit')
        if reason:
            qs = qs.filter(reason=reason)
        if in_pit == 'true':
            qs = qs.filter(out_date__isnull=True)
        elif in_pit == 'false':
            qs = qs.filter(out_date__isnull=False)
        return qs

    def perform_create(self, serializer):
        record = serializer.save(created_by=self.request.user)
        self._auto_link_vehicle(record)
        self._sync_calendar(record)

    def perform_update(self, serializer):
        record = serializer.save()
        # 출고일 입력 시 차량 placement_status 자동 복귀
        if record.out_date and record.vehicle:
            v = record.vehicle
            if v.placement_status in {'REPAIRING', 'IDLE'}:
                v.placement_status = 'OPERATING'
                v.save(update_fields=['placement_status', 'updated_at'])
        elif record.vehicle and record.vehicle.placement_status == 'OPERATING':
            record.vehicle.placement_status = 'REPAIRING'
            record.vehicle.save(update_fields=['placement_status', 'updated_at'])
        self._sync_calendar(record)

    def _auto_link_vehicle(self, record: PitRecord):
        """차량번호 끝 4자리로 Vehicle 자동 매칭 + placement_status='REPAIRING'."""
        if record.vehicle_id:
            if not record.out_date and record.vehicle and record.vehicle.placement_status != 'REPAIRING':
                record.vehicle.placement_status = 'REPAIRING'
                record.vehicle.save(update_fields=['placement_status', 'updated_at'])
            return
        v = Vehicle.objects.filter(
            company=record.company,
            vehicle_number_short=record.vehicle_number_short,
            is_active=True,
        ).first()
        if v:
            record.vehicle = v
            record.save(update_fields=['vehicle'])
            if not record.out_date and v.placement_status != 'REPAIRING':
                v.placement_status = 'REPAIRING'
                v.save(update_fields=['placement_status', 'updated_at'])

    def _sync_calendar(self, record: PitRecord):
        """비고에 'M/D 출고예정' 텍스트 → 캘린더 PIT_OUT 이벤트 자동 생성."""
        import re
        record.calendar_events.all().delete()
        if not record.note:
            return
        # 4/29, 4-29, 04/29 등 매칭
        for m in re.finditer(r'(\d{1,2})[/\-.](\d{1,2})\s*(?:천하대차)?\s*출고\s*예정', record.note):
            month, day = int(m.group(1)), int(m.group(2))
            year = record.in_date.year if record.in_date else timezone.now().year
            try:
                d = datetime(year, month, day).date()
            except ValueError:
                continue
            CalendarEvent.objects.create(
                company=record.company, kind='PIT_OUT',
                event_date=d,
                title=f'🚚 {record.vehicle_number_short} 출고 예정',
                body=record.note[:200],
                related_pit_record=record,
                related_vehicle=record.vehicle,
            )


class CalendarEventViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    """통합 일정. 관리자 등록(BLOCK 등) + 자동 생성 이벤트 모두 조회."""
    queryset = CalendarEvent.objects.select_related('company').all()
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        kind = self.request.query_params.get('kind')
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        if kind:
            qs = qs.filter(kind=kind)
        if date_from:
            qs = qs.filter(event_date__gte=date_from)
        if date_to:
            qs = qs.filter(event_date__lte=date_to)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = list(serializer.data)
        company_code = request.query_params.get('company')
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        manual_blocked_dates = {item['event_date'] for item in data if item.get('kind') == 'BLOCK'}
        if date_from and date_to:
            company = Company.objects.filter(code=company_code).first() if company_code else None
            for holiday_date, holiday_name in iter_public_holidays(
                datetime.fromisoformat(date_from).date(),
                datetime.fromisoformat(date_to).date(),
            ):
                iso_date = holiday_date.isoformat()
                if iso_date in manual_blocked_dates:
                    continue
                data.append({
                    'id': f'holiday-{iso_date}',
                    'company': company.id if company else None,
                    'company_code': company.code if company else None,
                    'kind': 'BLOCK',
                    'kind_display': '반납 불가',
                    'event_date': iso_date,
                    'event_time': None,
                    'title': f'공휴일 · {holiday_name}',
                    'body': holiday_name,
                    'related_vehicle': None,
                    'related_pit_record': None,
                    'related_subscription': None,
                    'related_return': None,
                    'related_as': None,
                    'created_at': None,
                })
        data.sort(key=lambda item: (item.get('event_date') or '', item.get('event_time') or '', str(item.get('id'))))
        return Response(data)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SubscriptionRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = SubscriptionRequest.objects.select_related('company').prefetch_related('matched_vehicles__vehicle').all()
    serializer_class = SubscriptionRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs

    def perform_create(self, serializer):
        req = serializer.save()
        CalendarEvent.objects.create(
            company=req.company, kind='REQ_HOPE',
            event_date=req.requested_date,
            title=f'{req.team_code}조 요청 {req.quantity}대',
            body=f'전화: {req.phone}',
            related_subscription=req,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        req = self.get_object()
        if req.status != 'REQUESTED':
            return Response({'detail': '요청 등록 상태에서만 승인할 수 있습니다.'}, status=400)
        req.status = 'APPROVED'
        req.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        req = self.get_object()
        if req.status not in {'REQUESTED', 'APPROVED'}:
            return Response({'detail': '요청 등록 또는 승인 상태에서만 거절할 수 있습니다.'}, status=400)
        payload = RejectSubscriptionSerializer(data=request.data or {})
        payload.is_valid(raise_exception=True)
        req.status = 'REJECTED'
        req.reject_reason = payload.validated_data.get('reject_reason', '')
        req.matched_vehicles.all().delete()
        req.save(update_fields=['status', 'reject_reason', 'updated_at'])
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """요청 대수만큼 차량 선택 (명세 7.2)."""
        req = self.get_object()
        if req.status not in {'APPROVED', 'VEHICLES_SELECTED'}:
            return Response({'detail': '승인된 요청만 차량 배정을 진행할 수 있습니다.'}, status=400)
        s = AssignVehiclesSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ids = s.validated_data['vehicle_ids']
        if len(ids) != req.quantity:
            return Response(
                {'detail': f'요청 대수 {req.quantity}대와 선택 차량 {len(ids)}대가 일치하지 않습니다.'},
                status=400,
            )
        with transaction.atomic():
            req.matched_vehicles.all().delete()
            for vid in ids:
                SubscriptionRequestVehicle.objects.create(request=req, vehicle_id=vid)
            req.status = 'VEHICLES_SELECTED'
            req.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        req = self.get_object()
        if req.status != 'VEHICLES_SELECTED':
            return Response({'detail': '차량 선택 완료 상태에서만 완료 처리 가능합니다.'}, status=400)
        req.status = 'COMPLETED'
        req.completed_at = timezone.now()
        req.save(update_fields=['status', 'completed_at', 'updated_at'])
        return Response(self.get_serializer(req).data)


class ReturnRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = ReturnRequest.objects.select_related('company').prefetch_related('photos').all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs

    def perform_create(self, serializer):
        # 반납 불가일 검증
        hope_date = serializer.validated_data['hope_date']
        company = serializer.validated_data['company']
        if CalendarEvent.objects.filter(company=company, event_date=hope_date,
                                         kind='BLOCK').exists():
            raise serializers.ValidationError({
                'hope_date': '관리자가 등록한 반납 불가일입니다.',
            })
        if hope_date.isoformat() in holiday_dates_between(hope_date, hope_date):
            raise serializers.ValidationError({
                'hope_date': '공휴일은 반납 불가일입니다.',
            })
        req = serializer.save()
        CalendarEvent.objects.create(
            company=req.company, kind='RET_HOPE',
            event_date=req.hope_date, event_time=req.hope_time,
            title=f'{req.team_code}조 {req.vehicle_number} 반납 희망',
            body=req.reason[:200],
            related_return=req,
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """반납 가능 → 날짜/시간 확정."""
        req = self.get_object()
        s = ConfirmReturnSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req.confirmed_date = s.validated_data['confirmed_date']
        req.confirmed_time = s.validated_data['confirmed_time']
        req.status = 'CONFIRMED'
        req.save(update_fields=['confirmed_date', 'confirmed_time', 'status', 'updated_at'])
        CalendarEvent.objects.filter(related_return=req, kind='RET_HOPE').delete()
        CalendarEvent.objects.create(
            company=req.company, kind='RET_CONFIRM',
            event_date=req.confirmed_date, event_time=req.confirmed_time,
            title=f'✓ {req.vehicle_number} 반납 확정',
            body=req.reason[:200],
            related_return=req,
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """반납 불가 → 불가사유/가능 날짜 입력."""
        req = self.get_object()
        s = AdjustReturnSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req.block_reason = s.validated_data['block_reason']
        req.available_dates = s.validated_data['available_dates']
        req.status = 'NEEDS_ADJUST'
        req.save(update_fields=['block_reason', 'available_dates', 'status', 'updated_at'])
        return Response(self.get_serializer(req).data)


def _vm_date(value):
    return value.isoformat() if value else ''


def _vm_datetime(value):
    if not value:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _vm_file_payload(request, file_field, uploaded_at=None):
    if not file_field:
        return None
    url = file_field.url
    return {
        'name': file_field.name.rsplit('/', 1)[-1],
        'url': request.build_absolute_uri(url) if request else url,
        'uploaded': _vm_date(uploaded_at.date() if hasattr(uploaded_at, 'date') else uploaded_at),
    }


def _vm_document_payload(request, document):
    payload = _vm_file_payload(request, document.file, document.uploaded_at)
    return {
        'id': f'DOC-{document.id}',
        'apiId': document.id,
        'companyId': document.company_id,
        'companyCode': document.company.code if document.company_id and getattr(document, 'company', None) else '',
        'type': document.document_type,
        'vehicleId': f'VEH-{document.vehicle_id}' if document.vehicle_id else '',
        'recordId': f'FVR-{document.vehicle_record_id}' if document.vehicle_record_id else '',
        'plate': document.vehicle_number,
        'name': payload['name'] if payload else '',
        'url': payload['url'] if payload else '',
        'uploaded': payload['uploaded'] if payload else '',
        'note': document.note,
    }


def _vehicle_status_label(vehicle):
    if vehicle.placement_status == 'OPERATING':
        return '운행중'
    if vehicle.placement_status == 'REPAIRING':
        return '검수중'
    if vehicle.placement_status == 'IDLE':
        return '출고대기'
    if vehicle.placement_status == 'NOT_SHIPPED':
        return '출고대기'
    return vehicle.placement_status


def _find_vehicle(company, vehicle_number):
    if not company or not vehicle_number:
        return None
    return Vehicle.objects.filter(company=company, vehicle_number=vehicle_number, is_active=True).first()


def _fleet_record_payload(record, request=None):
    vehicle = record.vehicle
    hgi = vehicle.hgi if vehicle else ''
    return {
        'id': f'FVR-{record.id}',
        'apiId': record.id,
        'companyId': record.company_id,
        'companyCode': record.company.code if record.company_id and getattr(record, 'company', None) else '',
        'vehicleApiId': record.vehicle_id,
        'vin': record.vin or '',
        'model': record.model or '',
        'hgi': hgi or '',
        'unitNumber': hgi or '',
        'start': _vm_date(record.start_date),
        'end': _vm_date(record.end_date),
        'status': record.status,
        'cert': {
            'name': record.certificate_name,
            'uploaded': _vm_date(record.certificate_uploaded_at),
            'url': '',
        } if record.certificate_name else None,
    }


def _vehicle_fallback_record(vehicle, request=None):
    cert_payload = _vm_file_payload(request, vehicle.registration_certificate, vehicle.registration_certificate_uploaded_at)
    return {
        'id': f'VEH-{vehicle.id}',
        'apiId': vehicle.id,
        'companyId': vehicle.company_id,
        'companyCode': vehicle.company.code if vehicle.company_id and getattr(vehicle, 'company', None) else '',
        'vehicleApiId': vehicle.id,
        'vin': vehicle.vin_tid or '',
        'model': vehicle.model or '',
        'hgi': vehicle.hgi or '',
        'unitNumber': vehicle.hgi or '',
        'start': _vm_date(vehicle.shipped_at) or _vm_date(vehicle.created_at.date()),
        'end': None,
        'status': _vehicle_status_label(vehicle),
        'placementStatus': vehicle.placement_status,
        'operationType': vehicle.operation_type,
        'cert': cert_payload,
    }


def _orphan_history_record(vehicle_number):
    return {
        'id': f'ORPHAN-{vehicle_number}',
        'apiId': None,
        'vehicleApiId': None,
        'vin': '',
        'model': '',
        'hgi': '',
        'unitNumber': '',
        'start': '',
        'end': None,
        'status': '이력만 있음',
        'placementStatus': '',
        'operationType': '',
        'cert': None,
    }


def _record_for_date(records, target_date):
    if not records:
        return None
    if not target_date:
        return next((r for r in records if r.get('status') == '운행중'), None) or records[-1]
    for record in records:
        start = record.get('start')
        end = record.get('end')
        if start and start <= target_date and (not end or target_date <= end):
            return record
    return next((r for r in records if r.get('status') == '운행중'), None) or records[-1]


def _record_for_object(obj, date_value=None):
    record = getattr(obj, 'vehicle_record', None)
    if record:
        return _fleet_record_payload(record)
    return None


class FleetSiteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        company_code = request.query_params.get('company')
        company_qs = Company.objects.filter(is_active=True).order_by('sort_order', 'id')
        if company_code:
            company_qs = company_qs.filter(code=company_code)
        companies = list(company_qs)
        if not companies:
            return Response({'detail': 'Unknown vehicle company.'}, status=404)

        company_ids = [company.id for company in companies]
        company_by_id = {company.id: company for company in companies}
        default_company = (
            next((company for company in companies if company.code == 'CHEONHA'), None)
            or companies[0]
        )

        vehicles = list(
            Vehicle.objects.filter(company_id__in=company_ids, is_active=True)
            .select_related('company')
            .order_by('vehicle_number', 'id')
        )
        fleet_records = list(
            FleetVehicleRecord.objects.filter(company_id__in=company_ids)
            .select_related('vehicle', 'company')
            .order_by('vehicle_number', 'start_date', 'id')
        )
        groups = {}

        def ensure_group(vehicle_number, vehicle=None, company_obj=None):
            if not vehicle_number:
                vehicle_number = '-'
            if vehicle_number not in groups:
                company_ref = company_obj or getattr(vehicle, 'company', None) or default_company
                groups[vehicle_number] = {
                    'plate': vehicle_number,
                    'owner': company_ref.name,
                    'companyId': company_ref.id,
                    'companyCode': company_ref.code,
                    'companyName': company_ref.name,
                    'records': [],
                    'documents': [],
                    'subscriptions': [],
                    'returns': [],
                    'accidents': [],
                    'insurances': [],
                }
            return groups[vehicle_number]

        for record in fleet_records:
            group = ensure_group(record.vehicle_number, record.vehicle, record.company)
            group['records'].append(_fleet_record_payload(record, request))

        for vehicle in vehicles:
            group = ensure_group(vehicle.vehicle_number, vehicle, vehicle.company)
            if not group['records']:
                group['records'].append(_vehicle_fallback_record(vehicle, request))

        for document in FleetVehicleDocument.objects.filter(company_id__in=company_ids).select_related('vehicle', 'vehicle_record', 'company'):
            group = ensure_group(document.vehicle_number, document.vehicle, document.company)
            group['documents'].append(_vm_document_payload(request, document))

        def resolve_record(group, obj, date_value=None):
            record_payload = _record_for_object(obj)
            if record_payload:
                return record_payload
            vehicle = getattr(obj, 'vehicle', None)
            if vehicle:
                candidates = [r for r in group['records'] if r.get('vehicleApiId') == vehicle.id]
                return _record_for_date(candidates or group['records'], date_value)
            return _record_for_date(group['records'], date_value)

        for contract in FleetSubscriptionContract.objects.filter(company_id__in=company_ids).select_related('vehicle', 'vehicle_record', 'company'):
            vehicle = contract.vehicle
            group = ensure_group(contract.vehicle_number, vehicle, contract.company)
            record = resolve_record(group, contract, _vm_date(contract.start_date))
            vin = record.get('vin') if record else (vehicle.vin_tid if vehicle else '')
            group['subscriptions'].append({
                'id': f'SUB-{contract.id}',
                'apiId': contract.id,
                'companyId': contract.company_id,
                'companyCode': contract.company.code if contract.company_id else '',
                'vehicleId': record.get('id') if record else (f'VEH-{vehicle.id}' if vehicle else ''),
                'vin': vin,
                'plate': contract.vehicle_number,
                'customer': contract.customer,
                'contact': contract.contact,
                'start': _vm_date(contract.start_date),
                'end': _vm_date(contract.end_date),
                'monthlyFee': contract.monthly_fee,
                'deposit': contract.deposit,
                'status': contract.status,
                'signStatus': contract.sign_status,
                'file': _vm_file_payload(request, contract.contract_file, contract.updated_at),
                'note': contract.note,
            })

        for record in FleetReturnRecord.objects.filter(company_id__in=company_ids).select_related('vehicle', 'vehicle_record', 'subscription', 'company'):
            vehicle = record.vehicle
            group = ensure_group(record.vehicle_number, vehicle, record.company)
            vehicle_record = resolve_record(group, record, _vm_date(record.actual_at.date() if record.actual_at else record.scheduled_at.date()))
            group['returns'].append({
                'id': f'RET-{record.id}',
                'apiId': record.id,
                'companyId': record.company_id,
                'companyCode': record.company.code if record.company_id else '',
                'subscriptionId': f'SUB-{record.subscription_id}' if record.subscription_id else '',
                'vehicleId': vehicle_record.get('id') if vehicle_record else (f'VEH-{vehicle.id}' if vehicle else ''),
                'plate': record.vehicle_number,
                'customer': record.customer,
                'scheduled': _vm_datetime(record.scheduled_at),
                'actual': _vm_datetime(record.actual_at),
                'location': record.location,
                'status': record.status,
                'photos': record.photos or [],
                'checks': record.checks or [],
                'note': record.note,
                'repairs': record.repairs or [],
            })

        for policy in FleetInsurancePolicy.objects.filter(company_id__in=company_ids).select_related('vehicle', 'vehicle_record', 'company'):
            vehicle = policy.vehicle
            group = ensure_group(policy.vehicle_number, vehicle, policy.company)
            record = resolve_record(group, policy, _vm_date(policy.start_date))
            group['insurances'].append({
                'id': f'INS-{policy.id}',
                'apiId': policy.id,
                'companyId': policy.company_id,
                'companyCode': policy.company.code if policy.company_id else '',
                'vehicleId': record.get('id') if record else (f'VEH-{vehicle.id}' if vehicle else ''),
                'vin': record.get('vin') if record else (vehicle.vin_tid if vehicle else ''),
                'plate': policy.vehicle_number,
                'insurer': policy.insurer,
                'policyNo': policy.policy_no,
                'start': _vm_date(policy.start_date),
                'end': _vm_date(policy.end_date),
                'previousRate': float(policy.previous_rate),
                'currentRate': float(policy.current_rate),
                'status': policy.status,
                'payments': policy.payments or [],
                'note': policy.note,
            })

        for accident in FleetAccidentCase.objects.filter(company_id__in=company_ids).select_related('vehicle', 'vehicle_record', 'company'):
            vehicle = accident.vehicle
            group = ensure_group(accident.vehicle_number, vehicle, accident.company)
            record = resolve_record(group, accident, _vm_date(accident.accident_at.date()))
            group['accidents'].append({
                'id': f'ACC-{accident.id}',
                'apiId': accident.id,
                'companyId': accident.company_id,
                'companyCode': accident.company.code if accident.company_id else '',
                'sourceKey': accident.source_key,
                'vehicleId': record.get('id') if record else (f'VEH-{vehicle.id}' if vehicle else ''),
                'vin': accident.vehicle_vin or (record.get('vin') if record else (vehicle.vin_tid if vehicle else '')),
                'plate': accident.vehicle_number,
                'driver': accident.driver,
                'date': _vm_datetime(accident.accident_at),
                'location': accident.location,
                'description': accident.description,
                'coverage': accident.coverage,
                'victim': accident.victim,
                'compensation': accident.compensation,
                'personalCompensation': accident.personal_compensation,
                'propertyCompensation': accident.property_compensation,
                'paid': accident.paid,
                'manager': accident.manager,
                'status': accident.status,
                'compensationNote': accident.compensation_note,
                'items': accident.items or [],
            })

        for group in groups.values():
            if not group['records']:
                group['records'].append(_orphan_history_record(group['plate']))

        evdash_by_plate = get_fleet_evdash(vehicles)
        for group in groups.values():
            group['evdash'] = evdash_by_plate.get(group['plate'], {
                'configured': True,
                'matched': False,
                'detail': 'EV Dashboard 차량 목록에서 일치하는 차량을 찾지 못했습니다.',
                'location': {'has_location': False, 'latitude': None, 'longitude': None},
                'summary': {'observed_at': None, 'age_seconds': None, 'online': None, 'online_label': '미수신', 'tone': 'slate'},
                'errors': {'has_error': False, 'items': [], 'count': 0},
            })

        return Response({
            'company': {'id': default_company.id, 'code': default_company.code, 'name': default_company.name},
            'companies': [
                {'id': company.id, 'code': company.code, 'name': company.name}
                for company in companies
            ],
            'groups': list(groups.values()),
        })

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def replacement(self, request):
        company_id = request.data.get('company')
        company_code = request.data.get('company_code') or request.query_params.get('company') or 'CHEONHA'
        company = Company.objects.filter(id=company_id).first() if company_id else Company.objects.filter(code=company_code).first()
        if not company:
            return Response({'detail': 'Unknown vehicle company.'}, status=404)

        vehicle_number = (request.data.get('vehicle_number') or '').strip()
        new_vehicle_number = (
            request.data.get('new_vehicle_number')
            or request.data.get('newVehicleNumber')
            or request.data.get('new_plate')
            or ''
        ).strip()
        old_end = request.data.get('old_end')
        new_start = request.data.get('new_start')
        requested_vin = (request.data.get('vin') or '').strip()
        model = (request.data.get('model') or '').strip()
        certificate_name = (request.data.get('certificate_name') or '').strip()
        if not vehicle_number or not new_vehicle_number or not old_end or not new_start:
            raise serializers.ValidationError({
                'detail': 'vehicle_number, new_vehicle_number, old_end, new_start are required.',
            })
        if vehicle_number == new_vehicle_number:
            raise serializers.ValidationError({
                'detail': 'new_vehicle_number must be different from vehicle_number.',
            })

        vehicle = _find_vehicle(company, vehicle_number)
        if not vehicle:
            if len(requested_vin) < 10:
                raise serializers.ValidationError({
                    'detail': 'Existing vehicle was not found. vin is required to create the vehicle.',
                })
            vehicle = Vehicle.objects.create(
                company=company,
                vehicle_number=vehicle_number,
                vin_tid=requested_vin,
                model=model,
                shipped_at=new_start,
                placement_status='OPERATING',
                operation_type='SUBSCRIPTION',
            )
        if _vehicle_number_conflict_qs(
            company,
            new_vehicle_number,
            active=True,
            exclude_vehicle=vehicle,
        ).exists():
            raise serializers.ValidationError({
                'detail': 'new_vehicle_number already exists as an active vehicle.',
            })
        _archive_inactive_vehicle_number_conflicts(
            company,
            new_vehicle_number,
            exclude_vehicle=vehicle,
        )

        existing_records = list(
            FleetVehicleRecord.objects.select_for_update()
            .filter(company=company, vehicle_number=vehicle_number)
            .order_by('start_date', 'id')
        )
        current_record = (
            FleetVehicleRecord.objects.select_for_update()
            .filter(company=company)
            .filter(Q(vehicle=vehicle) | Q(vehicle_number=vehicle_number))
            .filter(end_date__isnull=True)
            .order_by('-start_date', '-id')
            .first()
        )
        same_vin = vehicle.vin_tid or (current_record.vin if current_record else '') or requested_vin
        if not same_vin:
            raise serializers.ValidationError({
                'detail': 'The current VIN could not be resolved.',
            })
        model = model or vehicle.model or (current_record.model if current_record else '')

        if not existing_records:
            FleetVehicleRecord.objects.create(
                company=company,
                vehicle=vehicle,
                vehicle_number=vehicle_number,
                vin=same_vin,
                model=vehicle.model or model,
                start_date=vehicle.shipped_at or vehicle.created_at.date(),
                end_date=old_end,
                status='대폐차',
                certificate_name=vehicle.registration_certificate.name.rsplit('/', 1)[-1] if vehicle.registration_certificate else '',
                certificate_uploaded_at=vehicle.registration_certificate_uploaded_at.date() if vehicle.registration_certificate_uploaded_at else None,
                created_by=request.user,
            )
        else:
            FleetVehicleRecord.objects.filter(
                company=company,
                vehicle_number=vehicle_number,
                end_date__isnull=True,
            ).update(end_date=old_end, status='대폐차')

        new_record = FleetVehicleRecord.objects.create(
            company=company,
            vehicle=vehicle,
            vehicle_number=new_vehicle_number,
            vin=same_vin,
            model=model or vehicle.model,
            start_date=new_start,
            end_date=None,
            status='운행중',
            certificate_name=certificate_name,
            certificate_uploaded_at=new_start if certificate_name else None,
            created_by=request.user,
        )

        vehicle.vehicle_number = new_vehicle_number
        vehicle.vehicle_number_short = _vehicle_number_short(new_vehicle_number)
        vehicle.vin_tid = same_vin
        vehicle.model = model or vehicle.model
        vehicle.shipped_at = new_start
        vehicle.placement_status = 'OPERATING'
        vehicle.is_active = True
        vehicle.save(update_fields=[
            'vehicle_number', 'vehicle_number_short', 'vin_tid', 'model',
            'shipped_at', 'placement_status', 'is_active', 'updated_at',
        ])
        return Response({
            'record': _fleet_record_payload(new_record),
            'old_vehicle_number': vehicle_number,
            'new_vehicle_number': new_vehicle_number,
        }, status=status.HTTP_201_CREATED)


class FleetModelCreateMixin:
    def perform_create(self, serializer):
        company = serializer.validated_data.get('company')
        vehicle_record = serializer.validated_data.get('vehicle_record')
        vehicle = serializer.validated_data.get('vehicle')
        vehicle_number = serializer.validated_data.get('vehicle_number')
        if vehicle_record:
            vehicle = vehicle_record.vehicle or vehicle
            vehicle_number = vehicle_record.vehicle_number or vehicle_number
        if not vehicle:
            vehicle = _find_vehicle(company, vehicle_number)
        serializer.save(vehicle=vehicle, vehicle_number=vehicle_number, created_by=self.request.user)


ACTIVE_FLEET_SUBSCRIPTION_STATUSES = {'계약예정', '구독중', '반납진행'}
RETURN_PROGRESS_STATUSES = {'반납예정', '검수중'}
RETURN_COMPLETED_STATUSES = {'완료', '반납완료', '종료'}
SUBSCRIPTION_CLOSED_STATUS = '종료'
SUBSCRIPTION_RETURN_PROGRESS_STATUS = '반납진행'


def _fleet_subscription_overlap_queryset(company, vehicle_number, start_date, end_date, exclude_id=None):
    if not company or not vehicle_number or not start_date or not end_date:
        return FleetSubscriptionContract.objects.none()
    qs = FleetSubscriptionContract.objects.filter(
        company=company,
        vehicle_number=vehicle_number,
        status__in=ACTIVE_FLEET_SUBSCRIPTION_STATUSES,
        start_date__lte=end_date,
        end_date__gte=start_date,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs


def _find_active_subscription_for_return(return_record):
    if getattr(return_record, 'subscription', None):
        return return_record.subscription
    company = getattr(return_record, 'company', None)
    vehicle_number = getattr(return_record, 'vehicle_number', None)
    if not company or not vehicle_number:
        return None
    target_at = return_record.actual_at or return_record.scheduled_at
    target_date = timezone.localtime(target_at).date() if target_at else None
    qs = FleetSubscriptionContract.objects.filter(
        company=company,
        vehicle_number=vehicle_number,
        status__in=ACTIVE_FLEET_SUBSCRIPTION_STATUSES,
    ).order_by('-start_date', '-id')
    if target_date:
        bounded = qs.filter(start_date__lte=target_date, end_date__gte=target_date).first()
        if bounded:
            return bounded
    return qs.first()


def _sync_subscription_return_status(return_record):
    subscription = getattr(return_record, 'subscription', None)
    if not subscription:
        subscription = _find_active_subscription_for_return(return_record)
        if subscription:
            return_record.subscription = subscription
            return_record.save(update_fields=['subscription', 'updated_at'])
        else:
            return

    update_fields = []
    has_actual_return = bool(return_record.actual_at)
    if return_record.status in RETURN_COMPLETED_STATUSES or has_actual_return:
        if subscription.status != SUBSCRIPTION_CLOSED_STATUS:
            subscription.status = SUBSCRIPTION_CLOSED_STATUS
            update_fields.append('status')
        completed_date = None
        if return_record.actual_at:
            completed_date = timezone.localtime(return_record.actual_at).date()
        elif return_record.scheduled_at:
            completed_date = timezone.localtime(return_record.scheduled_at).date()
        if completed_date and subscription.end_date != completed_date:
            subscription.end_date = completed_date
            update_fields.append('end_date')
    elif return_record.status in RETURN_PROGRESS_STATUSES and subscription.status in ACTIVE_FLEET_SUBSCRIPTION_STATUSES:
        subscription.status = SUBSCRIPTION_RETURN_PROGRESS_STATUS
        update_fields.append('status')

    if update_fields:
        subscription.save(update_fields=[*set(update_fields), 'updated_at'])


class FleetVehicleRecordViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = FleetVehicleRecord.objects.select_related('company', 'vehicle').all()
    serializer_class = FleetVehicleRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number', 'vin', 'model', 'certificate_name', 'note']

    @action(detail=True, methods=['post', 'patch'], url_path='status')
    @transaction.atomic
    def status(self, request, pk=None):
        """차량번호별 실제 차량 이력의 현재 운영상태를 변경한다."""
        record = self.get_object()
        label = _normalize_fleet_operation_status(request.data.get('status'))
        if not label:
            return Response(
                {'detail': 'status must be one of 유휴, A/S, 판매, 구독, 직영.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle = record.vehicle or _find_vehicle(record.company, record.vehicle_number)
        label = _apply_fleet_operation_status(record=record, vehicle=vehicle, status_value=label)
        return Response({
            'status': label,
            'open_subscription': label == '구독',
            'record': _fleet_record_payload(record, request),
        })


class FleetVehicleDocumentViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = FleetVehicleDocument.objects.select_related('company', 'vehicle', 'vehicle_record').all()
    serializer_class = FleetVehicleDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number', 'document_type', 'note']

    def get_queryset(self):
        qs = super().get_queryset()
        vehicle_number = self.request.query_params.get('vehicle_number')
        document_type = self.request.query_params.get('document_type')
        if vehicle_number:
            qs = qs.filter(vehicle_number=vehicle_number)
        if document_type:
            qs = qs.filter(document_type=document_type)
        return qs

    def perform_create(self, serializer):
        company = serializer.validated_data.get('company')
        vehicle_record = serializer.validated_data.get('vehicle_record')
        vehicle = serializer.validated_data.get('vehicle')
        vehicle_number = serializer.validated_data.get('vehicle_number')
        if vehicle_record:
            vehicle = vehicle_record.vehicle or vehicle
            vehicle_number = vehicle_record.vehicle_number or vehicle_number
        if not vehicle:
            vehicle = _find_vehicle(company, vehicle_number)
        serializer.save(vehicle=vehicle, vehicle_number=vehicle_number, created_by=self.request.user)


class FleetSubscriptionContractViewSet(CompanyScopedMixin, FleetModelCreateMixin, viewsets.ModelViewSet):
    queryset = FleetSubscriptionContract.objects.select_related('company', 'vehicle').all()
    serializer_class = FleetSubscriptionContractSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number', 'customer', 'contact', 'note']

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs

    def _resolve_vehicle_payload(self, validated_data):
        if self.action in {'partial_update', 'update'}:
            instance = self.get_object()
            company = validated_data.get('company') or instance.company
            vehicle_record = validated_data.get('vehicle_record') or instance.vehicle_record
            vehicle = validated_data.get('vehicle') or instance.vehicle
            vehicle_number = validated_data.get('vehicle_number') or instance.vehicle_number
        else:
            company = validated_data.get('company')
            vehicle_record = validated_data.get('vehicle_record')
            vehicle = validated_data.get('vehicle')
            vehicle_number = validated_data.get('vehicle_number')

        if vehicle_record:
            vehicle = vehicle_record.vehicle or vehicle
            vehicle_number = vehicle_record.vehicle_number or vehicle_number
        if not vehicle:
            vehicle = _find_vehicle(company, vehicle_number)
        return company, vehicle_record, vehicle, vehicle_number

    def _validate_single_active_contract(self, serializer, instance=None):
        data = serializer.validated_data
        company, _vehicle_record, _vehicle, vehicle_number = self._resolve_vehicle_payload(data)
        start_date = data.get('start_date') or getattr(instance, 'start_date', None)
        end_date = data.get('end_date') or getattr(instance, 'end_date', None)
        contract_status = data.get('status') or getattr(instance, 'status', None)
        if contract_status not in ACTIVE_FLEET_SUBSCRIPTION_STATUSES:
            return
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({'detail': '계약 시작일은 종료일보다 늦을 수 없습니다.'})
        overlapping = _fleet_subscription_overlap_queryset(
            company,
            vehicle_number,
            start_date,
            end_date,
            exclude_id=getattr(instance, 'pk', None),
        )
        if overlapping.exists():
            raise serializers.ValidationError({
                'detail': '같은 차량의 동일 기간에 활성 구독 계약이 이미 있습니다. 기존 계약을 반납 처리한 뒤 등록해주세요.'
            })

    def perform_create(self, serializer):
        self._validate_single_active_contract(serializer)
        company, vehicle_record, vehicle, vehicle_number = self._resolve_vehicle_payload(serializer.validated_data)
        serializer.save(
            company=company,
            vehicle=vehicle,
            vehicle_record=vehicle_record,
            vehicle_number=vehicle_number,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        clear_contract_file = serializer.validated_data.pop('clear_contract_file', False)
        self._validate_single_active_contract(serializer, self.get_object())
        instance = serializer.save()
        if clear_contract_file and not self.request.FILES.get('contract_file'):
            if instance.contract_file:
                instance.contract_file.delete(save=False)
            instance.contract_file = ''
            instance.save(update_fields=['contract_file', 'updated_at'])


class FleetReturnRecordViewSet(CompanyScopedMixin, FleetModelCreateMixin, viewsets.ModelViewSet):
    queryset = FleetReturnRecord.objects.select_related('company', 'vehicle', 'subscription').all()
    serializer_class = FleetReturnRecordSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number', 'customer', 'location', 'note']

    def perform_create(self, serializer):
        subscription = serializer.validated_data.get('subscription')
        company = serializer.validated_data.get('company')
        vehicle_record = serializer.validated_data.get('vehicle_record') or (subscription.vehicle_record if subscription else None)
        vehicle = serializer.validated_data.get('vehicle') or (vehicle_record.vehicle if vehicle_record else None) or (subscription.vehicle if subscription else None)
        vehicle_number = serializer.validated_data.get('vehicle_number') or (subscription.vehicle_number if subscription else '')
        customer = serializer.validated_data.get('customer') or (subscription.customer if subscription else '')
        if vehicle_record:
            vehicle_number = vehicle_record.vehicle_number or vehicle_number
        if not vehicle:
            vehicle = _find_vehicle(company, vehicle_number)
        record = serializer.save(vehicle=vehicle, vehicle_record=vehicle_record, vehicle_number=vehicle_number, customer=customer, created_by=self.request.user)
        _sync_subscription_return_status(record)

    def perform_update(self, serializer):
        record = serializer.save()
        _sync_subscription_return_status(record)

    @action(detail=True, methods=['post'], url_path='photos')
    def upload_photo(self, request, pk=None):
        record = self.get_object()
        uploaded = request.FILES.get('file') or request.FILES.get('photo')
        if not uploaded:
            return Response({'detail': 'file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if uploaded.size > 20 * 1024 * 1024:
            return Response({'detail': 'file must be 20MB or smaller.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = uploaded.name.rsplit('.', 1)[-1].lower() if '.' in uploaded.name else ''
        if ext not in {'jpg', 'jpeg', 'png', 'webp', 'heic', 'heif'}:
            return Response({'detail': 'Unsupported image file type.'}, status=status.HTTP_400_BAD_REQUEST)

        label = (request.data.get('label') or uploaded.name).strip()
        key = uuid4().hex
        path = f'fleet_return_photos/{record.company_id}/{record.id}/{key}.{ext}'
        saved_path = default_storage.save(path, uploaded)
        file_url = default_storage.url(saved_path)
        absolute_url = request.build_absolute_uri(file_url)
        photo = {
            'id': key,
            'label': label,
            'name': uploaded.name,
            'url': absolute_url,
            'mime': uploaded.content_type or '',
            'uploaded': timezone.localtime(timezone.now()).isoformat(),
        }

        photos = list(record.photos or [])
        photos = [item for item in photos if item.get('label') != label]
        photos.append(photo)
        record.photos = photos
        record.save(update_fields=['photos', 'updated_at'])
        return Response(photo, status=status.HTTP_201_CREATED)


class FleetInsurancePolicyViewSet(CompanyScopedMixin, FleetModelCreateMixin, viewsets.ModelViewSet):
    queryset = FleetInsurancePolicy.objects.select_related('company', 'vehicle').all()
    serializer_class = FleetInsurancePolicySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['vehicle_number', 'insurer', 'policy_no', 'note']


ACCIDENT_HISTORY_COLUMNS = {
    'company_name': {'조합원명', '회사명', '소속'},
    'source_key': {'사고번호', '접수번호', '사고접수번호', '보상번호'},
    'status': {'상태', '처리상태', '진행상태'},
    'vehicle_number': {'차량번호', '차량 번호', '차번', '자동차번호'},
    'vehicle_vin': {'차대번호', 'VIN', '실제차대번호'},
    'driver': {'운전자', '운전자명', '기사', '기사명'},
    'accident_at': {'사고일시', '사고 일시', '사고일', '사고일자', '발생일시', '발생일'},
    'location': {'사고장소', '사고 장소', '장소', '위치'},
    'description': {'사고내용', '사고 내용', '내용', '비고', '특이사항'},
    'coverage': {'담보', '담보구분', '보상담보'},
    'victim': {'피해자', '피해물', '피해자/물', '피해내용'},
    'manager': {'담당자', '관리자', '처리자'},
}


def _vm_text(value):
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    return str(value).strip()


def _vm_header(value):
    return re.sub(r'[\s_./\\()\[\]-]+', '', _vm_text(value)).lower()


def _vm_header_aliases():
    aliases = {}
    for key, names in ACCIDENT_HISTORY_COLUMNS.items():
        for name in names:
            aliases[_vm_header(name)] = key
    return aliases


def _parse_vm_datetime(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    parsed = pd.to_datetime(value, errors='coerce')
    if pd.isna(parsed):
        return None
    dt = parsed.to_pydatetime()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _read_fleet_accident_frames(uploaded):
    name = (uploaded.name or '').lower()
    data = uploaded.read()
    if name.endswith('.csv'):
        last_error = None
        for encoding in ('utf-8-sig', 'cp949', 'euc-kr'):
            try:
                return {'CSV': pd.read_csv(io.BytesIO(data), header=None, dtype=object, encoding=encoding)}
            except Exception as exc:
                last_error = exc
        raise last_error
    if name.endswith('.xls') and not name.endswith('.xlsx'):
        return pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=object, engine='xlrd')
    return pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=object, engine='openpyxl')


def _extract_fleet_accident_rows(frame):
    aliases = _vm_header_aliases()
    header_index = None
    mapped = {}
    for idx, row in frame.iterrows():
        current = {}
        for col_idx, raw_header in enumerate(row.tolist()):
            key = aliases.get(_vm_header(raw_header))
            if key:
                current[col_idx] = key
        if len(current) >= 4 and 'vehicle_number' in current.values() and 'accident_at' in current.values():
            header_index = idx
            mapped = current
            break
    if header_index is None:
        return []

    rows = []
    for _, raw in frame.iloc[header_index + 1:].iterrows():
        item = {}
        for col_idx, key in mapped.items():
            item[key] = raw.iloc[col_idx] if col_idx < len(raw) else None
        if not any(_vm_text(value) for value in item.values()):
            continue
        accident_at = _parse_vm_datetime(item.get('accident_at'))
        vehicle_number = _vm_text(item.get('vehicle_number'))
        source_key = _vm_text(item.get('source_key'))
        if not vehicle_number and not accident_at and not source_key:
            continue
        row = {
            'source_key': source_key,
            'vehicle_number': vehicle_number,
            'vehicle_vin': _vm_text(item.get('vehicle_vin')),
            'driver': _vm_text(item.get('driver')),
            'accident_at': accident_at,
            'location': _vm_text(item.get('location')),
            'description': _vm_text(item.get('description')),
            'coverage': _vm_text(item.get('coverage')),
            'victim': _vm_text(item.get('victim')),
            'manager': _vm_text(item.get('manager')),
            'status': _vm_text(item.get('status')) or '진행중',
            'items': [{
                'kind': 'source_row',
                'company_name': _vm_text(item.get('company_name')),
                'raw': {key: _vm_text(value) for key, value in item.items()},
            }],
        }
        rows.append(row)
    return rows


def _parse_fleet_accident_history(uploaded):
    frames = _read_fleet_accident_frames(uploaded)
    rows = []
    for frame in frames.values():
        rows.extend(_extract_fleet_accident_rows(frame))
    if not rows:
        raise serializers.ValidationError('No accident history rows were found.')
    return rows


def _find_fleet_record_for_accident(company, vehicle_number, accident_at, vehicle=None):
    if not company or not vehicle_number:
        return None
    accident_date = timezone.localtime(accident_at).date() if accident_at else None
    qs = FleetVehicleRecord.objects.filter(company=company, vehicle_number=vehicle_number).order_by('-start_date', '-id')
    if accident_date:
        matched = qs.filter(start_date__lte=accident_date).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=accident_date)
        ).first()
        if matched:
            return matched
    return qs.first()


class FleetAccidentCaseViewSet(CompanyScopedMixin, FleetModelCreateMixin, viewsets.ModelViewSet):
    queryset = FleetAccidentCase.objects.select_related('company', 'vehicle').all()
    serializer_class = FleetAccidentCaseSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['source_key', 'vehicle_number', 'vehicle_vin', 'driver', 'location', 'description']

    def perform_create(self, serializer):
        company = serializer.validated_data.get('company')
        vehicle_record = serializer.validated_data.get('vehicle_record')
        vehicle = serializer.validated_data.get('vehicle')
        vehicle_number = serializer.validated_data.get('vehicle_number')
        if vehicle_record:
            vehicle = vehicle_record.vehicle or vehicle
            vehicle_number = vehicle_record.vehicle_number or vehicle_number
        if not vehicle:
            vehicle = _find_vehicle(company, vehicle_number)
        vehicle_vin = serializer.validated_data.get('vehicle_vin') or (vehicle_record.vin if vehicle_record else '') or (vehicle.vin_tid if vehicle else '')
        serializer.save(vehicle=vehicle, vehicle_record=vehicle_record, vehicle_number=vehicle_number, vehicle_vin=vehicle_vin, created_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='upload-template')
    def upload_template(self, request):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = '전체'
        sheet.append(['조합원명', '사고번호', '상태', '차량번호', '운전자', '사고일시', '사고장소'])
        sheet.append(['이브이앤솔루션(주)', '2230-00000', '종결', '전북91사0000', '홍길동', '2026.06.01 09:00', '사고 장소'])
        stream = io.BytesIO()
        workbook.save(stream)
        stream.seek(0)
        response = HttpResponse(
            stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="fleet_accident_history_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], url_path='upload-history')
    @transaction.atomic
    def upload_history(self, request):
        uploaded = request.FILES.get('file') or request.FILES.get('excel')
        if not uploaded:
            return Response({'detail': 'file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        company_id = request.data.get('company')
        company_code = request.data.get('company_code') or request.query_params.get('company') or 'CHEONHA'
        company = Company.objects.filter(id=company_id).first() if company_id else Company.objects.filter(code=company_code).first()
        if not company:
            return Response({'detail': 'Unknown vehicle company.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            rows = _parse_fleet_accident_history(uploaded)
        except Exception as exc:
            return Response({'detail': f'Cannot parse accident history file: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

        created = 0
        updated = 0
        skipped = []
        for index, row in enumerate(rows, start=1):
            source_key = _vm_text(row.get('source_key'))
            vehicle_number = _vm_text(row.get('vehicle_number'))
            accident_at = row.get('accident_at')
            if not vehicle_number or not accident_at:
                skipped.append({'row': index, 'reason': 'vehicle_number and accident_at are required.'})
                continue

            vehicle = _find_vehicle(company, vehicle_number)
            vehicle_record = _find_fleet_record_for_accident(company, vehicle_number, accident_at, vehicle)
            vehicle_vin = _vm_text(row.get('vehicle_vin')) or (vehicle_record.vin if vehicle_record else '') or (vehicle.vin_tid if vehicle else '')
            defaults = {
                'vehicle': vehicle,
                'vehicle_record': vehicle_record,
                'vehicle_number': vehicle_number,
                'vehicle_vin': vehicle_vin,
                'driver': _vm_text(row.get('driver')),
                'accident_at': accident_at,
                'location': _vm_text(row.get('location')),
                'description': _vm_text(row.get('description')),
                'coverage': _vm_text(row.get('coverage')),
                'victim': _vm_text(row.get('victim')),
                'manager': _vm_text(row.get('manager')),
                'status': _vm_text(row.get('status')) or '진행중',
                'items': row.get('items') or [],
            }
            if source_key:
                obj, was_created = FleetAccidentCase.objects.get_or_create(
                    company=company,
                    source_key=source_key,
                    defaults={**defaults, 'created_by': request.user},
                )
            else:
                obj, was_created = FleetAccidentCase.objects.get_or_create(
                    company=company,
                    vehicle_number=vehicle_number,
                    accident_at=accident_at,
                    driver=defaults['driver'],
                    defaults={**defaults, 'created_by': request.user},
                )
            if was_created:
                created += 1
                continue

            dirty_fields = []
            for field, value in defaults.items():
                if field == 'items':
                    existing_items = list(obj.items or [])
                    raw_marker = {'kind': 'uploaded_source', 'data': value}
                    if value and not any(item.get('kind') == 'uploaded_source' for item in existing_items if isinstance(item, dict)):
                        obj.items = [*existing_items, raw_marker]
                        dirty_fields.append('items')
                    continue
                if getattr(obj, field) != value:
                    setattr(obj, field, value)
                    dirty_fields.append(field)
            if source_key and obj.source_key != source_key:
                obj.source_key = source_key
                dirty_fields.append('source_key')
            if dirty_fields:
                obj.save(update_fields=[*set(dirty_fields), 'updated_at'])
            updated += 1

        return Response({
            'total': len(rows),
            'created': created,
            'updated': updated,
            'skipped': len(skipped),
            'errors': skipped[:50],
        })


class ASRequestViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = ASRequest.objects.select_related('company').all()
    serializer_class = ASRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """A/S 처리 완료 — 코멘트 + 캘린더 내용 입력."""
        req = self.get_object()
        s = CompleteASSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        req.admin_comment = s.validated_data.get('admin_comment', '')
        req.calendar_note = s.validated_data.get('calendar_note', '')
        req.status = s.validated_data['status']
        req.completed_at = timezone.now()
        req.save(update_fields=['admin_comment', 'calendar_note', 'status', 'completed_at', 'updated_at'])
        vehicle = Vehicle.objects.filter(
            company=req.company,
            vehicle_number=req.vehicle_number,
            is_active=True,
        ).first()
        if vehicle and req.status in {'REPAIRING', 'OPERATING'}:
            vehicle.placement_status = req.status
            vehicle.save(update_fields=['placement_status', 'updated_at'])
        return Response(self.get_serializer(req).data)
