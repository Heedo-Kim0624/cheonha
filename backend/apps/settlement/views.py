from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import logging

from apps.dispatch.models import DispatchUpload, DispatchRecord
from apps.region.models import Region, RegionPrice
from apps.accounts.models import Team
from .models import Settlement, SettlementDetail
from .serializers import (
    SettlementSerializer, SettlementCreateSerializer,
    SettlementDetailSerializer, SettlementConfirmSerializer
)

logger = logging.getLogger(__name__)


class SettlementViewSet(viewsets.ModelViewSet):
    """정산 관리"""
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SettlementCreateSerializer
        return SettlementSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin():
            return Settlement.objects.all()
        if user.team:
            return Settlement.objects.filter(team=user.team)
        return Settlement.objects.none()

    def create(self, request, *args, **kwargs):
        """정산 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = serializer.validated_data.get('team')
        if not team:
            return Response(
                {'team': ['팀을 선택해주세요.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.is_team_leader() and request.user.team != team:
            return Response(
                {'team': ['자신의 팀에만 정산할 수 있습니다.']},
                status=status.HTTP_403_FORBIDDEN
            )

        settlement = Settlement.objects.create(**serializer.validated_data)
        response_serializer = SettlementSerializer(settlement)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """배차 데이터 기반 정산 자동 생성
        Body: {"upload_id": 1}
        — 해당 업로드의 레코드에서 권역단가를 조회하여 정산 자동 계산
        """
        upload_id = request.data.get('upload_id')
        if not upload_id:
            return Response(
                {'detail': 'upload_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)

        # 권한 확인
        if not request.user.is_admin() and dispatch_upload.team != request.user.team:
            return Response(
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 확정된 배차만 정산 가능
        if dispatch_upload.status != 'CONFIRMED':
            return Response(
                {'detail': '확정된 배차 데이터만 정산할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        team = dispatch_upload.team
        today = timezone.now().date()

        # 정산 생성
        settlement, created = Settlement.objects.get_or_create(
            team=team,
            period_start=today,
            period_end=today,
            defaults={
                'status': 'DRAFT',
                'note': f'배차 업로드 #{upload_id} 기반 자동 정산',
            }
        )

        if not created:
            # 기존 정산의 상세 삭제 후 재생성
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

            # 권역 조회
            try:
                region = Region.objects.get(code=record.detail_region)
            except Region.DoesNotExist:
                missing_prices.append(record.detail_region)
                continue

            # 배송타입 매핑 (한국어 → 코드)
            delivery_type_map = {
                '당일': 'SAME_DAY',
                '익일': 'NEXT_DAY',
                'SAME_DAY': 'SAME_DAY',
                'NEXT_DAY': 'NEXT_DAY',
            }
            dt_code = delivery_type_map.get(record.delivery_type, 'SAME_DAY')

            # 단가 조회 (가장 최근 유효한 단가)
            price = RegionPrice.objects.filter(
                region=region,
                delivery_type=dt_code,
                start_date__lte=today,
            ).filter(
                # end_date가 null이거나 오늘 이후인 것
                **{}
            ).order_by('-start_date').first()

            if not price:
                # end_date 조건 없이 가장 최근 단가
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

        # 합계 업데이트
        settlement.total_receive = total_receive
        settlement.total_pay = total_pay
        settlement.total_overtime = total_overtime
        settlement.total_profit = total_receive - total_pay - total_overtime
        settlement.save()

        logger.info(
            f'정산 자동 생성: settlement #{settlement.id} — '
            f'{details_created}건, 수신액 {total_receive}, 지급액 {total_pay}'
        )

        serializer = SettlementSerializer(settlement)
        return Response({
            'settlement': serializer.data,
            'details_created': details_created,
            'missing_prices': list(set(missing_prices)),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """정산 확정"""
        settlement = self.get_object()

        if settlement.status in ['CONFIRMED', 'PAID']:
            return Response(
                {'detail': '이미 확정된 정산입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not settlement.details.exists():
            return Response(
                {'detail': '정산 상세 정보가 없습니다.'},
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

        logger.info(f'정산 확정: {settlement.id} (확정자: {request.user.username})')

        serializer = SettlementSerializer(settlement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """정산 지급 완료 표시"""
        settlement = self.get_object()

        if settlement.status != 'CONFIRMED':
            return Response(
                {'detail': '확정된 정산만 지급 완료로 표시할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        settlement.status = 'PAID'
        settlement.save()

        serializer = SettlementSerializer(settlement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def recalc(self, request, pk=None):
        """정산 합계 재계산"""
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

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """정산서 내보내기 (CSV)"""
        settlement = self.get_object()

        if not request.user.is_admin() and settlement.team != request.user.team:
            return Response(
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        import csv
        from io import StringIO
        from django.http import HttpResponse

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            '정산 기간', f'{settlement.period_start} ~ {settlement.period_end}',
            '팀', settlement.team.name if settlement.team else '',
            '상태', settlement.get_status_display()
        ])
        writer.writerow([])
        writer.writerow([
            '배송원코드', '배송원명', '권역', '배송타입',
            '박스수', '수신액', '지급액', '연장근무료', '이윤'
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
            '합계', '', '', '', '',
            settlement.total_receive, settlement.total_pay,
            settlement.total_overtime, settlement.total_profit
        ])

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=settlement_{settlement.id}.csv'
        return response


class SettlementDetailViewSet(viewsets.ModelViewSet):
    """정산 상세 정보 관리"""
    serializer_class = SettlementDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        settlement_id = self.request.query_params.get('settlement_id')
        user = self.request.user

        # PATCH/DELETE 등 개별 접근 시 전체에서 찾기
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
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if settlement.status in ['CONFIRMED', 'PAID']:
            return Response(
                {'detail': '확정된 정산은 상세 정보를 추가할 수 없습니다.'},
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
        new_boxes = serializer.validated_data.get('boxes', obj.boxes)

        # 박스수 변경 시 pay/receive 자동 재계산 (단가 유지)
        if new_boxes != obj.boxes and 'receive_amount' not in serializer.validated_data:
            team = obj.settlement.team if obj.settlement else None
            receive_price = team.receive_price if team else Decimal('0')
            serializer.validated_data['receive_amount'] = receive_price * Decimal(str(new_boxes))
        if new_boxes != obj.boxes and 'pay_amount' not in serializer.validated_data:
            crew = obj.crew_member
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
