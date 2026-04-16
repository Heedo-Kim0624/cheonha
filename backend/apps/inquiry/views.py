from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from .models import SettlementInquiry, InquiryMessage
from .serializers import SettlementInquirySerializer, InquiryMessageSerializer

from apps.crew.models import CrewMember
from apps.settlement.models import Settlement, SettlementDetail


class SettlementInquiryViewSet(viewsets.ModelViewSet):
    queryset = SettlementInquiry.objects.all()
    serializer_class = SettlementInquirySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = SettlementInquiry.objects.all().prefetch_related('messages')
        team_name = self.request.query_params.get('team_name')
        status_filter = self.request.query_params.get('status')
        if team_name:
            qs = qs.filter(team_name=team_name)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """신규 문의 (모바일에서 생성)"""
        data = request.data.copy()
        initial_message = data.pop('message', None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save(
            status='OPEN',
            last_by='crew',
            boxes=data.get('original_boxes', 0),
            pay_price=data.get('original_pay_price', 0),
            adjustment_amount=data.get('original_adjustment', 0),
            total_amount=data.get('original_total', 0),
        )

        # 초기 메시지
        if initial_message:
            content = initial_message if isinstance(initial_message, str) else initial_message.get('content', '')
            if content:
                InquiryMessage.objects.create(
                    inquiry=inquiry,
                    author_type='crew',
                    author_name=inquiry.crew_name,
                    content=content,
                )

        return Response(self.get_serializer(inquiry).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """관리자 수정: 박스수/단가/조정 → 정산금액 자동 + 배송원/정산/배차 연동"""
        inquiry = self.get_object()
        data = request.data

        old_pay_price = inquiry.pay_price
        old_boxes = inquiry.boxes
        old_adjustment = inquiry.adjustment_amount
        old_other_cost = inquiry.other_cost

        if 'boxes' in data:
            inquiry.boxes = int(data['boxes'])
        if 'pay_price' in data:
            inquiry.pay_price = Decimal(str(data['pay_price']))
        if 'is_overtime' in data:
            inquiry.is_overtime = bool(data['is_overtime'])
        if 'adjustment_amount' in data:
            inquiry.adjustment_amount = Decimal(str(data['adjustment_amount']))
        if 'other_cost' in data:
            inquiry.other_cost = Decimal(str(data['other_cost']))

        # 자동 합산: 박스 * 지급단가 + 조정금액 (기타지출은 배송원 지급에서 차감하지 않음)
        inquiry.total_amount = (
            inquiry.pay_price * Decimal(str(inquiry.boxes)) + inquiry.adjustment_amount
        )

        pay_price_changed = inquiry.pay_price != old_pay_price
        boxes_changed = inquiry.boxes != old_boxes
        adjustment_changed = inquiry.adjustment_amount != old_adjustment
        other_cost_changed = inquiry.other_cost != old_other_cost
        any_changed = boxes_changed or pay_price_changed or adjustment_changed or other_cost_changed

        with transaction.atomic():
            inquiry.save()

            # 1. 배송원 지급단가 반영 (기본: 현재 이후에만 적용)
            if pay_price_changed and inquiry.crew_member:
                inquiry.crew_member.pay_price = inquiry.pay_price
                inquiry.crew_member.save(update_fields=['pay_price'])

            # 2. 해당 날짜 정산 detail 업데이트 (운영현황/대시보드는 정산 기반이므로 여기서 전파됨)
            if any_changed and inquiry.crew_member:
                details = SettlementDetail.objects.filter(
                    crew_member=inquiry.crew_member,
                    settlement__period_start=inquiry.dispatch_date,
                    settlement__period_end=inquiry.dispatch_date,
                )
                settlement_ids = set()
                if details.exists():
                    count = details.count()
                    per = inquiry.boxes // count
                    rem = inquiry.boxes % count
                    receive_price = inquiry.team.receive_price if inquiry.team else Decimal('0')
                    for i, d in enumerate(details.order_by('id')):
                        new_boxes = per + (1 if i < rem else 0) if boxes_changed else d.boxes
                        d.boxes = new_boxes
                        d.receive_amount = receive_price * Decimal(str(new_boxes))
                        d.pay_amount = inquiry.pay_price * Decimal(str(new_boxes))
                        # 조정금액/기타지출은 첫 번째 detail에 귀속
                        if i == 0:
                            d.overtime_cost = inquiry.adjustment_amount
                            d.other_cost = inquiry.other_cost
                        else:
                            d.overtime_cost = Decimal('0')
                            d.other_cost = Decimal('0')
                        # profit = 수신 - 지급 - 조정비용 - 기타지출
                        d.profit = d.receive_amount - d.pay_amount - d.overtime_cost - d.other_cost
                        d.save(update_fields=['boxes', 'receive_amount', 'pay_amount', 'overtime_cost', 'other_cost', 'profit'])
                        settlement_ids.add(d.settlement_id)

                # 정산 합계 재계산
                for sid in settlement_ids:
                    try:
                        s = Settlement.objects.get(id=sid)
                        agg = s.details.aggregate(
                            r=Sum('receive_amount'), p=Sum('pay_amount'),
                            o=Sum('overtime_cost'), oc=Sum('other_cost'), pr=Sum('profit')
                        )
                        s.total_receive = agg['r'] or 0
                        s.total_pay = agg['p'] or 0
                        s.total_overtime = agg['o'] or 0
                        s.total_other_cost = agg['oc'] or 0
                        s.total_profit = agg['pr'] or 0
                        s.save()
                    except Settlement.DoesNotExist:
                        pass

        result = self.get_serializer(inquiry).data
        result['pay_price_changed'] = pay_price_changed
        result['crew_member_id'] = inquiry.crew_member.id if inquiry.crew_member else None
        return Response(result)

    @action(detail=True, methods=['post'], url_path='messages')
    def add_message(self, request, pk=None):
        """댓글 작성"""
        inquiry = self.get_object()
        content = request.data.get('content', '').strip()
        author_type = request.data.get('author_type', 'admin')
        if not content:
            return Response({'detail': '내용을 입력하세요.'}, status=status.HTTP_400_BAD_REQUEST)

        author_name = request.user.get_full_name() or request.user.username
        if author_type == 'crew':
            author_name = inquiry.crew_name

        msg = InquiryMessage.objects.create(
            inquiry=inquiry,
            author_type=author_type,
            author_name=author_name,
            content=content,
        )

        # 상태 업데이트
        inquiry.last_by = author_type
        if author_type == 'admin':
            inquiry.status = 'ANSWERED'
        else:
            inquiry.status = 'OPEN'
        inquiry.save(update_fields=['last_by', 'status', 'updated_at'])

        return Response(InquiryMessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """읽음 처리"""
        inquiry = self.get_object()
        inquiry.status = 'READ'
        inquiry.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(inquiry).data)

    @action(detail=False, methods=['get'])
    def counts(self, request):
        """카운트 (전체/미응답)"""
        qs = SettlementInquiry.objects.all()
        team_name = request.query_params.get('team_name')
        if team_name:
            qs = qs.filter(team_name=team_name)
        total = qs.count()
        open_count = qs.filter(last_by='crew').exclude(status='READ').count()
        return Response({'total': total, 'open': open_count})
