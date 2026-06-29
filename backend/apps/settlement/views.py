from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, date, timedelta
import logging

from apps.dispatch.models import DispatchUpload, DispatchRecord
from apps.dispatch.date_utils import date_iso
from apps.dispatch.settlement_services import build_region_allocations
from apps.accounts.shipper_utils import normalize_shipper_code
from apps.common.company_scope import get_company_app_from_request
from apps.region.models import Region, RegionPrice
from apps.accounts.models import Team
from .models import Settlement, SettlementDetail
from .serializers import (
    SettlementSerializer, SettlementCreateSerializer,
    SettlementDetailSerializer, SettlementConfirmSerializer
)

logger = logging.getLogger(__name__)


class SettlementViewSet(viewsets.ModelViewSet):
    """Settlement management endpoints."""
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SettlementCreateSerializer
        return SettlementSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        include_details_param = str(self.request.query_params.get('include_details') or '').lower()
        if self.action == 'list' and include_details_param not in ('1', 'true', 'yes'):
            context['include_details'] = False
        return context

    def get_queryset(self):
        user = self.request.user
        company_app = get_company_app_from_request(self.request)
        if user.is_admin():
            queryset = Settlement.objects.filter(team__company_app=company_app)
        elif user.team:
            queryset = Settlement.objects.filter(team=user.team)
        else:
            return Settlement.objects.none()

        queryset = queryset.select_related('team', 'confirmed_by')
        if self.action == 'list':
            queryset = self._with_detail_totals(queryset)
        return queryset

    def _with_detail_totals(self, queryset):
        return queryset.annotate(
            regular_total_receive_agg=Sum('details__receive_amount', filter=Q(details__is_yongcha=False)),
            regular_total_pay_agg=Sum('details__pay_amount', filter=Q(details__is_yongcha=False)),
            regular_total_overtime_agg=Sum('details__overtime_cost', filter=Q(details__is_yongcha=False)),
            regular_total_other_cost_agg=Sum('details__other_cost', filter=Q(details__is_yongcha=False)),
            regular_total_profit_agg=Sum('details__profit', filter=Q(details__is_yongcha=False)),
            regular_total_boxes_agg=Sum('details__boxes', filter=Q(details__is_yongcha=False)),
            yongcha_total_receive_agg=Sum('details__receive_amount', filter=Q(details__is_yongcha=True)),
            yongcha_total_pay_agg=Sum('details__pay_amount', filter=Q(details__is_yongcha=True)),
            yongcha_total_overtime_agg=Sum('details__overtime_cost', filter=Q(details__is_yongcha=True)),
            yongcha_total_other_cost_agg=Sum('details__other_cost', filter=Q(details__is_yongcha=True)),
            yongcha_total_profit_agg=Sum('details__profit', filter=Q(details__is_yongcha=True)),
            yongcha_total_boxes_agg=Sum('details__boxes', filter=Q(details__is_yongcha=True)),
        )

    def _parse_month(self, value):
        if not value:
            today = timezone.now().date()
            return today.year, today.month
        try:
            parsed = datetime.strptime(value, '%Y-%m')
            return parsed.year, parsed.month
        except (TypeError, ValueError):
            today = timezone.now().date()
            return today.year, today.month

    def _month_bounds(self, value):
        year, month = self._parse_month(value)
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return start, end

    def _serialize_detail_groups(self, settlement):
        details = settlement.details.select_related('crew_member', 'dispatch_upload').all()
        groups = {}
        household_allocations = {}

        def resolve_households(detail):
            if not detail.dispatch_upload_id or not detail.crew_member_id:
                return 0

            cache_key = (detail.dispatch_upload_id, detail.crew_member_id)
            if cache_key not in household_allocations:
                names = {
                    str(detail.crew_member.code or '').strip(),
                    str(detail.crew_member.name or '').strip(),
                }
                names = [name for name in names if name]
                records = DispatchRecord.objects.filter(
                    upload_id=detail.dispatch_upload_id,
                    is_valid=True,
                    manager_name__in=names,
                )
                household_allocations[cache_key] = build_region_allocations(records)

            return int(
                household_allocations[cache_key].get(detail.region, {}).get('households', 0) or 0
            )

        for detail in details:
            upload_id = detail.dispatch_upload_id or 'unknown'
            if upload_id not in groups:
                shipper_code = (
                    getattr(detail.dispatch_upload, 'shipper_code', None)
                    or getattr(detail.settlement, 'shipper_code', None)
                    or getattr(detail, 'shipper_code', None)
                    or 'kurly'
                )
                groups[upload_id] = {
                    'uploadId': upload_id,
                    'filename': getattr(detail.dispatch_upload, 'original_filename', '') or '?????',
                    'uploadTime': getattr(detail.dispatch_upload, 'upload_date', None),
                    'roundNo': getattr(detail.dispatch_upload, 'round_no', None),
                    'shipperCode': shipper_code,
                    'crewMap': {},
                }

            group = groups[upload_id]
            crew_name = detail.crew_member.name if detail.crew_member else '???'
            crew_code = detail.crew_member.code if detail.crew_member else ''
            crew_key = detail.crew_member_id or crew_code or crew_name or 'unknown'

            if crew_key not in group['crewMap']:
                group['crewMap'][crew_key] = {
                    'name': crew_name,
                    'crewMemberId': detail.crew_member_id,
                    'isYongcha': bool(detail.is_yongcha),
                    'payBasis': 'households' if detail.is_yongcha else 'boxes',
                    'regions': set(),
                    'totalBoxes': 0,
                    'totalHouseholds': 0,
                    'totalReceive': 0,
                    'totalPay': 0,
                    'totalOvertime': 0,
                    'totalProfit': 0,
                    'detailIds': [],
                }

            crew = group['crewMap'][crew_key]
            households = resolve_households(detail)
            if detail.region:
                crew['regions'].add(detail.region)
            crew['isYongcha'] = crew['isYongcha'] or bool(detail.is_yongcha)
            crew['payBasis'] = 'households' if crew['isYongcha'] else 'boxes'
            crew['totalBoxes'] += int(detail.boxes or 0)
            crew['totalHouseholds'] += households
            crew['totalReceive'] += int(detail.receive_amount or 0)
            crew['totalPay'] += int(detail.pay_amount or 0)
            crew['totalOvertime'] += int(detail.overtime_cost or 0)
            crew['totalProfit'] += int(detail.profit or 0)
            crew['detailIds'].append(detail.id)

        serialized = []
        for group in sorted(
            groups.values(),
            key=lambda item: (item.get('roundNo') or 99, item['uploadTime'] or datetime.min),
        ):
            crew_list = [
                {
                    **crew,
                    'regions': sorted(crew['regions']),
                }
                for crew in group['crewMap'].values()
            ]
            regular = sorted(
                [crew for crew in crew_list if not crew['isYongcha']],
                key=lambda item: item['totalReceive'],
                reverse=True,
            )
            yongcha = sorted(
                [crew for crew in crew_list if crew['isYongcha']],
                key=lambda item: item['totalReceive'],
                reverse=True,
            )
            serialized.append({
                'uploadId': group['uploadId'],
                'filename': group['filename'],
                'uploadTime': group['uploadTime'],
                'roundNo': group.get('roundNo'),
                'shipperCode': group.get('shipperCode') or 'kurly',
                'regularCrewList': regular,
                'yongchaCrewList': yongcha,
                'regularTotalReceive': sum(item['totalReceive'] for item in regular),
                'regularTotalPay': sum(item['totalPay'] for item in regular),
                'regularTotalProfit': sum(item['totalProfit'] for item in regular),
                'yongchaTotalReceive': sum(item['totalReceive'] for item in yongcha),
                'yongchaTotalPay': sum(item['totalPay'] for item in yongcha),
                'yongchaTotalProfit': sum(item['totalProfit'] for item in yongcha),
            })
        return serialized

    def create(self, request, *args, **kwargs):
        """Create a settlement."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = serializer.validated_data.get('team')
        if not team:
            return Response(
                {'team': ['????좏깮?댁＜?몄슂.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        company_app = get_company_app_from_request(request)
        if request.user.is_admin() and team.company_app != company_app:
            return Response(
                {'team': ['현재 회사 범위와 다른 팀입니다.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.is_team_leader() and request.user.team != team:
            return Response(
                {'team': ['?먯떊????먮쭔 ?뺤궛?????덉뒿?덈떎.']},
                status=status.HTTP_403_FORBIDDEN
            )

        settlement = Settlement.objects.create(**serializer.validated_data)
        response_serializer = SettlementSerializer(settlement)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a settlement draft from one dispatch upload."""
        upload_id = request.data.get('upload_id')
        if not upload_id:
            return Response(
                {'detail': 'upload_id媛 ?꾩슂?⑸땲??'},
                status=status.HTTP_400_BAD_REQUEST
            )

        company_app = get_company_app_from_request(request)
        if request.user.is_admin():
            dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id, team__company_app=company_app)
        else:
            dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)

        # 沅뚰븳 ?뺤씤
        if not request.user.is_admin() and dispatch_upload.team != request.user.team:
            return Response(
                {'detail': '沅뚰븳???놁뒿?덈떎.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # ?뺤젙??諛곗감留??뺤궛 媛??
        if dispatch_upload.status != 'CONFIRMED':
            return Response(
                {'detail': '?뺤젙??諛곗감 ?곗씠?곕쭔 ?뺤궛?????덉뒿?덈떎.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        team = dispatch_upload.team
        shipper_code = normalize_shipper_code(getattr(dispatch_upload, 'shipper_code', None))
        today = timezone.now().date()
        base_date = dispatch_upload.dispatch_date or today

        # ?뺤궛 ?앹꽦
        settlement, created = Settlement.objects.get_or_create(
            team=team,
            shipper_code=shipper_code,
            period_start=base_date,
            period_end=base_date,
            defaults={
                'status': 'DRAFT',
                'note': f'諛곗감 ?낅줈??#{upload_id} 湲곕컲 ?먮룞 ?뺤궛',
            }
        )

        if not created:
            # 湲곗〈 ?뺤궛???곸꽭 ??젣 ???ъ깮??
            settlement.details.all().delete()

        total_receive = Decimal('0')
        total_pay = Decimal('0')
        total_overtime = Decimal('0')
        details_created = 0
        missing_prices = []

        records = dispatch_upload.records.filter(is_valid=True)
        for record in records:
            if not record.detail_region or record.boxes <= 0:
                continue

            # 沅뚯뿭 議고쉶
            try:
                region = Region.objects.get(code=record.detail_region)
            except Region.DoesNotExist:
                missing_prices.append(record.detail_region)
                continue

            # 諛곗넚???留ㅽ븨 (?쒓뎅????肄붾뱶)
            delivery_type_map = {
                '?뱀씪': 'SAME_DAY',
                '?듭씪': 'NEXT_DAY',
                'SAME_DAY': 'SAME_DAY',
                'NEXT_DAY': 'NEXT_DAY',
            }
            dt_code = delivery_type_map.get(record.delivery_type, 'SAME_DAY')

            # ?④? 議고쉶 (媛??理쒓렐 ?좏슚???④?)
            price = RegionPrice.objects.filter(
                region=region,
                delivery_type=dt_code,
                start_date__lte=today,
            ).filter(
                # end_date媛 null?닿굅???ㅻ뒛 ?댄썑??寃?
                **{}
            ).order_by('-start_date').first()

            if not price:
                # end_date 議곌굔 ?놁씠 媛??理쒓렐 ?④?
                price = RegionPrice.objects.filter(
                    region=region,
                    delivery_type=dt_code,
                ).order_by('-start_date').first()

            if not price:
                missing_prices.append(record.detail_region)
                continue

            receive_amount = price.receive_price * record.boxes
            pay_amount = price.pay_price * record.boxes
            overtime_cost = Decimal('0')

            if record.is_overtime and team:
                overtime_cost = team.default_overtime_cost

            profit = receive_amount - pay_amount - overtime_cost

            SettlementDetail.objects.create(
                settlement=settlement,
                crew_member=None,
                shipper_code=shipper_code,
                region=record.detail_region,
                delivery_type=dt_code,
                boxes=record.boxes,
                receive_amount=receive_amount,
                pay_amount=pay_amount,
                overtime_cost=overtime_cost,
                profit=profit,
            )

            total_receive += receive_amount
            total_pay += pay_amount
            total_overtime += overtime_cost
            details_created += 1

        # ?⑷퀎 ?낅뜲?댄듃
        settlement.total_receive = total_receive
        settlement.total_pay = total_pay
        settlement.total_overtime = total_overtime
        settlement.total_profit = total_receive - total_pay - total_overtime
        settlement.save()

        logger.info(
            f'?뺤궛 ?먮룞 ?앹꽦: settlement #{settlement.id} ??'
            f'{details_created}嫄? ?섏떊??{total_receive}, 吏湲됱븸 {total_pay}'
        )

        serializer = SettlementSerializer(settlement)
        return Response({
            'settlement': serializer.data,
            'details_created': details_created,
            'missing_prices': list(set(missing_prices)),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a settlement."""
        settlement = self.get_object()

        if settlement.status in ['CONFIRMED', 'PAID']:
            return Response(
                {'detail': '?대? ?뺤젙???뺤궛?낅땲??'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not settlement.details.exists():
            return Response(
                {'detail': '?뺤궛 ?곸꽭 ?뺣낫媛 ?놁뒿?덈떎.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        details = settlement.details.all()
        total_receive = details.aggregate(Sum('receive_amount'))['receive_amount__sum'] or 0
        total_pay = details.aggregate(Sum('pay_amount'))['pay_amount__sum'] or 0
        total_overtime = details.aggregate(Sum('overtime_cost'))['overtime_cost__sum'] or 0

        settlement.total_receive = total_receive
        settlement.total_pay = total_pay
        settlement.total_overtime = total_overtime
        settlement.total_profit = total_receive - total_pay - total_overtime
        settlement.status = 'CONFIRMED'
        settlement.confirmed_by = request.user
        settlement.confirmed_at = timezone.now()
        settlement.save()

        logger.info(f'?뺤궛 ?뺤젙: {settlement.id} (?뺤젙?? {request.user.username})')

        serializer = SettlementSerializer(settlement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark a confirmed settlement as paid."""
        settlement = self.get_object()

        if settlement.status != 'CONFIRMED':
            return Response(
                {'detail': '?뺤젙???뺤궛留?吏湲??꾨즺濡??쒖떆?????덉뒿?덈떎.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        settlement.status = 'PAID'
        settlement.save()

        serializer = SettlementSerializer(settlement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def recalc(self, request, pk=None):
        """Recalculate settlement totals."""
        settlement = self.get_object()
        details = settlement.details.all()
        total_receive = details.aggregate(Sum('receive_amount'))['receive_amount__sum'] or 0
        total_pay = details.aggregate(Sum('pay_amount'))['pay_amount__sum'] or 0
        total_overtime = details.aggregate(Sum('overtime_cost'))['overtime_cost__sum'] or 0
        total_other = details.aggregate(Sum('other_cost'))['other_cost__sum'] or 0
        settlement.total_receive = total_receive
        settlement.total_pay = total_pay
        settlement.total_overtime = total_overtime
        settlement.total_other_cost = total_other
        settlement.total_profit = total_receive - total_pay - total_overtime - total_other
        settlement.save()
        serializer = SettlementSerializer(settlement)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def web_overview(self, request):
        team_name = request.query_params.get('team_name')
        month = request.query_params.get('month')
        month_start, month_end = self._month_bounds(month)

        queryset = self._with_detail_totals(self.get_queryset().filter(
            period_start__gte=month_start,
            period_start__lte=month_end,
        ))
        if team_name:
            queryset = queryset.filter(team__name=team_name)
        shipper_code = str(request.query_params.get('shipper_code') or '').strip().lower()
        if shipper_code:
            queryset = queryset.filter(shipper_code=normalize_shipper_code(shipper_code))

        settlements = list(queryset.order_by('-period_start', '-id'))
        serialized = SettlementSerializer(
            settlements,
            many=True,
            context={'request': request, 'include_details': False},
        ).data

        settlements_by_date = {}
        for row in serialized:
            settlements_by_date.setdefault(row['period_start'], []).append(row)

        first = month_start
        start_offset = (first.weekday()) % 7
        total_cells = ((start_offset + month_end.day + 6) // 7) * 7
        cells = []
        for index in range(total_cells):
            cell_date = first - timedelta(days=start_offset) + timedelta(days=index)
            date_key = cell_date.isoformat()
            day_settlements = settlements_by_date.get(date_key, [])
            cells.append({
                'key': f'{date_key}-{index}',
                'date': date_key,
                'day': cell_date.day,
                'inMonth': cell_date.month == month_start.month,
                'settlementCount': len(day_settlements),
                'teamNames': sorted({item.get('team_name') for item in day_settlements if item.get('team_name')}),
                'totalProfit': sum(int(item.get('total_profit') or 0) for item in day_settlements),
            })

        return Response({
            'settlements': serialized,
            'settlements_by_date': settlements_by_date,
            'calendar_cells': cells,
            'initial_selected_date': date_iso(settlements[0].period_start) if settlements else None,
        })

    @action(detail=True, methods=['get'], url_path='web-detail-groups')
    def web_detail_groups(self, request, pk=None):
        settlement = self.get_object()
        return Response({'groups': self._serialize_detail_groups(settlement)})

    @action(detail=False, methods=['get'], url_path='web-crew-history')
    def web_crew_history(self, request):
        crew_member_id = request.query_params.get('crew_member_id')
        crew_name = (request.query_params.get('crew_name') or '').strip()
        month = request.query_params.get('month')

        details = SettlementDetail.objects.filter(
            settlement__in=self.get_queryset(),
        ).select_related('settlement', 'dispatch_upload')

        if crew_member_id:
            details = details.filter(crew_member_id=crew_member_id)
        elif crew_name:
            details = details.filter(
                Q(crew_member__name=crew_name) |
                Q(crew_member__code=crew_name)
            )
        else:
            return Response({'rows': [], 'totals': {'boxes': 0, 'households': 0, 'pay': 0, 'overtime': 0}})

        if month:
            month_start, month_end = self._month_bounds(month)
            details = details.filter(
                settlement__period_start__gte=month_start,
                settlement__period_start__lte=month_end,
            )

        rows_by_upload = {}
        household_totals_by_upload = {}
        for detail in details.order_by('dispatch_upload_id', 'settlement__period_start', 'id'):
            upload_id = detail.dispatch_upload_id or f"detail-{detail.id}"
            if upload_id not in rows_by_upload:
                if detail.dispatch_upload_id:
                    if detail.crew_member_id:
                        names = {
                            str(detail.crew_member.code or '').strip(),
                            str(detail.crew_member.name or '').strip(),
                        }
                    else:
                        names = {crew_name}
                    names = [name for name in names if name]
                    household_totals_by_upload[upload_id] = sum(
                        int(record.households or 0)
                        for record in DispatchRecord.objects.filter(
                            upload_id=detail.dispatch_upload_id,
                            is_valid=True,
                            manager_name__in=names,
                        )
                    )
                else:
                    household_totals_by_upload[upload_id] = 0
                rows_by_upload[upload_id] = {
                    'date': date_iso(
                        getattr(detail.dispatch_upload, 'dispatch_date', None)
                        or detail.settlement.period_start
                    ) or '-',
                    'regions': set(),
                    'boxes': 0,
                    'households': household_totals_by_upload[upload_id],
                    'pay': 0,
                    'overtime': 0,
                }
            row = rows_by_upload[upload_id]
            if detail.region:
                row['regions'].add(detail.region)
            row['boxes'] += int(detail.boxes or 0)
            row['pay'] += int(detail.pay_amount or 0)
            row['overtime'] += int(detail.overtime_cost or 0)

        rows = [{
            **value,
            'regions': ', '.join(sorted(value['regions'])),
        } for value in rows_by_upload.values()]
        rows.sort(key=lambda item: item['date'])
        totals = {
            'boxes': sum(item['boxes'] for item in rows),
            'households': sum(item['households'] for item in rows),
            'pay': sum(item['pay'] for item in rows),
            'overtime': sum(item['overtime'] for item in rows),
        }
        return Response({'rows': rows, 'totals': totals})

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """?뺤궛???대낫?닿린 (CSV)"""
        settlement = self.get_object()

        if not request.user.is_admin() and settlement.team != request.user.team:
            return Response(
                {'detail': '沅뚰븳???놁뒿?덈떎.'},
                status=status.HTTP_403_FORBIDDEN
            )

        import csv
        from io import StringIO
        from django.http import HttpResponse

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'Settlement Period', f'{date_iso(settlement.period_start)} ~ {date_iso(settlement.period_end)}',
            'Team', settlement.team.name if settlement.team else '',
            'Status', settlement.get_status_display()
        ])
        writer.writerow([])
        writer.writerow([
            'Crew Code', 'Crew Name', 'Region', 'Delivery Type',
            'Boxes', 'Receive Amount', 'Pay Amount', 'Overtime Cost', 'Profit'
        ])

        for detail in settlement.details.all():
            writer.writerow([
                detail.crew_member.code if detail.crew_member else '',
                detail.crew_member.name if detail.crew_member else '',
                detail.region,
                detail.get_delivery_type_display(),
                detail.boxes,
                detail.receive_amount,
                detail.pay_amount,
                detail.overtime_cost,
                detail.profit
            ])

        writer.writerow([])
        writer.writerow([
            '?⑷퀎', '', '', '', '',
            settlement.total_receive, settlement.total_pay,
            settlement.total_overtime, settlement.total_profit
        ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=settlement_{settlement.id}.csv'
        return response


class SettlementDetailViewSet(viewsets.ModelViewSet):
    """Settlement detail endpoints."""
    serializer_class = SettlementDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        settlement_id = self.request.query_params.get('settlement_id')
        user = self.request.user

        # PATCH/DELETE ??媛쒕퀎 ?묎렐 ???꾩껜?먯꽌 李얘린
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            if user.is_admin() or user.is_staff:
                return SettlementDetail.objects.all()
            return SettlementDetail.objects.filter(settlement__team=user.team)

        if settlement_id:
            settlement = get_object_or_404(Settlement, id=settlement_id)
            if not user.is_admin() and settlement.team != user.team:
                return SettlementDetail.objects.none()
            return settlement.details.all()
        return SettlementDetail.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        settlement_id = request.data.get('settlement')
        settlement = get_object_or_404(Settlement, id=settlement_id)

        if not request.user.is_admin() and settlement.team != request.user.team:
            return Response(
                {'detail': '沅뚰븳???놁뒿?덈떎.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if settlement.status in ['CONFIRMED', 'PAID']:
            return Response(
                {'detail': '?뺤젙???뺤궛? ?곸꽭 ?뺣낫瑜?異붽??????놁뒿?덈떎.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        profit = (
            serializer.validated_data.get('receive_amount', 0) -
            serializer.validated_data.get('pay_amount', 0) -
            serializer.validated_data.get('overtime_cost', 0) -
            serializer.validated_data.get('other_cost', 0)
        )
        serializer.validated_data['profit'] = profit
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        from decimal import Decimal
        obj = self.get_object()
        settlement = obj.settlement
        new_boxes = serializer.validated_data.get('boxes', obj.boxes)

        # 諛뺤뒪??蹂寃???pay/receive ?먮룞 ?ш퀎??(?④? ?좎?)
        if new_boxes != obj.boxes and 'receive_amount' not in serializer.validated_data:
            team = obj.settlement.team if obj.settlement else None
            receive_price = team.receive_price if team else Decimal('0')
            serializer.validated_data['receive_amount'] = receive_price * Decimal(str(new_boxes))
        if new_boxes != obj.boxes and 'pay_amount' not in serializer.validated_data:
            crew = obj.crew_member
            if not obj.is_yongcha:
                pay_price = crew.pay_price if crew else Decimal('0')
                serializer.validated_data['pay_amount'] = pay_price * Decimal(str(new_boxes))

        profit = (
            serializer.validated_data.get('receive_amount', obj.receive_amount) -
            serializer.validated_data.get('pay_amount', obj.pay_amount) -
            serializer.validated_data.get('overtime_cost', obj.overtime_cost) -
            serializer.validated_data.get('other_cost', obj.other_cost)
        )
        serializer.validated_data['profit'] = profit
        serializer.save(updated_by=self.request.user)
        if settlement:
            self._recalculate_settlement(settlement)

    def _recalculate_settlement(self, settlement):
        details = settlement.details.all()
        agg = details.aggregate(
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
        settlement.total_profit = (
            settlement.total_receive -
            settlement.total_pay -
            settlement.total_overtime -
            settlement.total_other_cost
        )
        settlement.save(update_fields=[
            'total_receive', 'total_pay', 'total_overtime',
            'total_other_cost', 'total_profit', 'updated_at',
        ])
