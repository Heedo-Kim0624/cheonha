from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
import logging

from apps.common.views import BaseViewSet
from apps.settlement.models import SettlementDetail
from .models import CrewMember, OvertimeSetting
from .serializers import CrewMemberSerializer, OvertimeSettingSerializer

logger = logging.getLogger(__name__)


class CrewMemberViewSet(BaseViewSet):
    """배송원 관리"""
    queryset = CrewMember.objects.filter(is_active=True)
    serializer_class = CrewMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['code', 'name', 'phone']
    ordering_fields = ['code', 'name', 'is_new']

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        user = self.request.user

        if user.is_admin() or user.is_staff:
            return CrewMember.objects.filter(is_active=True)

        # 팀장은 자기 팀 배송원만
        if user.team:
            return CrewMember.objects.filter(team=user.team, is_active=True)

        return CrewMember.objects.none()

    @action(detail=False, methods=['get'])
    def new_members(self, request):
        """신규 배송원 조회"""
        queryset = self.get_queryset().filter(is_new=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def settlement_history(self, request, pk=None):
        """배송원별 정산 내역 조회"""
        crew_member = self.get_object()
        details = SettlementDetail.objects.filter(
            crew_member=crew_member
        ).select_related('settlement').order_by('-settlement__period_start')

        result = []
        for d in details:
            result.append({
                'id': d.id,
                'settlement_id': d.settlement.id,
                'period_start': d.settlement.period_start,
                'period_end': d.settlement.period_end,
                'team': d.settlement.team.name if d.settlement.team else '',
                'region': d.region,
                'delivery_type': d.delivery_type,
                'boxes': d.boxes,
                'receive_amount': int(d.receive_amount),
                'pay_amount': int(d.pay_amount),
                'overtime_cost': int(d.overtime_cost),
                'profit': int(d.profit),
                'status': d.settlement.status,
            })
        return Response(result)

    @action(detail=True, methods=['post'])
    def mark_registered(self, request, pk=None):
        """신규 배송원을 등록으로 변경"""
        crew_member = self.get_object()
        crew_member.is_new = False
        crew_member.save()

        logger.info(f'배송원 신규 상태 변경: {crew_member.code} (변경자: {request.user.username})')

        serializer = self.get_serializer(crew_member)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OvertimeSettingViewSet(viewsets.ModelViewSet):
    """연장근무 설정 관리"""
    serializer_class = OvertimeSettingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """배차 업로드별 연장근무 설정 조회"""
        upload_id = self.request.query_params.get('upload_id')

        if upload_id:
            from apps.dispatch.models import DispatchUpload

            dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)

            # 권한 확인
            user = self.request.user
            if not user.is_admin() and dispatch_upload.team != user.team:
                return OvertimeSetting.objects.none()

            return dispatch_upload.overtime_settings.all()

        return OvertimeSetting.objects.none()

    def create(self, request, *args, **kwargs):
        """연장근무 설정 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 권한 확인
        upload_id = request.data.get('dispatch_upload')
        from apps.dispatch.models import DispatchUpload

        dispatch_upload = get_object_or_404(DispatchUpload, id=upload_id)
        if not request.user.is_admin() and dispatch_upload.team != request.user.team:
            return Response(
                {'detail': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_create(serializer)

        logger.info(f'연장근무 설정 생성: {serializer.instance.id} (생성자: {request.user.username})')

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """연장근무 설정 생성 시 생성자 정보 기록"""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """연장근무 설정 수정 시 수정자 정보 기록"""
        serializer.save(updated_by=self.request.user)
        logger.info(f'연장근무 설정 수정: {serializer.instance.id} (수정자: {self.request.user.username})')
