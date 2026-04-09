from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class BaseViewSet(viewsets.ModelViewSet):
    """기본 ViewSet - 권한 검증 및 팀 필터링 기능"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        queryset = super().get_queryset()
        user = self.request.user

        # 관리자는 전체 데이터 조회
        if user.is_admin():
            return queryset

        # 팀장/일반사용자는 자신의 팀 데이터만 조회
        if hasattr(queryset.model, 'team') and user.team:
            return queryset.filter(team=user.team)

        return queryset

    def perform_create(self, serializer):
        """생성 시 생성자 정보 기록"""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """수정 시 수정자 정보 기록"""
        serializer.save(updated_by=self.request.user)
