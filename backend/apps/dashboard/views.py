from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.settlement.models import Settlement, SettlementDetail
from apps.crew.models import CrewMember
from apps.region.models import Region
from .serializers import KPISerializer, RevenueByRegionSerializer, SettlementSummarySerializer


class DashboardViewSet(viewsets.ViewSet):
    """대시보드 조회"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def kpi(self, request):
        """KPI 조회"""
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # 쿼리셋 필터링
        if user.is_admin():
            settlements = Settlement.objects.filter(status__in=['CONFIRMED', 'PAID'])
            crews = CrewMember.objects.filter(is_active=True)
            regions = Region.objects.filter(is_active=True)
        else:
            settlements = Settlement.objects.filter(team=user.team, status__in=['CONFIRMED', 'PAID'])
            crews = CrewMember.objects.filter(team=user.team, is_active=True)
            regions = Region.objects.filter(team=user.team, is_active=True)

        # KPI 계산
        total_settlements = settlements.count()
        total_revenue = settlements.aggregate(Sum('total_receive'))['total_receive__sum'] or 0
        total_paid = settlements.aggregate(Sum('total_pay'))['total_pay__sum'] or 0
        total_profit = settlements.aggregate(Sum('total_profit'))['total_profit__sum'] or 0
        active_crews = crews.count()
        active_regions = regions.count()

        data = {
            'total_settlements': total_settlements,
            'total_revenue': total_revenue,
            'total_paid': total_paid,
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

        # 쿼리셋 필터링
        if user.is_admin():
            details = SettlementDetail.objects.all()
        else:
            details = SettlementDetail.objects.filter(settlement__team=user.team)

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

        # 쿼리셋 필터링
        if user.is_admin():
            settlements = Settlement.objects.filter(status__in=['CONFIRMED', 'PAID'])
        else:
            settlements = Settlement.objects.filter(team=user.team, status__in=['CONFIRMED', 'PAID'])

        # 기간별 정산 요약
        summary_data = []
        for settlement in settlements.order_by('-period_start'):
            summary_data.append({
                'period': f'{settlement.period_start} ~ {settlement.period_end}',
                'total_receive': settlement.total_receive,
                'total_pay': settlement.total_pay,
                'total_profit': settlement.total_profit,
            })

        serializer = SettlementSummarySerializer(summary_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly_trend(self, request):
        """월별 추세 조회"""
        user = request.user

        # 쿼리셋 필터링
        if user.is_admin():
            settlements = Settlement.objects.filter(status__in=['CONFIRMED', 'PAID'])
        else:
            settlements = Settlement.objects.filter(team=user.team, status__in=['CONFIRMED', 'PAID'])

        # 월별 추세
        trend_data = []
        for settlement in settlements.order_by('period_start'):
            trend_data.append({
                'month': settlement.period_start.strftime('%Y-%m'),
                'total_receive': settlement.total_receive,
                'total_pay': settlement.total_pay,
                'total_profit': settlement.total_profit,
            })

        return Response(trend_data)

    @action(detail=False, methods=['get'])
    def crew_statistics(self, request):
        """배송원 통계 조회"""
        user = request.user

        # 쿼리셋 필터링
        if user.is_admin():
            crews = CrewMember.objects.all()
        else:
            crews = CrewMember.objects.filter(team=user.team)

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
