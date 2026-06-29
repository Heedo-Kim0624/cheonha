import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, Max
from django.utils import timezone

from apps.settlement.models import Settlement, SettlementDetail
from apps.dispatch.date_utils import date_iso, to_work_date
from apps.common.company_scope import get_company_app_from_request
from apps.accounts.models import CompanyApp
from apps.crew.models import CrewMember
from apps.region.models import Region
from .serializers import KPISerializer, RevenueByRegionSerializer, SettlementSummarySerializer
from .workflow_monitor import snapshot


class DashboardViewSet(viewsets.ViewSet):
    """대시보드 조회"""
    permission_classes = [permissions.IsAuthenticated]

    def _scoped_settlements(self, user):
        company_app = get_company_app_from_request(self.request)
        if user.is_admin():
            return Settlement.objects.filter(status__in=['CONFIRMED', 'PAID'], team__company_app=company_app)
        return Settlement.objects.filter(team=user.team, status__in=['CONFIRMED', 'PAID'])

    def _scoped_details(self, user):
        company_app = get_company_app_from_request(self.request)
        details = SettlementDetail.objects.filter(
            settlement__status__in=['CONFIRMED', 'PAID'],
            is_yongcha=False,
        )
        if user.is_admin():
            details = details.filter(settlement__team__company_app=company_app)
        else:
            details = details.filter(settlement__team=user.team)
        return details

    def _parse_date_param(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    def _parse_month_param(self, value):
        today = timezone.localdate()
        if not value:
            return today.year, today.month
        try:
            parsed = datetime.strptime(str(value), "%Y-%m").date()
            return parsed.year, parsed.month
        except (TypeError, ValueError):
            return today.year, today.month

    def _month_range(self, year, month):
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return start, end

    def _previous_month_range(self, year, month):
        if month == 1:
            return self._month_range(year - 1, 12)
        return self._month_range(year, month - 1)

    def _business_days_between(self, start, end):
        if not start or not end or start > end:
            return 0
        count = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                count += 1
            current += timedelta(days=1)
        return count

    def _company_options(self, request):
        user = request.user
        qs = CompanyApp.objects.exclude(status=CompanyApp.Status.DELETED).order_by("name", "code")
        if not user.is_admin():
            qs = qs.filter(code=getattr(getattr(user, "team", None), "company_app", ""))
        return [
            {"code": row.code, "name": row.name}
            for row in qs
        ]

    def _sales_details_for_month(self, request, start, end, company_code=""):
        user = request.user
        details = SettlementDetail.objects.filter(
            settlement__status__in=["CONFIRMED", "PAID"],
            settlement__period_start__gte=start,
            settlement__period_start__lte=end,
        )
        if user.is_admin():
            if company_code:
                details = details.filter(settlement__team__company_app=company_code)
        else:
            details = details.filter(settlement__team=user.team)
        return details

    @action(detail=False, methods=['get'])
    def kpi(self, request):
        """KPI 조회"""
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        settlements = self._scoped_settlements(user)
        details = self._scoped_details(user)
        company_app = get_company_app_from_request(request)
        if user.is_admin():
            crews = CrewMember.objects.filter(is_active=True, is_yongcha=False, team__company_app=company_app)
            regions = Region.objects.filter(is_active=True, team__company_app=company_app)
        else:
            crews = CrewMember.objects.filter(team=user.team, is_active=True, is_yongcha=False)
            regions = Region.objects.filter(team=user.team, is_active=True)

        # KPI 계산
        total_settlements = settlements.count()
        total_revenue = details.aggregate(Sum('receive_amount'))['receive_amount__sum'] or 0
        total_paid = details.aggregate(Sum('pay_amount'))['pay_amount__sum'] or 0
        total_overtime = details.aggregate(Sum('overtime_cost'))['overtime_cost__sum'] or 0
        total_other = details.aggregate(Sum('other_cost'))['other_cost__sum'] or 0
        total_profit = details.aggregate(Sum('profit'))['profit__sum'] or 0
        active_crews = crews.count()
        active_regions = regions.count()

        data = {
            'total_settlements': total_settlements,
            'total_revenue': total_revenue,
            'total_paid': total_paid,
            'total_overtime': total_overtime,
            'total_other_cost': total_other,
            'total_profit': total_profit,
            'active_crews': active_crews,
            'active_regions': active_regions,
        }

        serializer = KPISerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def revenue_by_region(self, request):
        """권역별 수익 조회"""
        user = request.user

        details = self._scoped_details(user)

        # 권역별 수익 집계
        revenue_data = details.values('region').annotate(
            revenue=Sum('receive_amount'),
            count=Count('id')
        ).order_by('-revenue')

        serializer = RevenueByRegionSerializer(revenue_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def settlement_summary(self, request):
        """정산 요약 조회"""
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        settlements = self._scoped_settlements(user)

        # 기간별 정산 요약
        summary_data = []
        for settlement in settlements.order_by('-period_start'):
            visible_details = settlement.details.filter(is_yongcha=False)
            agg = visible_details.aggregate(
                receive=Sum('receive_amount'),
                pay=Sum('pay_amount'),
                profit=Sum('profit'),
            )
            summary_data.append({
                'period': f'{date_iso(settlement.period_start)} ~ {date_iso(settlement.period_end)}',
                'total_receive': agg['receive'] or 0,
                'total_pay': agg['pay'] or 0,
                'total_profit': agg['profit'] or 0,
            })

        serializer = SettlementSummarySerializer(summary_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def home_overview(self, request):
        user = request.user
        team_name = request.query_params.get('team_name')
        start = self._parse_date_param(request.query_params.get('start'))
        end = self._parse_date_param(request.query_params.get('end'))

        settlements = self._scoped_settlements(user)
        if team_name:
            settlements = settlements.filter(team__name=team_name)
        if start and end:
            if start > end:
                start, end = end, start
            settlements = settlements.filter(
                period_end__gte=start,
                period_start__lte=end,
            )

        settlements = settlements.select_related('team').order_by('-period_end', '-period_start', '-id')
        settlement_count = settlements.count()
        details = SettlementDetail.objects.filter(settlement__in=settlements)

        regular_filter = Q(is_yongcha=False, crew_member__is_yongcha=False)
        yongcha_crew_filter = Q(crew_member__is_yongcha=True)
        regular_yongcha_filter = Q(is_yongcha=True, crew_member__is_yongcha=False)

        totals = details.aggregate(
            total_receive=Sum('receive_amount'),
            total_revenue=Sum('receive_amount', filter=regular_filter),
            total_paid=Sum('pay_amount', filter=regular_filter),
            total_overtime=Sum('overtime_cost'),
            total_profit=Sum('profit'),
            total_yongcha_receive=Sum('receive_amount', filter=yongcha_crew_filter),
            total_yongcha_pay=Sum('pay_amount', filter=yongcha_crew_filter),
            regular_yongcha_receive=Sum('receive_amount', filter=regular_yongcha_filter),
            regular_yongcha_pay=Sum('pay_amount', filter=regular_yongcha_filter),
        )

        summary = {
            'total_receive': int(totals['total_receive'] or 0),
            'total_revenue': int(totals['total_revenue'] or 0),
            'total_paid': int(totals['total_paid'] or 0),
            'total_overtime': int(totals['total_overtime'] or 0),
            'total_profit': int(totals['total_profit'] or 0),
            'total_yongcha_receive': int(totals['total_yongcha_receive'] or 0),
            'total_yongcha_pay': int(totals['total_yongcha_pay'] or 0),
            'regular_yongcha_receive': int(totals['regular_yongcha_receive'] or 0),
            'regular_yongcha_pay': int(totals['regular_yongcha_pay'] or 0),
        }

        daily_breakdown = []
        daily_rows = (
            details
            .values('settlement__period_start')
            .annotate(
                total_receive=Sum('receive_amount'),
                total_paid=Sum('pay_amount', filter=regular_filter),
                total_yongcha_pay=Sum('pay_amount', filter=yongcha_crew_filter),
                regular_yongcha_pay=Sum('pay_amount', filter=regular_yongcha_filter),
                total_profit=Sum('profit'),
            )
            .order_by('-settlement__period_start')
        )
        for row in daily_rows:
            day = row.get('settlement__period_start')
            daily_breakdown.append({
                'date': date_iso(day),
                'work_date': date_iso(to_work_date(day)),
                'total_receive': int(row.get('total_receive') or 0),
                'total_paid': int(row.get('total_paid') or 0),
                'total_yongcha_pay': int(row.get('total_yongcha_pay') or 0),
                'regular_yongcha_pay': int(row.get('regular_yongcha_pay') or 0),
                'total_profit': int(row.get('total_profit') or 0),
            })

        recent_dates = list(
            settlements
            .values('period_start')
            .annotate(latest_settlement_id=Max('id'))
            .order_by('-period_start')[:3]
            .values_list('period_start', flat=True)
        )
        recent_settlements = list(
            details.filter(settlement__period_start__in=recent_dates)
            .values(
                'settlement__period_start',
                'settlement__period_end',
                'settlement__team_id',
                'settlement__team__name',
            )
            .annotate(
                latest_settlement_id=Max('settlement_id'),
                detail_total_receive=Sum('receive_amount'),
                regular_total_receive=Sum('receive_amount', filter=regular_filter),
                regular_total_pay=Sum('pay_amount', filter=regular_filter),
                regular_total_overtime=Sum('overtime_cost', filter=regular_filter),
                yongcha_total_receive=Sum('receive_amount', filter=yongcha_crew_filter),
                yongcha_total_pay=Sum('pay_amount', filter=yongcha_crew_filter),
                regular_yongcha_total_receive=Sum('receive_amount', filter=regular_yongcha_filter),
                regular_yongcha_total_pay=Sum('pay_amount', filter=regular_yongcha_filter),
                total_profit=Sum('profit'),
            )
            .order_by('-settlement__period_start', '-latest_settlement_id')
        )

        for item in recent_settlements:
            period_start = item.pop('settlement__period_start', None)
            period_end = item.pop('settlement__period_end', None)
            team_id = item.pop('settlement__team_id', None)
            item['id'] = f"{date_iso(period_start)}-{team_id or 'none'}"
            item['team_name'] = item.pop('settlement__team__name', '') or ''
            item['detail_total_receive'] = int(item.get('detail_total_receive') or 0)
            item['regular_total_receive'] = int(item.get('regular_total_receive') or 0)
            item['regular_total_pay'] = int(item.get('regular_total_pay') or 0)
            item['regular_total_overtime'] = int(item.get('regular_total_overtime') or 0)
            item['yongcha_total_receive'] = int(item.get('yongcha_total_receive') or 0)
            item['yongcha_total_pay'] = int(item.get('yongcha_total_pay') or 0)
            item['regular_yongcha_total_receive'] = int(item.get('regular_yongcha_total_receive') or 0)
            item['regular_yongcha_total_pay'] = int(item.get('regular_yongcha_total_pay') or 0)
            item['total_profit'] = int(item.get('total_profit') or 0)
            item['work_period_start'] = date_iso(to_work_date(period_start))
            item['work_period_end'] = date_iso(to_work_date(period_end))
            item['period_start'] = date_iso(period_start)
            item['period_end'] = date_iso(period_end)

        team_order = {'A조': 0, 'A': 0, 'R조': 1, 'R': 1, 'X조': 2, 'X': 2}
        recent_settlements.sort(
            key=lambda item: (
                team_order.get(item.get('team_name'), 99),
                item.get('team_name') or '',
                -(int(str(item.get('period_start') or '0000-00-00').replace('-', ''))),
            )
        )
        latest_settlement_date = max(
            (item['period_end'] for item in recent_settlements if item.get('period_end')),
            default=None,
        )

        return Response({
            'settlement_count': settlement_count,
            'latest_settlement_date': latest_settlement_date,
            'summary': summary,
            'daily_breakdown': daily_breakdown,
            'recent_settlements': recent_settlements,
        })

    @action(detail=False, methods=['get'])
    def sales_overview(self, request):
        year, month = self._parse_month_param(request.query_params.get("month"))
        company_code = str(
            request.query_params.get("company_code")
            or request.query_params.get("company_app")
            or ""
        ).strip().lower()
        if company_code in {"all", "전체"}:
            company_code = ""

        month_start, month_end = self._month_range(year, month)
        prev_start, prev_end = self._previous_month_range(year, month)
        today = timezone.localdate()
        elapsed_end = month_end
        if month_start <= today <= month_end:
            elapsed_end = today
        elif today < month_start:
            elapsed_end = month_start - timedelta(days=1)

        calendar_days_elapsed = max((elapsed_end - month_start).days + 1, 0)
        calendar_days_in_month = (month_end - month_start).days + 1
        business_days_elapsed = calendar_days_elapsed
        business_days_in_month = calendar_days_in_month

        details = self._sales_details_for_month(request, month_start, month_end, company_code)
        previous_details = self._sales_details_for_month(request, prev_start, prev_end, company_code)

        box_rate = 40
        total_boxes = int(details.aggregate(total=Sum("boxes"))["total"] or 0)
        total_revenue = total_boxes * box_rate
        previous_boxes = int(previous_details.aggregate(total=Sum("boxes"))["total"] or 0)
        previous_revenue = previous_boxes * box_rate

        if previous_revenue:
            month_over_month_percent = round(((total_revenue - previous_revenue) / previous_revenue) * 100, 1)
        else:
            month_over_month_percent = None

        average_basis_days = max(calendar_days_elapsed, 1)
        average_daily_revenue = round(total_revenue / average_basis_days) if total_revenue else 0
        expected_monthly_revenue = average_daily_revenue * calendar_days_in_month

        monthly_rows = list(
            details.values("settlement__team__company_app")
            .annotate(boxes=Sum("boxes"))
            .order_by("settlement__team__company_app")
        )
        company_options = self._company_options(request)
        company_name_map = {row["code"]: row["name"] for row in company_options}
        visible_company_codes = {
            row["settlement__team__company_app"] or "cheonha"
            for row in monthly_rows
        }
        if company_code:
            visible_company_codes.add(company_code)
        else:
            visible_company_codes.update(company_name_map.keys())

        monthly_by_company = []
        for row in monthly_rows:
            code = row["settlement__team__company_app"] or "cheonha"
            boxes = int(row["boxes"] or 0)
            monthly_by_company.append({
                "company_code": code,
                "company_name": company_name_map.get(code, code),
                "boxes": boxes,
                "revenue": boxes * box_rate,
            })

        for code in sorted(visible_company_codes):
            if not any(item["company_code"] == code for item in monthly_by_company):
                monthly_by_company.append({
                    "company_code": code,
                    "company_name": company_name_map.get(code, code),
                    "boxes": 0,
                    "revenue": 0,
                })

        daily_rows = list(
            details.values("settlement__period_start")
            .annotate(boxes=Sum("boxes"))
            .order_by("settlement__period_start")
        )
        daily_lookup = {
            row["settlement__period_start"]: int(row["boxes"] or 0)
            for row in daily_rows
            if row["settlement__period_start"]
        }
        daily_sales = []
        current = month_start
        while current <= month_end:
            boxes = daily_lookup.get(current, 0)
            daily_sales.append({
                "date": date_iso(current),
                "day": current.day,
                "weekday": current.weekday(),
                "is_business_day": current.weekday() < 5,
                "boxes": boxes,
                "revenue": boxes * box_rate,
            })
            current += timedelta(days=1)

        company_options = [
            {"code": "all", "name": "전체"},
            *company_options,
        ]

        return Response({
            "month": f"{year}-{month:02d}",
            "company_code": company_code or "all",
            "box_rate": box_rate,
            "company_options": company_options,
            "summary": {
                "total_revenue": total_revenue,
                "previous_month_revenue": previous_revenue,
                "month_over_month_percent": month_over_month_percent,
                "total_boxes": total_boxes,
                "average_daily_revenue": average_daily_revenue,
                "business_days_elapsed": business_days_elapsed,
                "business_days_in_month": business_days_in_month,
                "calendar_days_elapsed": calendar_days_elapsed,
                "calendar_days_in_month": calendar_days_in_month,
                "expected_monthly_revenue": expected_monthly_revenue,
            },
            "monthly_by_company": monthly_by_company,
            "monthly_by_shipper": [
                {
                    "shipper_code": row["company_code"],
                    "shipper_name": row["company_name"],
                    "boxes": row["boxes"],
                    "revenue": row["revenue"],
                }
                for row in monthly_by_company
            ],
            "daily_sales": daily_sales,
            "expected": {
                "average_daily_revenue": average_daily_revenue,
                "business_days_in_month": business_days_in_month,
                "calendar_days_elapsed": calendar_days_elapsed,
                "calendar_days_in_month": calendar_days_in_month,
                "expected_monthly_revenue": expected_monthly_revenue,
                "basis_text": f"{calendar_days_elapsed}일 기준",
            },
        })

    @action(detail=False, methods=['get'])
    def home_daily_detail(self, request):
        user = request.user
        target_date = self._parse_date_param(request.query_params.get('date'))
        if not target_date:
            return Response({'detail': 'date is required.'}, status=400)

        metric = request.query_params.get('metric') or 'total_receive'
        metric_config = {
            'total_receive': {
                'label': '전체 수신',
                'amount_field': 'receive_amount',
                'filter': Q(),
            },
            'total_paid': {
                'label': '정규 지급',
                'amount_field': 'pay_amount',
                'filter': Q(is_yongcha=False, crew_member__is_yongcha=False),
            },
            'total_yongcha_pay': {
                'label': '용차 지급',
                'amount_field': 'pay_amount',
                'filter': Q(crew_member__is_yongcha=True),
            },
            'regular_yongcha_pay': {
                'label': '정규 용차 지급',
                'amount_field': 'pay_amount',
                'filter': Q(is_yongcha=True, crew_member__is_yongcha=False),
            },
            'total_profit': {
                'label': '수익',
                'amount_field': 'profit',
                'filter': Q(),
            },
        }
        if metric not in metric_config:
            metric = 'total_receive'
        metric_info = metric_config[metric]

        team_name = request.query_params.get('team_name')
        settlements = self._scoped_settlements(user).filter(
            period_start__lte=target_date,
            period_end__gte=target_date,
        )
        if team_name:
            settlements = settlements.filter(team__name=team_name)

        details = (
            SettlementDetail.objects
            .filter(settlement__in=settlements)
            .filter(metric_info['filter'])
            .select_related(
                'settlement',
                'settlement__team',
                'dispatch_upload',
                'dispatch_upload__team',
                'crew_member',
                'crew_member__team',
                'crew_member__yongcha_pay_group',
            )
        )

        grouped = {}
        for detail in details:
            key = (
                detail.settlement_id,
                detail.dispatch_upload_id or 0,
                detail.crew_member_id or 0,
                detail.is_yongcha,
            )
            row = grouped.setdefault(key, {
                'settlement': detail.settlement,
                'dispatch_upload': detail.dispatch_upload,
                'crew_member': detail.crew_member,
                'is_yongcha': bool(detail.is_yongcha),
                'boxes': 0,
                'households': 0,
                'receive_amount': 0,
                'pay_amount': 0,
                'profit': 0,
                'metric_amount': 0,
            })
            row['boxes'] += int(detail.boxes or 0)
            row['receive_amount'] += int(detail.receive_amount or 0)
            row['pay_amount'] += int(detail.pay_amount or 0)
            row['profit'] += int(detail.profit or 0)
            row['metric_amount'] += int(getattr(detail, metric_info['amount_field'], 0) or 0)

        household_cache = {}
        for row in grouped.values():
            upload = row['dispatch_upload']
            crew = row['crew_member']
            if not upload or not crew:
                continue
            cache_key = (upload.id, crew.id)
            if cache_key not in household_cache:
                names = [name for name in {crew.code, crew.name} if name]
                household_cache[cache_key] = (
                    upload.records
                    .filter(is_valid=True, manager_name__in=names)
                    .aggregate(total=Sum('households'))['total'] or 0
                )
            row['households'] = int(household_cache[cache_key] or 0)

        rounds = defaultdict(lambda: {
            'round_no': None,
            'round_label': '회차 미지정',
            'rows': [],
            'totals': {
                'households': 0,
                'boxes': 0,
                'receive_amount': 0,
                'pay_amount': 0,
                'profit': 0,
                'metric_amount': 0,
            },
        })

        for row in grouped.values():
            upload = row['dispatch_upload']
            crew = row['crew_member']
            settlement = row['settlement']
            round_no = getattr(upload, 'round_no', None)
            round_key = round_no or 0
            round_row = rounds[round_key]
            round_row['round_no'] = round_no
            round_row['round_label'] = f'{round_no}회차' if round_no else '회차 미지정'

            team_name_value = (
                getattr(getattr(upload, 'team', None), 'name', None) or
                getattr(getattr(settlement, 'team', None), 'name', '') or
                ''
            )
            yongcha_group = getattr(crew, 'yongcha_pay_group', None) if crew else None
            item = {
                'team_name': team_name_value,
                'crew_member_id': crew.id if crew else None,
                'crew_name': crew.name if crew else '미등록',
                'crew_code': crew.code if crew else '',
                'crew_type': '용차관리' if getattr(crew, 'is_yongcha', False) else '정규',
                'is_yongcha': row['is_yongcha'],
                'has_yongcha_pay_group': bool(row['is_yongcha'] and yongcha_group),
                'yongcha_pay_group_name': yongcha_group.name if row['is_yongcha'] and yongcha_group else '',
                'households': row['households'],
                'boxes': row['boxes'],
                'receive_amount': row['receive_amount'],
                'pay_amount': row['pay_amount'],
                'profit': row['profit'],
                'metric_amount': row['metric_amount'],
            }
            round_row['rows'].append(item)
            for field in ('households', 'boxes', 'receive_amount', 'pay_amount', 'profit', 'metric_amount'):
                round_row['totals'][field] += int(item[field] or 0)

        response_rounds = []
        for _, round_row in sorted(rounds.items(), key=lambda item: item[0]):
            round_row['rows'].sort(key=lambda item: (item['team_name'], item['crew_name'], item['crew_code']))
            response_rounds.append(round_row)

        totals = {
            'households': sum(round_row['totals']['households'] for round_row in response_rounds),
            'boxes': sum(round_row['totals']['boxes'] for round_row in response_rounds),
            'receive_amount': sum(round_row['totals']['receive_amount'] for round_row in response_rounds),
            'pay_amount': sum(round_row['totals']['pay_amount'] for round_row in response_rounds),
            'profit': sum(round_row['totals']['profit'] for round_row in response_rounds),
            'metric_amount': sum(round_row['totals']['metric_amount'] for round_row in response_rounds),
        }

        return Response({
            'date': date_iso(target_date),
            'team_name': team_name or '',
            'metric': metric,
            'metric_label': metric_info['label'],
            'totals': totals,
            'rounds': response_rounds,
        })

    @action(detail=False, methods=['get'])
    def monthly_trend(self, request):
        """월별 추세 조회"""
        user = request.user

        settlements = self._scoped_settlements(user)

        # 월별 추세
        trend_data = []
        for settlement in settlements.order_by('period_start'):
            visible_details = settlement.details.filter(is_yongcha=False)
            agg = visible_details.aggregate(
                receive=Sum('receive_amount'),
                pay=Sum('pay_amount'),
                profit=Sum('profit'),
            )
            trend_data.append({
                'month': settlement.period_start.strftime('%Y-%m'),
                'total_receive': agg['receive'] or 0,
                'total_pay': agg['pay'] or 0,
                'total_profit': agg['profit'] or 0,
            })

        return Response(trend_data)

    @action(detail=False, methods=['get'])
    def crew_statistics(self, request):
        """배송원 통계 조회"""
        user = request.user

        # 쿼리셋 필터링
        company_app = get_company_app_from_request(request)
        if user.is_admin():
            crews = CrewMember.objects.filter(is_yongcha=False, team__company_app=company_app)
        else:
            crews = CrewMember.objects.filter(team=user.team, is_yongcha=False)

        # 통계
        total_crews = crews.count()
        active_crews = crews.filter(is_active=True).count()
        new_crews = crews.filter(is_new=True).count()

        data = {
            'total_crews': total_crews,
            'active_crews': active_crews,
            'new_crews': new_crews,
            'inactive_crews': total_crews - active_crews,
        }

        return Response(data)


class WorkflowMonitorViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        if not (request.user.is_staff or getattr(request.user, "is_admin", lambda: False)()):
            return Response({"detail": "관리자만 접근할 수 있습니다."}, status=403)
        return Response(snapshot())
