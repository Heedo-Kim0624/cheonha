from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
import logging

from .models import User, Team
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserMeSerializer, TeamSerializer, CustomTokenObtainPairSerializer
)

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT 토큰 발급"""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """사용자 관리"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """액션에 따른 serializer 선택"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'me':
            return UserMeSerializer
        return UserSerializer

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        user = self.request.user

        # 관리자는 모든 사용자 조회
        if user.is_admin():
            return User.objects.all()

        # 팀장은 자신의 팀 멤버만 조회
        if user.is_team_leader():
            return User.objects.filter(team=user.team)

        # 일반 사용자는 자신의 정보만 조회
        return User.objects.filter(id=user.id)

    def create(self, request, *args, **kwargs):
        """사용자 생성"""
        # 관리자만 사용자 생성 가능
        if not request.user.is_admin():
            return Response(
                {'detail': '관리자만 사용자를 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """사용자 생성 시 생성자 정보 기록"""
        serializer.save()
        logger.info(f'사용자 생성: {serializer.instance.username} (생성자: {self.request.user.username})')

    def perform_update(self, serializer):
        """사용자 수정 시 수정자 정보 기록"""
        serializer.save()
        logger.info(f'사용자 수정: {serializer.instance.username} (수정자: {self.request.user.username})')

    @action(detail=False, methods=['get'])
    def me(self, request):
        """현재 사용자 정보 조회"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """비밀번호 변경"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        # 기존 비밀번호 확인
        if not user.check_password(old_password):
            return Response(
                {'old_password': ['기존 비밀번호가 일치하지 않습니다.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 새 비밀번호 일치 확인
        if new_password != new_password_confirm:
            return Response(
                {'new_password': ['새 비밀번호가 일치하지 않습니다.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 비밀번호 변경
        user.set_password(new_password)
        user.save()

        logger.info(f'비밀번호 변경: {user.username}')

        return Response(
            {'detail': '비밀번호가 변경되었습니다.'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """로그아웃"""
        # 간단한 로그아웃 처리 (JWT 토큰 블랙리스트는 settings에서 BLACKLIST_AFTER_ROTATION 설정)
        logger.info(f'로그아웃: {request.user.username}')
        return Response({'detail': '로그아웃되었습니다.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def roles(self, request):
        """역할 목록 조회"""
        roles = [{'code': code, 'name': name} for code, name in User.ROLE_CHOICES]
        return Response(roles)


class TeamViewSet(viewsets.ModelViewSet):
    """팀 관리"""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Team.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        """팀 생성"""
        # 관리자만 팀 생성 가능
        if not request.user.is_admin():
            return Response(
                {'detail': '관리자만 팀을 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        logger.info(f'팀 생성: {serializer.instance.name} (생성자: {request.user.username})')

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        """팀 수정 시 수정자 정보 기록"""
        serializer.save()
        logger.info(f'팀 수정: {serializer.instance.name} (수정자: {self.request.user.username})')

    @action(detail=True, methods=['post'])
    def recalc_settlements(self, request, pk=None):
        """팀 수신단가 변경 후 기존 정산 재계산"""
        team = self.get_object()
        from decimal import Decimal
        from django.db.models import Sum
        from apps.settlement.models import Settlement, SettlementDetail
        from apps.crew.models import CrewMember

        receive_price = team.receive_price or Decimal('0')
        details = SettlementDetail.objects.filter(settlement__team=team)
        updated = 0
        settlement_ids = set()

        for d in details:
            # 배송원 지급단가
            crew_pay = Decimal('0')
            if d.crew_member:
                crew_pay = d.crew_member.pay_price or Decimal('0')
            new_receive = receive_price * Decimal(str(d.boxes))
            new_pay = crew_pay * Decimal(str(d.boxes))
            d.receive_amount = new_receive
            d.pay_amount = new_pay
            d.profit = new_receive - new_pay - d.overtime_cost - d.other_cost
            d.save(update_fields=['receive_amount', 'pay_amount', 'profit'])
            settlement_ids.add(d.settlement_id)
            updated += 1

        for sid in settlement_ids:
            try:
                s = Settlement.objects.get(id=sid)
                agg = s.details.aggregate(r=Sum('receive_amount'), p=Sum('pay_amount'), o=Sum('overtime_cost'), pr=Sum('profit'))
                s.total_receive = agg['r'] or 0
                s.total_pay = agg['p'] or 0
                s.total_overtime = agg['o'] or 0
                s.total_profit = agg['pr'] or 0
                s.save()
            except Settlement.DoesNotExist:
                pass

        return Response({'detail': f'{updated}건 정산 재계산 완료'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def teams_list(self, request):
        """팀 목록 조회 (권한 없이 조회 가능)"""
        teams = Team.objects.filter(is_active=True)
        serializer = self.get_serializer(teams, many=True)
        return Response(serializer.data)
