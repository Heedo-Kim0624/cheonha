import logging
import math
from decimal import Decimal
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.views import BaseViewSet
from apps.common.company_scope import get_company_app_from_request
from apps.accounts.models import Team
from apps.dispatch.date_utils import date_iso, to_work_date
from apps.dispatch.settlement_services import build_region_allocations, is_effective_yongcha, replace_settlement_details_for_crew_upload
from apps.mobile.models import MobileAppMessageConfig
from apps.settlement.models import Settlement, SettlementDetail
from .models import CrewMember, OvertimeSetting, YongchaPayGroup
from .serializers import (
    CrewMemberSerializer,
    OvertimeSettingSerializer,
    YongchaPayGroupSerializer,
    parse_app_version_code,
    yongcha_pay_group_round_detail,
    yongcha_pay_group_round_name,
    yongcha_pay_group_round_extra_pay,
)

logger = logging.getLogger(__name__)


def _parse_month_bounds(month_value):
    month_value = (month_value or "").strip()
    if not month_value:
        today = date.today()
        month_value = today.strftime("%Y-%m")
    try:
        year_str, month_str = month_value.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        if month < 1 or month > 12:
            raise ValueError
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return month_value, start, end
    except Exception:
        return month_value, None, None


def _detail_households(detail, cache):
    if not detail.dispatch_upload_id or not detail.crew_member_id:
        return 0

    cache_key = (detail.dispatch_upload_id, detail.crew_member_id)
    if cache_key not in cache:
        from apps.dispatch.models import DispatchRecord

        names = {
            str(getattr(detail.crew_member, "code", "") or "").strip(),
            str(getattr(detail.crew_member, "name", "") or "").strip(),
        }
        names = [name for name in names if name]
        records = DispatchRecord.objects.filter(
            upload_id=detail.dispatch_upload_id,
            is_valid=True,
            manager_name__in=names,
        )
        cache[cache_key] = build_region_allocations(records)

    return int(cache[cache_key].get(detail.region, {}).get("households", 0) or 0)


def _format_yongcha_label(values):
    values = {bool(value) for value in values}
    if values == {True}:
        return "예"
    if values == {False}:
        return "아니오"
    return "혼합"


class YongchaPayGroupViewSet(BaseViewSet):
    serializer_class = YongchaPayGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_app = get_company_app_from_request(self.request)
        queryset = YongchaPayGroup.objects.filter(company_app=company_app)
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(
                is_active=str(is_active).lower() not in ('0', 'false', 'no', 'n')
            )
        return queryset.order_by('name', 'id')

    def perform_create(self, serializer):
        serializer.save(
            company_app=get_company_app_from_request(self.request),
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        company_app = get_company_app_from_request(self.request)
        suffix = f" [deleted:{instance.pk}]"
        base_name = (instance.name or "")[: max(0, 100 - len(suffix))]
        with transaction.atomic():
            CrewMember.objects.filter(
                yongcha_pay_group=instance,
                team__company_app=company_app,
            ).update(yongcha_pay_group=None)
            instance.name = f"{base_name}{suffix}"
            instance.is_active = False
            instance.updated_by = self.request.user
            instance.save(update_fields=["name", "is_active", "updated_by", "updated_at"])

    @action(detail=True, methods=["get"], url_path="settlement-summary")
    def settlement_summary(self, request, pk=None):
        pay_group = self.get_object()
        month_value, month_start, month_end = _parse_month_bounds(request.query_params.get("month"))
        if not month_start or not month_end:
            return Response({"detail": f"올바르지 않은 month 값입니다: {month_value}"}, status=status.HTTP_400_BAD_REQUEST)

        crew_queryset = (
            CrewMember.objects
            .filter(
                yongcha_pay_group=pay_group,
                is_active=True,
                team__company_app=get_company_app_from_request(request),
            )
            .select_related("team", "yongcha_pay_group")
            .order_by("team__code", "name", "code")
        )
        crew_ids = list(crew_queryset.values_list("id", flat=True))
        details = (
            SettlementDetail.objects
            .filter(
                crew_member_id__in=crew_ids,
                is_yongcha=True,
                settlement__period_start__gte=month_start,
                settlement__period_start__lte=month_end,
            )
            .select_related("settlement", "settlement__team", "dispatch_upload", "crew_member", "crew_member__team")
            .order_by("-settlement__period_start", "id")
        )

        household_cache = {}
        daily = {}
        member_stats = {
            crew.id: {
                "id": crew.id,
                "name": crew.name,
                "code": crew.code,
                "team_name": crew.team.name if crew.team else "",
                "boxes": 0,
                "households": 0,
                "receive_amount": 0,
                "pay_amount": 0,
            }
            for crew in crew_queryset
        }

        totals = {
            "households": 0,
            "boxes": 0,
            "receive_amount": 0,
            "pay_amount": 0,
        }

        for detail in details:
            delivery_date = detail.settlement.period_start if detail.settlement else None
            date_key = date_iso(delivery_date)
            households = _detail_households(detail, household_cache)
            boxes = int(detail.boxes or 0)
            receive_amount = int(detail.receive_amount or 0)
            pay_amount = int(detail.pay_amount or 0)

            if date_key not in daily:
                daily[date_key] = {
                    "date": date_key,
                    "work_date": date_iso(to_work_date(delivery_date)),
                    "households": 0,
                    "boxes": 0,
                    "receive_amount": 0,
                    "pay_amount": 0,
                }
            daily[date_key]["households"] += households
            daily[date_key]["boxes"] += boxes
            daily[date_key]["receive_amount"] += receive_amount
            daily[date_key]["pay_amount"] += pay_amount

            for key, value in (
                ("households", households),
                ("boxes", boxes),
                ("receive_amount", receive_amount),
                ("pay_amount", pay_amount),
            ):
                totals[key] += value

            member_row = member_stats.get(detail.crew_member_id)
            if member_row:
                member_row["households"] += households
                member_row["boxes"] += boxes
                member_row["receive_amount"] += receive_amount
                member_row["pay_amount"] += pay_amount

        daily_rows = sorted(daily.values(), key=lambda item: item["date"], reverse=True)
        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = max(int(request.query_params.get("page_size", 10) or 10), 1)
        total_pages = max(math.ceil(len(daily_rows) / page_size), 1)
        start = (page - 1) * page_size
        end = start + page_size

        return Response({
            "group": {
                "id": pay_group.id,
                "name": pay_group.name,
            },
            "month": month_value,
            "totals": totals,
            "daily": {
                "count": len(daily_rows),
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "results": daily_rows[start:end],
            },
            "members": list(member_stats.values()),
        })


class CrewMemberViewSet(BaseViewSet):
    queryset = CrewMember.objects.filter(is_active=True)
    serializer_class = CrewMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['code', 'name', 'phone']
    ordering_fields = ['code', 'name', 'is_new']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        config = MobileAppMessageConfig.get_solo()
        context["latest_mobile_app_version_code"] = parse_app_version_code(
            config.merged_messages.get("app_update_latest_version_code", "")
        )
        return context

    def get_queryset(self):
        user = self.request.user
        company_app = get_company_app_from_request(self.request)
        is_yongcha = self.request.query_params.get('is_yongcha')
        team_name = self.request.query_params.get('team_name')
        search = (self.request.query_params.get('search') or '').strip()

        if user.is_admin() or user.is_staff:
            queryset = CrewMember.objects.filter(is_active=True, team__company_app=company_app)
        elif user.team:
            queryset = CrewMember.objects.filter(team=user.team, is_active=True)
        else:
            return CrewMember.objects.none()

        queryset = queryset.select_related(
            'team',
            'partner',
            'yongcha_pay_group',
            'mobile_app_user',
            'live_work_status',
        )

        if is_yongcha is not None:
            queryset = queryset.filter(
                is_yongcha=str(is_yongcha).lower() in ('1', 'true', 'yes', 'y')
            )

        if team_name:
            queryset = queryset.filter(team__name=team_name)

        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )

        return queryset

    def _inspection_status(self, crew_member):
        value = crew_member.vehicle_inspection_date
        if not value:
            return {
                'label': '미등록',
                'class_name': 'bg-gray-100 text-gray-500',
                'days_remaining': None,
            }

        days = (value - date.today()).days
        if days < 0:
            return {
                'label': f'{value} 만료',
                'class_name': 'bg-red-50 text-red-600',
                'days_remaining': days,
            }
        if days <= 30:
            return {
                'label': f'{value} D-{days}',
                'class_name': 'bg-amber-50 text-amber-700',
                'days_remaining': days,
            }
        return {
            'label': str(value),
            'class_name': 'bg-green-50 text-green-700',
            'days_remaining': days,
        }

    def _parse_month_filter(self, request):
        month_value = (request.query_params.get('month') or '').strip()
        if not month_value:
            return None, None
        try:
            year_str, month_str = month_value.split('-', 1)
            year = int(year_str)
            month = int(month_str)
            if month < 1 or month > 12:
                raise ValueError
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(year, month + 1, 1) - timedelta(days=1)
            return month_value, {
                'settlement__period_start__gte': month_start,
                'settlement__period_start__lte': month_end,
            }
        except Exception:
            return month_value, 'invalid'

    def _paginate(self, items):
        page = max(int(self.request.query_params.get('page', 1) or 1), 1)
        page_size = max(int(self.request.query_params.get('page_size', 20) or 20), 1)
        total_count = len(items)
        total_pages = max(math.ceil(total_count / page_size), 1)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'results': items[start:end],
        }

    def _positive_decimal(self, value):
        amount = Decimal(str(value or 0))
        return amount if amount > 0 else Decimal('0')

    def _member_round_override(self, crew_member, round_no):
        return self._positive_decimal(
            getattr(crew_member, f'personal_round_{round_no}_yongcha_pay_price', 0)
        )

    def _team_regular_round_rate(self, crew_member, round_no):
        team = getattr(crew_member, 'team', None)
        if not team:
            return Decimal('3000')
        team_value = self._positive_decimal(getattr(team, f'round_{round_no}_yongcha_pay_price', 0))
        if team_value > 0:
            return team_value
        general = self._positive_decimal(getattr(team, 'yongcha_pay_price', 0))
        return general if general > 0 else Decimal('3000')

    def _team_yongcha_round_rate(self, crew_member, round_no):
        team = getattr(crew_member, 'team', None)
        if not team:
            return Decimal('3000')
        team_value = self._positive_decimal(getattr(team, f'yongcha_round_{round_no}_pay_price', 0))
        if team_value > 0:
            return team_value
        member_general = self._positive_decimal(getattr(crew_member, 'yongcha_pay_price', 0))
        if member_general > 0:
            return member_general
        team_general = self._positive_decimal(getattr(team, 'yongcha_pay_price', 0))
        return team_general if team_general > 0 else Decimal('3000')

    def _regular_round_display_rate(self, crew_member, round_no):
        override = self._member_round_override(crew_member, round_no)
        return int(override if override > 0 else self._team_regular_round_rate(crew_member, round_no))

    def _yongcha_round_display_rate(self, crew_member, round_no):
        group_extra = yongcha_pay_group_round_extra_pay(crew_member, round_no)
        if group_extra > 0:
            return int(group_extra)
        override = self._member_round_override(crew_member, round_no)
        return int(override if override > 0 else self._team_yongcha_round_rate(crew_member, round_no))

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().select_related('team', 'partner', 'yongcha_pay_group').order_by('team__code', 'name', 'code')
        serializer = self.get_serializer(queryset, many=True)
        results = []
        inspection_by_id = {
            crew.id: self._inspection_status(crew)
            for crew in queryset
        }
        for row in serializer.data:
            row = dict(row)
            row['inspection_status'] = inspection_by_id.get(row['id'])
            results.append(row)

        if request.query_params.get('page') or request.query_params.get('page_size'):
            return Response(self._paginate(results))
        return Response(results)

    @action(detail=False, methods=['get'])
    def new_members(self, request):
        queryset = self.get_queryset().filter(is_new=True, is_yongcha=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def settlement_history(self, request, pk=None):
        crew_member = self.get_object()
        details = (
            SettlementDetail.objects.filter(crew_member=crew_member)
            .select_related('settlement')
            .order_by('-settlement__period_start')
        )

        result = []
        for detail in details:
            result.append({
                'id': detail.id,
                'settlement_id': detail.settlement.id,
                'period_start': date_iso(detail.settlement.period_start),
                'period_end': date_iso(detail.settlement.period_end),
                'work_period_start': date_iso(to_work_date(detail.settlement.period_start)),
                'work_period_end': date_iso(to_work_date(detail.settlement.period_end)),
                'team': detail.settlement.team.name if detail.settlement.team else '',
                'region': detail.region,
                'delivery_type': detail.delivery_type,
                'boxes': detail.boxes,
                'receive_amount': int(detail.receive_amount),
                'pay_amount': int(detail.pay_amount),
                'overtime_cost': int(detail.overtime_cost),
                'profit': int(detail.profit),
                'status': detail.settlement.status,
            })
        return Response(result)

    @action(detail=False, methods=['get'])
    def yongcha_summary(self, request):
        queryset = self.get_queryset().filter(is_yongcha=True).select_related('team', 'yongcha_pay_group')
        month_value, month_filter = self._parse_month_filter(request)
        if month_filter == 'invalid':
            return Response({'detail': f'올바르지 않은 month 값입니다: {month_value}'}, status=status.HTTP_400_BAD_REQUEST)
        team_name = request.query_params.get('team_name')
        search = (request.query_params.get('search') or '').strip()
        if team_name:
            queryset = queryset.filter(team__name=team_name)
        if search:
            queryset = queryset.filter(
                Q(code__icontains=search) |
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )

        result = []
        for crew in queryset.order_by('team__code', 'name', 'code'):
            detail_queryset = SettlementDetail.objects.filter(
                crew_member=crew,
                is_yongcha=True,
            )
            if month_filter:
                detail_queryset = detail_queryset.filter(**month_filter)
            agg = detail_queryset.aggregate(
                boxes=Sum('boxes'),
                receive=Sum('receive_amount'),
            )
            last_detail = detail_queryset.select_related('settlement').order_by('-settlement__period_start').first()
            result.append({
                'id': crew.id,
                'code': crew.code,
                'name': crew.name,
                'team': crew.team_id,
                'team_name': crew.team.name if crew.team else '',
                'team_code': crew.team.code if crew.team else '',
                'phone': crew.phone,
                'vehicle_number': crew.vehicle_number,
                'is_yongcha': crew.is_yongcha,
                'two_insurance_percent': float(crew.two_insurance_percent or 0),
                'pay_price': int(crew.pay_price or 0),
                'yongcha_pay_price': int(crew.yongcha_pay_price or 3000),
                'yongcha_pay_group': crew.yongcha_pay_group_id,
                'yongcha_pay_group_name': crew.yongcha_pay_group.name if crew.yongcha_pay_group else '',
                'regular_round_1_base_pay': int(crew.regular_round_1_base_pay or 0),
                'regular_round_2_base_pay': int(crew.regular_round_2_base_pay or 0),
                'regular_round_3_base_pay': int(crew.regular_round_3_base_pay or 0),
                'personal_round_1_yongcha_pay_price': int(crew.personal_round_1_yongcha_pay_price or 0),
                'personal_round_2_yongcha_pay_price': int(crew.personal_round_2_yongcha_pay_price or 0),
                'personal_round_3_yongcha_pay_price': int(crew.personal_round_3_yongcha_pay_price or 0),
                'yongcha_round_1_display_pay_price': self._yongcha_round_display_rate(crew, 1),
                'yongcha_round_2_display_pay_price': self._yongcha_round_display_rate(crew, 2),
                'yongcha_round_3_display_pay_price': self._yongcha_round_display_rate(crew, 3),
                'yongcha_pay_group_round_1_name': yongcha_pay_group_round_name(crew, 1),
                'yongcha_pay_group_round_2_name': yongcha_pay_group_round_name(crew, 2),
                'yongcha_pay_group_round_3_name': yongcha_pay_group_round_name(crew, 3),
                'yongcha_pay_group_round_1_detail': yongcha_pay_group_round_detail(crew, 1),
                'yongcha_pay_group_round_2_detail': yongcha_pay_group_round_detail(crew, 2),
                'yongcha_pay_group_round_3_detail': yongcha_pay_group_round_detail(crew, 3),
                'total_boxes': int(agg['boxes'] or 0),
                'total_receive': int(agg['receive'] or 0),
                'last_date': date_iso(
                    last_detail.settlement.period_start
                    if last_detail and last_detail.settlement
                    else None
                ),
            })
        if request.query_params.get('page') or request.query_params.get('page_size'):
            return Response(self._paginate(result))
        return Response(result)

    @action(detail=True, methods=['get'])
    def yongcha_daily(self, request, pk=None):
        crew_member = self.get_object()
        month_value, month_filter = self._parse_month_filter(request)
        if month_filter == 'invalid':
            return Response({'detail': f'올바르지 않은 month 값입니다: {month_value}'}, status=status.HTTP_400_BAD_REQUEST)
        details = SettlementDetail.objects.filter(
            crew_member=crew_member,
            is_yongcha=True,
        ).select_related('settlement')
        if month_filter:
            details = details.filter(**month_filter)

        rows = (
            details.values(
                'settlement__period_start',
                'settlement__team__name',
            )
            .annotate(
                boxes=Sum('boxes'),
                receive=Sum('receive_amount'),
            )
            .order_by('-settlement__period_start')
        )

        return Response([
            {
                'date': date_iso(row['settlement__period_start']),
                'work_date': date_iso(to_work_date(row['settlement__period_start'])),
                'team_name': row['settlement__team__name'] or '',
                'boxes': int(row['boxes'] or 0),
                'receive_amount': int(row['receive'] or 0),
            }
            for row in rows
        ])

    @action(detail=True, methods=['post'], url_path='set-insurance-percent')
    def set_insurance_percent(self, request, pk=None):
        crew_member = self.get_object()
        try:
            percent = Decimal(str(request.data.get('percent') or 0)).quantize(Decimal('0.01'))
        except Exception:
            return Response({'detail': '2대보험 공제율이 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if percent < 0 or percent > 100:
            return Response({'detail': '2대보험 공제율은 0 이상 100 이하로 입력해야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        apply_all = str(request.data.get('apply_all', False)).lower() in ('1', 'true', 'yes', 'y', 'on')
        now = timezone.now()
        if apply_all:
            company_app = get_company_app_from_request(request)
            queryset = CrewMember.objects.filter(
                is_active=True,
                yongcha_pay_group__isnull=True,
            )
            if request.user.is_admin() or request.user.is_staff:
                queryset = queryset.filter(team__company_app=company_app)
            elif request.user.team_id:
                queryset = queryset.filter(team_id=request.user.team_id)
            else:
                return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

            current_member_updated = queryset.filter(id=crew_member.id).exists()
            updated_count = queryset.update(
                two_insurance_percent=percent,
                updated_at=now,
            )
        else:
            crew_member.two_insurance_percent = percent
            crew_member.updated_at = now
            crew_member.save(update_fields=['two_insurance_percent', 'updated_at'])
            current_member_updated = True
            updated_count = 1

        crew_member.refresh_from_db(fields=['two_insurance_percent'])
        return Response({
            'detail': (
                f'용차팀을 제외한 {updated_count}명에게 2대보험 공제율 {percent}%를 적용했습니다.'
                if apply_all
                else f'{crew_member.name} 배송원에게 2대보험 공제율 {percent}%를 저장했습니다.'
            ),
            'percent': float(percent),
            'current_percent': float(crew_member.two_insurance_percent or 0),
            'apply_all': apply_all,
            'updated_count': updated_count,
            'current_member_updated': current_member_updated,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='monthly-settlement')
    def monthly_settlement(self, request, pk=None):
        crew_member = self.get_object()
        month_value, month_start, month_end = _parse_month_bounds(request.query_params.get('month'))
        if not month_start or not month_end:
            return Response({'detail': f'올바르지 않은 month 값입니다: {month_value}'}, status=status.HTTP_400_BAD_REQUEST)

        details = (
            SettlementDetail.objects
            .filter(
                crew_member=crew_member,
                settlement__period_start__gte=month_start,
                settlement__period_start__lte=month_end,
            )
            .select_related('settlement', 'settlement__team', 'dispatch_upload', 'crew_member', 'crew_member__yongcha_pay_group')
            .order_by('-settlement__period_start', 'id')
        )

        household_cache = {}
        daily = {}
        totals = {
            'households': 0,
            'boxes': 0,
            'pay_amount': 0,
            'receive_amount': 0,
        }

        for detail in details:
            delivery_date = detail.settlement.period_start if detail.settlement else None
            date_key = date_iso(delivery_date)
            households = _detail_households(detail, household_cache)
            boxes = int(detail.boxes or 0)
            pay_amount = int(detail.pay_amount or 0)
            receive_amount = int(detail.receive_amount or 0)

            if date_key not in daily:
                daily[date_key] = {
                    'date': date_key,
                    'work_date': date_iso(to_work_date(delivery_date)),
                    'team_names': set(),
                    'households': 0,
                    'boxes': 0,
                    'receive_amount': 0,
                    'pay_amount': 0,
                    'is_yongcha_values': set(),
                    'has_yongcha_pay_group': False,
                    'yongcha_pay_group_names': set(),
                    'detail_ids': [],
                    'settlement_ids': set(),
                    'rounds': {},
                }

            row = daily[date_key]
            round_no = detail.dispatch_upload.round_no if detail.dispatch_upload else None
            round_key = round_no or 0
            if round_key not in row['rounds']:
                row['rounds'][round_key] = {
                    'round_no': round_no,
                    'round_label': f'{round_no}회차' if round_no else '미지정',
                    'team_names': set(),
                    'households': 0,
                    'boxes': 0,
                    'receive_amount': 0,
                    'pay_amount': 0,
                    'is_yongcha_values': set(),
                    'has_yongcha_pay_group': False,
                    'yongcha_pay_group_names': set(),
                    'detail_ids': [],
                    'settlement_ids': set(),
                }
            round_row = row['rounds'][round_key]

            if detail.settlement and detail.settlement.team:
                row['team_names'].add(detail.settlement.team.name)
                round_row['team_names'].add(detail.settlement.team.name)
            if detail.id:
                row['detail_ids'].append(detail.id)
                round_row['detail_ids'].append(detail.id)
            if detail.settlement_id:
                row['settlement_ids'].add(detail.settlement_id)
                round_row['settlement_ids'].add(detail.settlement_id)
            row['households'] += households
            row['boxes'] += boxes
            row['receive_amount'] += receive_amount
            row['pay_amount'] += pay_amount
            row['is_yongcha_values'].add(bool(detail.is_yongcha))
            round_row['households'] += households
            round_row['boxes'] += boxes
            round_row['receive_amount'] += receive_amount
            round_row['pay_amount'] += pay_amount
            round_row['is_yongcha_values'].add(bool(detail.is_yongcha))
            if detail.is_yongcha and detail.crew_member and detail.crew_member.yongcha_pay_group_id:
                row['has_yongcha_pay_group'] = True
                row['yongcha_pay_group_names'].add(detail.crew_member.yongcha_pay_group.name)
                round_row['has_yongcha_pay_group'] = True
                round_row['yongcha_pay_group_names'].add(detail.crew_member.yongcha_pay_group.name)

            totals['households'] += households
            totals['boxes'] += boxes
            totals['pay_amount'] += pay_amount
            totals['receive_amount'] += receive_amount

        rows = []
        for row in daily.values():
            rounds = []
            for round_row in row['rounds'].values():
                rounds.append({
                    'round_no': round_row['round_no'],
                    'round_label': round_row['round_label'],
                    'team_name': ', '.join(sorted(round_row['team_names'])),
                    'households': round_row['households'],
                    'boxes': round_row['boxes'],
                    'receive_amount': round_row['receive_amount'],
                    'pay_amount': round_row['pay_amount'],
                    'is_yongcha': True in round_row['is_yongcha_values'],
                    'is_yongcha_label': _format_yongcha_label(round_row['is_yongcha_values']),
                    'has_yongcha_pay_group': round_row['has_yongcha_pay_group'],
                    'yongcha_pay_group_name': ', '.join(sorted(round_row['yongcha_pay_group_names'])),
                    'detail_ids': list(round_row['detail_ids']),
                    'settlement_ids': sorted(round_row['settlement_ids']),
                })
            rounds.sort(key=lambda item: item['round_no'] or 999)
            rows.append({
                'date': row['date'],
                'work_date': row['work_date'],
                'team_name': ', '.join(sorted(row['team_names'])),
                'households': row['households'],
                'boxes': row['boxes'],
                'receive_amount': row['receive_amount'],
                'pay_amount': row['pay_amount'],
                'is_yongcha': True in row['is_yongcha_values'],
                'is_yongcha_label': _format_yongcha_label(row['is_yongcha_values']),
                'has_yongcha_pay_group': row['has_yongcha_pay_group'],
                'yongcha_pay_group_name': ', '.join(sorted(row['yongcha_pay_group_names'])),
                'detail_ids': list(row['detail_ids']),
                'settlement_ids': sorted(row['settlement_ids']),
                'rounds': rounds,
            })
        rows.sort(key=lambda item: item['date'], reverse=True)

        return Response({
            'crew': {
                'id': crew_member.id,
                'name': crew_member.name,
                'code': crew_member.code,
                'team_name': crew_member.team.name if crew_member.team else '',
                'is_yongcha': crew_member.is_yongcha,
                'two_insurance_percent': float(crew_member.two_insurance_percent or 0),
                'yongcha_pay_group': crew_member.yongcha_pay_group_id,
                'yongcha_pay_group_name': crew_member.yongcha_pay_group.name if crew_member.yongcha_pay_group else '',
            },
            'month': month_value,
            'totals': totals,
            'results': rows,
        })

    def _refresh_settlement_totals(self, settlement_ids):
        for settlement_id in settlement_ids:
            try:
                settlement = Settlement.objects.get(id=settlement_id)
            except Settlement.DoesNotExist:
                continue

            agg = settlement.details.aggregate(
                receive=Sum('receive_amount'),
                pay=Sum('pay_amount'),
                overtime=Sum('overtime_cost'),
                other=Sum('other_cost'),
                profit=Sum('profit'),
            )
            settlement.total_receive = agg['receive'] or 0
            settlement.total_pay = agg['pay'] or 0
            settlement.total_overtime = agg['overtime'] or 0
            settlement.total_other_cost = agg['other'] or 0
            settlement.total_profit = agg['profit'] or 0
            settlement.save(update_fields=[
                'total_receive',
                'total_pay',
                'total_overtime',
                'total_other_cost',
                'total_profit',
                'updated_at',
            ])

    def _refresh_dispatch_upload_summaries(self, upload_ids):
        if not upload_ids:
            return

        from apps.dispatch.models import DispatchUpload

        for dispatch_upload in DispatchUpload.objects.filter(id__in=upload_ids):
            records = dispatch_upload.records.filter(is_valid=True, boxes__gt=0)
            total_boxes = sum(int(record.boxes or 0) for record in records)
            crew_names = {
                str(record.manager_name or '').strip()
                for record in records
                if str(record.manager_name or '').strip()
            }
            regular_count = 0
            yongcha_count = 0

            for name in crew_names:
                record_is_yongcha = records.filter(
                    manager_name=name,
                    is_yongcha=True,
                ).exists()
                crew = None
                if dispatch_upload.team_id:
                    crew = CrewMember.objects.filter(
                        code=name,
                        team=dispatch_upload.team,
                    ).first()
                if not crew:
                    crew = CrewMember.objects.filter(code=name).first()

                is_yongcha = is_effective_yongcha(
                    crew,
                    round_no=dispatch_upload.round_no,
                    explicit_yongcha=record_is_yongcha,
                )
                if is_yongcha:
                    yongcha_count += 1
                else:
                    regular_count += 1

            dispatch_upload.mor_total_boxes = total_boxes
            dispatch_upload.mor_regular_crew_count = regular_count
            dispatch_upload.mor_yongcha_crew_count = yongcha_count
            dispatch_upload.save(update_fields=[
                'mor_total_boxes',
                'mor_regular_crew_count',
                'mor_yongcha_crew_count',
                'updated_at',
            ])

    def _recalculate_member_settlements(self, crew_member):
        details = SettlementDetail.objects.filter(crew_member=crew_member)

        updated = 0
        settlement_ids = set()
        upload_ids = set()

        upload_groups = {}
        fallback_details = []
        for detail in details.select_related('settlement', 'dispatch_upload'):
            if detail.dispatch_upload_id and detail.settlement_id:
                upload_groups[(detail.settlement_id, detail.dispatch_upload_id)] = {
                    'settlement': detail.settlement,
                    'dispatch_upload': detail.dispatch_upload,
                }
            else:
                fallback_details.append(detail)

        for payload in upload_groups.values():
            settlement = payload['settlement']
            dispatch_upload = payload['dispatch_upload']
            if not settlement or not dispatch_upload:
                continue
            matching_records = list(
                self._matching_dispatch_records(crew_member).filter(upload=dispatch_upload, is_valid=True)
            )
            overtime_setting = OvertimeSetting.objects.filter(
                dispatch_upload=dispatch_upload,
                crew_member=crew_member,
                is_overtime=True,
            ).first()
            overtime_cost = Decimal(str(overtime_setting.overtime_cost or 0)) if overtime_setting else Decimal('0')
            receive_price = Decimal(str(dispatch_upload.team.receive_price if dispatch_upload.team else 0))

            existing_count = settlement.details.filter(
                dispatch_upload=dispatch_upload,
                crew_member=crew_member,
            ).count()
            replace_settlement_details_for_crew_upload(
                settlement=settlement,
                crew_member=crew_member,
                dispatch_upload=dispatch_upload,
                records=matching_records,
                receive_price=receive_price,
                overtime_cost=overtime_cost,
            )
            updated += existing_count
            settlement_ids.add(settlement.id)
            upload_ids.add(dispatch_upload.id)

        receive_price = Decimal(str(crew_member.team.receive_price if crew_member.team else 0))
        for detail in fallback_details:
            boxes = Decimal(str(detail.boxes or 0))
            overtime_cost = Decimal(str(detail.overtime_cost or 0))
            other_cost = Decimal(str(detail.other_cost or 0))
            if detail.is_yongcha:
                new_pay = Decimal(str(detail.pay_amount or 0))
            else:
                new_pay = Decimal(str(crew_member.pay_price or 0)) * boxes
            new_receive = receive_price * boxes

            detail.pay_amount = new_pay
            detail.receive_amount = new_receive
            detail.profit = new_receive - new_pay - overtime_cost - other_cost
            detail.save(update_fields=['pay_amount', 'receive_amount', 'profit'])

            settlement_ids.add(detail.settlement_id)
            if detail.dispatch_upload_id:
                upload_ids.add(detail.dispatch_upload_id)
            updated += 1

        self._refresh_settlement_totals(settlement_ids)
        return updated, upload_ids

    def _matching_dispatch_records(self, crew_member):
        from apps.dispatch.models import DispatchRecord

        names = {crew_member.code, crew_member.name}
        names = {name for name in names if name}
        filters = {'manager_name__in': names}
        if crew_member.team_id:
            filters['upload__team'] = crew_member.team
        return DispatchRecord.objects.filter(**filters)

    @action(detail=False, methods=['post'])
    def bulk_yongcha_pay_price(self, request):
        team_id = request.data.get('team_id')
        if not team_id:
            return Response({'detail': 'team_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        company_app = get_company_app_from_request(request)
        team = get_object_or_404(Team, id=team_id, company_app=company_app)
        if not (request.user.is_admin() or request.user.is_staff) and request.user.team_id != team.id:
            return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            yongcha_pay_price = Decimal(str(request.data.get('yongcha_pay_price') or 0))
        except Exception:
            return Response({'detail': '용차 지급단가가 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        apply_history = str(request.data.get('apply_history', True)).lower() not in ('0', 'false', 'no', 'n', '')
        crew_queryset = CrewMember.objects.filter(team=team, is_active=True)
        crew_count = crew_queryset.count()
        if crew_count == 0:
            return Response({
                'detail': '적용할 배송원이 없습니다.',
                'team_id': team.id,
                'team_name': team.name,
                'crew_count': 0,
                'settlement_recalculated_count': 0,
            }, status=status.HTTP_200_OK)

        crew_queryset.update(yongcha_pay_price=yongcha_pay_price)

        recalculated_count = 0
        affected_upload_ids = set()
        if apply_history:
            for crew_member in crew_queryset:
                updated, upload_ids = self._recalculate_member_settlements(crew_member)
                recalculated_count += updated
                affected_upload_ids.update(upload_ids)
            self._refresh_dispatch_upload_summaries(affected_upload_ids)

        return Response({
            'detail': f'{team.name} 팀 용차 지급단가를 {int(yongcha_pay_price)}원으로 반영했습니다.',
            'team_id': team.id,
            'team_name': team.name,
            'crew_count': crew_count,
            'yongcha_pay_price': int(yongcha_pay_price),
            'settlement_recalculated_count': recalculated_count,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-set-yongcha-pay-group')
    def bulk_set_yongcha_pay_group(self, request):
        assignments = request.data.get('assignments') or []
        if not isinstance(assignments, list) or not assignments:
            return Response({'detail': '변경할 배송원을 선택하세요.'}, status=status.HTTP_400_BAD_REQUEST)

        apply_history = str(request.data.get('apply_history', True)).lower() not in ('0', 'false', 'no', 'n')
        company_app = get_company_app_from_request(request)
        normalized = []
        group_ids = set()
        crew_ids = []

        for item in assignments:
            try:
                crew_id = int(item.get('crew_member_id') or item.get('id'))
            except Exception:
                return Response({'detail': '배송원 선택값이 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
            raw_group_id = item.get('yongcha_pay_group')
            group_id = None
            if raw_group_id not in (None, '', 0, '0'):
                try:
                    group_id = int(raw_group_id)
                    group_ids.add(group_id)
                except Exception:
                    return Response({'detail': '용차팀 선택값이 올바르지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
            normalized.append((crew_id, group_id))
            crew_ids.append(crew_id)

        pay_groups = {
            group.id: group
            for group in YongchaPayGroup.objects.filter(
                id__in=group_ids,
                company_app=company_app,
                is_active=True,
            )
        }
        if len(pay_groups) != len(group_ids):
            return Response({'detail': '현재 회사에서 사용할 수 없는 용차팀이 포함되어 있습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        crew_queryset = CrewMember.objects.filter(
            id__in=crew_ids,
            is_active=True,
            is_yongcha=True,
            team__company_app=company_app,
        ).select_related('team')

        crews = {crew.id: crew for crew in crew_queryset}
        if len(crews) != len(set(crew_ids)):
            return Response({'detail': '용차 관리 대상이 아닌 배송원이 포함되어 있습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if not (request.user.is_admin() or request.user.is_staff):
            if not request.user.team_id or any(crew.team_id != request.user.team_id for crew in crews.values()):
                return Response({'detail': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

        updated_count = 0
        recalculated_count = 0
        affected_upload_ids = set()
        with transaction.atomic():
            for crew_id, group_id in normalized:
                crew = crews[crew_id]
                if crew.yongcha_pay_group_id == group_id:
                    continue
                crew.yongcha_pay_group_id = group_id
                crew.save(update_fields=['yongcha_pay_group', 'updated_at'])
                updated_count += 1

                if apply_history:
                    updated, detail_upload_ids = self._recalculate_member_settlements(crew)
                    recalculated_count += updated
                    affected_upload_ids.update(detail_upload_ids)

            if apply_history:
                self._refresh_dispatch_upload_summaries(affected_upload_ids)

        return Response({
            'detail': f'{updated_count}명 용차팀을 변경했습니다.',
            'updated_count': updated_count,
            'settlement_recalculated_count': recalculated_count,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_regular_fixed_pay(self, request, pk=None):
        crew_member = self.get_object()
        apply_history = str(request.data.get('apply_history', True)).lower() not in ('0', 'false', 'no', 'n')
        update_fields = []

        try:
            for round_no in (1, 2, 3):
                key = f'round_{round_no}_base_pay'
                model_field = f'regular_round_{round_no}_base_pay'
                if key in request.data:
                    amount = Decimal(str(request.data.get(key) or 0))
                else:
                    amount = Decimal(str(request.data.get(model_field) or 0))
                if amount < 0:
                    raise ValueError
                setattr(crew_member, model_field, amount)
                update_fields.append(model_field)
        except Exception:
            return Response({'detail': '기본급은 0 이상의 숫자여야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        update_fields.append('updated_at')
        crew_member.save(update_fields=update_fields)

        detail_count = 0
        dispatch_count = 0
        recalculated_count = 0
        affected_upload_ids = set()
        if apply_history:
            detail_count = SettlementDetail.objects.filter(crew_member=crew_member).count()
            dispatch_qs = self._matching_dispatch_records(crew_member)
            affected_upload_ids.update(dispatch_qs.values_list('upload_id', flat=True).distinct())
            dispatch_count = dispatch_qs.count()
            recalculated_count, detail_upload_ids = self._recalculate_member_settlements(crew_member)
            affected_upload_ids.update(detail_upload_ids)
            self._refresh_dispatch_upload_summaries(affected_upload_ids)

        serializer = self.get_serializer(crew_member)
        data = serializer.data
        data['history_marked_count'] = detail_count
        data['dispatch_marked_count'] = dispatch_count
        data['settlement_recalculated_count'] = recalculated_count
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_yongcha_pay_group(self, request, pk=None):
        crew_member = self.get_object()
        apply_history = str(request.data.get('apply_history', True)).lower() not in ('0', 'false', 'no', 'n')
        group_id = request.data.get('yongcha_pay_group')
        raw_rounds = request.data.get('round_yongcha_numbers', None)

        pay_group = None
        if group_id not in (None, '', 0, '0'):
            pay_group = get_object_or_404(
                YongchaPayGroup,
                id=group_id,
                company_app=get_company_app_from_request(request),
                is_active=True,
            )

        selected_rounds = None
        if raw_rounds is not None:
            try:
                if isinstance(raw_rounds, str):
                    raw_rounds = [value for value in raw_rounds.split(',') if value.strip()]
                selected_rounds = {int(value) for value in raw_rounds}
            except Exception:
                return Response({'detail': '용차 전환 회차는 1, 2, 3 중에서 선택해야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            if any(round_no not in (1, 2, 3) for round_no in selected_rounds):
                return Response({'detail': '용차 전환 회차는 1, 2, 3 중에서 선택해야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        crew_member.yongcha_pay_group = pay_group
        update_fields = ['yongcha_pay_group', 'updated_at']
        if selected_rounds is not None and not crew_member.is_yongcha:
            for round_no in (1, 2, 3):
                field_name = f'round_{round_no}_is_yongcha'
                setattr(crew_member, field_name, round_no in selected_rounds)
                update_fields.append(field_name)
        crew_member.save(update_fields=update_fields)

        detail_count = 0
        dispatch_count = 0
        recalculated_count = 0
        affected_upload_ids = set()
        if apply_history:
            detail_count = SettlementDetail.objects.filter(crew_member=crew_member).count()
            dispatch_qs = self._matching_dispatch_records(crew_member)
            affected_upload_ids.update(dispatch_qs.values_list('upload_id', flat=True).distinct())
            dispatch_count = dispatch_qs.count()
            recalculated_count, detail_upload_ids = self._recalculate_member_settlements(crew_member)
            affected_upload_ids.update(detail_upload_ids)
            self._refresh_dispatch_upload_summaries(affected_upload_ids)

        serializer = self.get_serializer(crew_member)
        data = serializer.data
        data['history_marked_count'] = detail_count
        data['dispatch_marked_count'] = dispatch_count
        data['settlement_recalculated_count'] = recalculated_count
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def convert_to_regular(self, request, pk=None):
        crew_member = self.get_object()
        apply_history = request.data.get('apply_history', False)
        apply_history = str(apply_history).lower() not in ('0', 'false', 'no', 'n', '')

        detail_count = 0
        dispatch_count = 0
        recalculated_count = 0
        affected_upload_ids = set()

        with transaction.atomic():
            crew_member.is_yongcha = False
            crew_member.is_new = False
            crew_member.round_1_is_yongcha = False
            crew_member.round_2_is_yongcha = False
            crew_member.round_3_is_yongcha = False
            if 'pay_price' in request.data:
                crew_member.pay_price = Decimal(str(request.data.get('pay_price') or 0))
            crew_member.save(update_fields=[
                'is_yongcha', 'is_new', 'pay_price',
                'round_1_is_yongcha', 'round_2_is_yongcha', 'round_3_is_yongcha',
                'updated_at',
            ])

            if apply_history:
                detail_count = SettlementDetail.objects.filter(crew_member=crew_member).count()
                dispatch_qs = self._matching_dispatch_records(crew_member)
                affected_upload_ids.update(
                    dispatch_qs.values_list('upload_id', flat=True).distinct()
                )
                dispatch_count = dispatch_qs.count()
                recalculated_count, detail_upload_ids = self._recalculate_member_settlements(crew_member)
                affected_upload_ids.update(detail_upload_ids)
                self._refresh_dispatch_upload_summaries(affected_upload_ids)

        serializer = self.get_serializer(crew_member)
        data = serializer.data
        data['history_marked_count'] = detail_count
        data['dispatch_marked_count'] = dispatch_count
        data['settlement_recalculated_count'] = recalculated_count
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def convert_to_yongcha(self, request, pk=None):
        crew_member = self.get_object()
        apply_history = request.data.get('apply_history', True)
        apply_history = str(apply_history).lower() not in ('0', 'false', 'no', 'n')

        crew_member.is_yongcha = True
        crew_member.is_new = False
        crew_member.round_1_is_yongcha = False
        crew_member.round_2_is_yongcha = False
        crew_member.round_3_is_yongcha = False
        general_payload_value = request.data.get('yongcha_pay_price')
        if general_payload_value is not None:
            crew_member.yongcha_pay_price = Decimal(str(general_payload_value or 3000))
        elif crew_member.team_id and crew_member.team:
            crew_member.yongcha_pay_price = Decimal(str(crew_member.team.yongcha_pay_price or 3000))

        personal_fields = []
        for round_no in (1, 2, 3):
            field_name = f'personal_round_{round_no}_yongcha_pay_price'
            request_key = field_name
            if request_key in request.data:
                setattr(crew_member, field_name, Decimal(str(request.data.get(request_key) or 0)))
                personal_fields.append(field_name)
            elif general_payload_value is not None:
                setattr(crew_member, field_name, Decimal(str(general_payload_value or 0)))
                personal_fields.append(field_name)
        crew_member.save(update_fields=[
            'is_yongcha', 'is_new', 'yongcha_pay_price',
            'round_1_is_yongcha', 'round_2_is_yongcha', 'round_3_is_yongcha',
            *personal_fields,
            'updated_at',
        ])

        detail_count = 0
        dispatch_count = 0
        recalculated_count = 0
        affected_upload_ids = set()
        if apply_history:
            detail_count = SettlementDetail.objects.filter(crew_member=crew_member).count()
            dispatch_qs = self._matching_dispatch_records(crew_member)
            affected_upload_ids.update(dispatch_qs.values_list('upload_id', flat=True).distinct())
            dispatch_count = dispatch_qs.count()
            recalculated_count, detail_upload_ids = self._recalculate_member_settlements(crew_member)
            affected_upload_ids.update(detail_upload_ids)
            self._refresh_dispatch_upload_summaries(affected_upload_ids)

        serializer = self.get_serializer(crew_member)
        data = serializer.data
        data['history_marked_count'] = detail_count
        data['dispatch_marked_count'] = dispatch_count
        data['settlement_recalculated_count'] = recalculated_count
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_round_yongcha(self, request, pk=None):
        crew_member = self.get_object()
        round_no = int(request.data.get('round_no') or 0)
        if round_no not in (1, 2, 3):
            return Response({'detail': 'round_no must be 1, 2, or 3'}, status=status.HTTP_400_BAD_REQUEST)

        is_yongcha = str(request.data.get('is_yongcha', True)).lower() not in ('0', 'false', 'no', 'n')
        apply_history = str(request.data.get('apply_history', True)).lower() not in ('0', 'false', 'no', 'n')
        yongcha_pay_price = request.data.get('round_pay_price', request.data.get('yongcha_pay_price'))
        field_name = f'round_{round_no}_is_yongcha'
        rate_field_name = f'personal_round_{round_no}_yongcha_pay_price'

        setattr(crew_member, field_name, is_yongcha)
        crew_member.is_new = False
        if yongcha_pay_price is not None:
            setattr(crew_member, rate_field_name, Decimal(str(yongcha_pay_price or 0)))

        update_fields = [field_name, 'is_new', 'updated_at']
        if yongcha_pay_price is not None:
            update_fields.append(rate_field_name)
        crew_member.save(update_fields=update_fields)

        detail_count = 0
        dispatch_count = 0
        recalculated_count = 0
        affected_upload_ids = set()
        if apply_history:
            matching_details = SettlementDetail.objects.filter(
                crew_member=crew_member,
                dispatch_upload__round_no=round_no,
            )
            detail_count = matching_details.count()
            matching_dispatch = self._matching_dispatch_records(crew_member).filter(upload__round_no=round_no)
            dispatch_count = matching_dispatch.count()
            affected_upload_ids.update(matching_dispatch.values_list('upload_id', flat=True).distinct())
            recalculated_count, detail_upload_ids = self._recalculate_member_settlements(crew_member)
            affected_upload_ids.update(detail_upload_ids)
            self._refresh_dispatch_upload_summaries(affected_upload_ids)

        serializer = self.get_serializer(crew_member)
        data = serializer.data
        data['history_marked_count'] = detail_count
        data['dispatch_marked_count'] = dispatch_count
        data['settlement_recalculated_count'] = recalculated_count
        data['round_no'] = round_no
        data['round_is_yongcha'] = is_yongcha
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def recalc_settlements(self, request, pk=None):
        crew_member = self.get_object()
        updated, _ = self._recalculate_member_settlements(crew_member)
        return Response({'detail': f'{updated}건 정산 재계산 완료'})

    @action(detail=True, methods=['post'])
    def mark_registered(self, request, pk=None):
        crew_member = self.get_object()
        crew_member.is_new = False
        crew_member.is_yongcha = False
        crew_member.save(update_fields=['is_new', 'is_yongcha'])

        logger.info(
            '배송원 신규 상태 변경: %s (변경자: %s)',
            crew_member.code,
            request.user.username,
        )

        serializer = self.get_serializer(crew_member)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OvertimeSettingViewSet(viewsets.ModelViewSet):
    serializer_class = OvertimeSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        upload_id = self.request.query_params.get('upload_id')

        if upload_id:
            from apps.dispatch.models import DispatchUpload

            dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)

            user = self.request.user
            if not user.is_admin() and dispatch_upload.team != user.team:
                return OvertimeSetting.objects.none()

            return dispatch_upload.overtime_settings.all()

        return OvertimeSetting.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload_id = request.data.get('dispatch_upload')
        from apps.dispatch.models import DispatchUpload

        dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)
        if not request.user.is_admin() and dispatch_upload.team != request.user.team:
            return Response(
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_create(serializer)

        logger.info(
            '연장근무 설정 생성: %s (생성자: %s)',
            serializer.instance.id,
            request.user.username,
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        logger.info(
            '연장근무 설정 수정: %s (수정자: %s)',
            serializer.instance.id,
            self.request.user.username,
        )
