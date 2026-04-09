from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging

from apps.common.views import BaseViewSet
from .models import Region, RegionPrice, PriceHistory
from .serializers import RegionSerializer, RegionPriceSerializer, PriceHistorySerializer

logger = logging.getLogger(__name__)


class RegionViewSet(BaseViewSet):
    """권역 관리"""
    queryset = Region.objects.filter(is_active=True)
    serializer_class = RegionSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name']

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        user = self.request.user

        # 관리자는 모든 권역 조회
        if user.is_admin():
            return Region.objects.filter(is_active=True)

        # 팀장/일반사용자는 자신의 팀 권역만 조회
        if user.team:
            return Region.objects.filter(team=user.team, is_active=True)

        return Region.objects.none()


class RegionPriceViewSet(viewsets.ModelViewSet):
    """권역별 단가 관리"""
    serializer_class = RegionPriceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        user = self.request.user

        # 관리자는 모든 단가 조회
        if user.is_admin():
            return RegionPrice.objects.all()

        # 팀장/일반사용자는 자신의 팀 권역 단가만 조회
        if user.team:
            return RegionPrice.objects.filter(region__team=user.team)

        return RegionPrice.objects.none()

    def create(self, request, *args, **kwargs):
        """권역 단가 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 권한 확인
        region_id = request.data.get('region')
        region = get_object_or_404(Region, id=region_id)

        if not request.user.is_admin() and region.team != request.user.team:
            return Response(
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_create(serializer)

        logger.info(f'권역 단가 생성: {serializer.instance.id} (생성자: {request.user.username})')

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """권역 단가 생성 시 생성자 정보 기록"""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """권역 단가 수정 시 수정자 정보 기록 및 이력 기록"""
        instance = self.get_object()
        old_pay_price = instance.pay_price
        old_receive_price = instance.receive_price

        serializer.save(updated_by=self.request.user)

        # 지급단가 변경 시 이력 기록
        if old_pay_price != serializer.instance.pay_price:
            PriceHistory.objects.create(
                region_price=serializer.instance,
                field_changed='pay_price',
                old_value=str(old_pay_price),
                new_value=str(serializer.instance.pay_price),
                changed_by=self.request.user
            )

        # 수신단가 변경 시 이력 기록
        if old_receive_price != serializer.instance.receive_price:
            PriceHistory.objects.create(
                region_price=serializer.instance,
                field_changed='receive_price',
                old_value=str(old_receive_price),
                new_value=str(serializer.instance.receive_price),
                changed_by=self.request.user
            )

        logger.info(f'권역 단가 수정: {serializer.instance.id} (수정자: {self.request.user.username})')

    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """권역 단가 변경 이력 조회"""
        region_price = self.get_object()
        histories = region_price.histories.all()
        serializer = PriceHistorySerializer(histories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """권역 단가 이력 조회"""
    serializer_class = PriceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """권역별 이력 조회"""
        region_price_id = self.request.query_params.get('region_price_id')

        if region_price_id:
            region_price = get_object_or_404(RegionPrice, id=region_price_id)

            # 권한 확인
            user = self.request.user
            if not user.is_admin() and region_price.region.team != user.team:
                return PriceHistory.objects.none()

            return region_price.histories.all()

        return PriceHistory.objects.none()
