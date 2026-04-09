import re
import logging
from datetime import date
from decimal import Decimal
from collections import defaultdict

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
import openpyxl

from apps.accounts.models import Team
from apps.region.models import Region, RegionPrice
from apps.crew.models import CrewMember, OvertimeSetting
from apps.settlement.models import Settlement, SettlementDetail
from apps.partner.models import Partner
from .models import DispatchUpload, DispatchRecord
from .serializers import (
    DispatchUploadSerializer, DispatchUploadCreateSerializer,
    DispatchRecordSerializer, DispatchValidationSerializer
)

logger = logging.getLogger(__name__)

REGION_CODE_PATTERN = re.compile(r'(\d+)([A-Za-z])(\d+)')
DATE_PATTERN = re.compile(r'(\d{4})-(\d{2})-(\d{2})')


def extract_team_code(region_code):
    match = REGION_CODE_PATTERN.match(str(region_code).strip())
    return match.group(2).upper() if match else None


def split_region_codes(raw):
    if not raw:
        return []
    raw = str(raw).strip()
    if raw in ('', '-'):
        return []
    parts = [p.strip() for p in raw.split(',')]
    return [p for p in parts if p and REGION_CODE_PATTERN.match(p)]


def safe_int(val):
    if val is None:
        return 0
    s = str(val).strip()
    if s in ('', '-'):
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


class DispatchUploadViewSet(viewsets.ModelViewSet):
    queryset = DispatchUpload.objects.all()
    serializer_class = DispatchUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DispatchUploadCreateSerializer
        return DispatchUploadSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or (hasattr(user, 'is_admin') and user.is_admin()):
            return DispatchUpload.objects.all()
        # 자기 팀 또는 자기가 올린 데이터
        from django.db.models import Q
        q = Q(uploaded_by=user)
        if hasattr(user, 'team') and user.team:
            q = q | Q(team=user.team)
        return DispatchUpload.objects.filter(q)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.validated_data.get('team')

        uploaded_file = serializer.validated_data['file']
        original_filename = uploaded_file.name or ''
        dispatch_date = None
        date_match = DATE_PATTERN.search(original_filename)
        if date_match:
            try:
                dispatch_date = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            except (ValueError, TypeError):
                pass

        dispatch_upload = DispatchUpload.objects.create(
            uploaded_by=request.user,
            team=team,
            file=uploaded_file,
            original_filename=original_filename,
            dispatch_date=dispatch_date,
            note=serializer.validated_data.get('note', ''),
            status='PENDING'
        )

        try:
            self._parse_and_save_records(dispatch_upload)
            response_data = DispatchUploadSerializer(dispatch_upload).data
            response_data['detected_info'] = self._get_detected_info(dispatch_upload)
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            dispatch_upload.status = 'ERROR'
            dispatch_upload.note = f'파싱 오류: {str(e)}'
            dispatch_upload.save()
            return Response({'detail': f'파일 파싱 오류: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    def _parse_and_save_records(self, dispatch_upload):
        """배차 파일 파싱 - 권역은 그대로 유지, 박스수 분리 없음"""
        file_path = dispatch_upload.file.path
        workbook = openpyxl.load_workbook(file_path)
        worksheet = workbook.active

        total_rows = 0
        success_rows = 0
        error_rows = 0
        detected_teams = set()
        detected_regions = set()
        detected_crew = {}

        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                if not row or all(cell is None for cell in row):
                    continue

                delivery_type = str(row[0] or '').strip()
                partner_name = str(row[1] or '').strip()
                manager_name = str(row[2] or '').strip()
                sub_region_raw = str(row[3] or '').strip()
                detail_region = str(row[4] or '').strip() if len(row) > 4 else ''
                households = safe_int(row[5]) if len(row) > 5 else 0
                boxes = safe_int(row[6]) if len(row) > 6 else 0

                if sub_region_raw == '-':
                    sub_region_raw = ''
                if detail_region == '-':
                    detail_region = ''

                total_rows += 1

                if manager_name:
                    detected_crew[manager_name] = (partner_name, sub_region_raw)

                # 권역 감지
                individual_regions = split_region_codes(sub_region_raw)
                for rc in individual_regions:
                    tc = extract_team_code(rc)
                    if tc:
                        detected_teams.add(tc)
                        detected_regions.add((rc, tc))

                # 박스가 있거나 담당자가 있는 행만 저장
                if manager_name or boxes > 0:
                    DispatchRecord.objects.create(
                        upload=dispatch_upload,
                        row_num=row_idx,
                        delivery_type=delivery_type,
                        partner_name=partner_name,
                        manager_name=manager_name,
                        sub_region=sub_region_raw,
                        detail_region=detail_region,
                        households=households,
                        boxes=boxes,
                        original_boxes=boxes,
                        is_split=False,
                        split_group=0,
                        is_valid=True
                    )
                    success_rows += 1

            except Exception as e:
                total_rows += 1
                error_rows += 1
                DispatchRecord.objects.create(
                    upload=dispatch_upload, row_num=row_idx,
                    delivery_type=str(row[0] or '') if row else '',
                    partner_name=str(row[1] or '') if row and len(row) > 1 else '',
                    manager_name=str(row[2] or '') if row and len(row) > 2 else '',
                    sub_region=str(row[3] or '') if row and len(row) > 3 else '',
                    detail_region='', households=0, boxes=0, original_boxes=0,
                    is_split=False, split_group=0, is_valid=False, error_message=str(e)
                )

        # 팀 자동 생성
        team_objects = {}
        for tc in sorted(detected_teams):
            obj, _ = Team.objects.get_or_create(code=tc, defaults={'name': f'{tc}조', 'is_active': True})
            team_objects[tc] = obj

        # 권역 자동 생성
        for rc, tc in sorted(detected_regions):
            team_obj = team_objects.get(tc)
            if team_obj:
                Region.objects.get_or_create(code=rc, defaults={'team': team_obj, 'name': rc, 'is_active': True})

        # 배송원 감지
        for manager_name, (partner_name, sub_region_raw) in detected_crew.items():
            partner_obj = None
            if partner_name:
                partner_obj, _ = Partner.objects.get_or_create(name=partner_name, defaults={'is_active': True})
            team_for_crew = None
            if sub_region_raw:
                individual = split_region_codes(sub_region_raw)
                if individual:
                    tc = extract_team_code(individual[0])
                    if tc:
                        team_for_crew = team_objects.get(tc)
            if not team_for_crew and dispatch_upload.team:
                team_for_crew = dispatch_upload.team
            if team_for_crew:
                crew_obj, created = CrewMember.objects.get_or_create(
                    code=manager_name, team=team_for_crew,
                    defaults={'name': manager_name, 'phone': '', 'vehicle_number': '',
                              'partner': partner_obj, 'region': sub_region_raw, 'is_active': True, 'is_new': True}
                )
                if not created and partner_obj:
                    crew_obj.partner = partner_obj
                    crew_obj.region = sub_region_raw or crew_obj.region
                    crew_obj.save(update_fields=['partner', 'region'])

        # 팀 연결
        if not dispatch_upload.team and team_objects:
            dispatch_upload.team = list(team_objects.values())[0]

        dispatch_upload.total_rows = total_rows
        dispatch_upload.success_rows = success_rows
        dispatch_upload.error_rows = error_rows
        dispatch_upload.status = 'PENDING'
        dispatch_upload.save()

    def _get_detected_info(self, dispatch_upload):
        records = dispatch_upload.records.filter(is_valid=True)
        teams_set = set()
        regions_set = set()
        crew_set = set()

        for rec in records:
            if rec.sub_region:
                for rc in split_region_codes(rec.sub_region):
                    tc = extract_team_code(rc)
                    if tc:
                        teams_set.add(tc)
                        regions_set.add(rc)
            if rec.manager_name:
                crew_set.add(rec.manager_name)

        teams_info = []
        for tc in sorted(teams_set):
            try:
                t = Team.objects.get(code=tc)
                teams_info.append({
                    'code': tc, 'name': t.name, 'id': t.id, 'exists': True,
                    'receive_price': int(t.receive_price), 'pay_price': int(t.pay_price),
                    'default_overtime_cost': int(t.default_overtime_cost),
                    'has_price': t.receive_price > 0,
                })
            except Team.DoesNotExist:
                teams_info.append({'code': tc, 'name': f'{tc}조', 'exists': False,
                                   'receive_price': 0, 'pay_price': 0, 'default_overtime_cost': 0, 'has_price': False})

        crew_info = []
        for mn in sorted(crew_set):
            crews = CrewMember.objects.filter(code=mn)
            if crews.exists():
                c = crews.first()
                crew_info.append({'code': mn, 'name': c.name, 'id': c.id, 'is_new': c.is_new,
                                  'phone': c.phone, 'vehicle_number': c.vehicle_number, 'exists': True})
            else:
                crew_info.append({'code': mn, 'name': mn, 'is_new': True, 'phone': '', 'vehicle_number': '', 'exists': False})

        return {
            'teams': teams_info,
            'regions': list(sorted(regions_set)),
            'crew_members': crew_info,
        }

    @action(detail=True, methods=['get'])
    def detected_info(self, request, pk=None):
        return Response(self._get_detected_info(self.get_object()))

    @action(detail=False, methods=['post'])
    def reset_data(self, request):
        if not (request.user.is_staff or (hasattr(request.user, 'is_admin') and request.user.is_admin())):
            return Response({'detail': '관리자만 접근 가능합니다.'}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            SettlementDetail.objects.all().delete()
            Settlement.objects.all().delete()
            OvertimeSetting.objects.all().delete()
            DispatchRecord.objects.all().delete()
            DispatchUpload.objects.all().delete()
            CrewMember.objects.all().delete()
            RegionPrice.objects.all().delete()
            Region.objects.all().delete()
            Partner.objects.all().delete()
            Team.objects.all().delete()
        return Response({'detail': '모든 데이터가 초기화되었습니다.'})

    @action(detail=True, methods=['post'])
    def configure(self, request, pk=None):
        """팀 단가 설정 + 배송원 등록"""
        dispatch_upload = self.get_object()
        teams_data = request.data.get('teams', [])
        crew_data = request.data.get('crew', [])
        teams_count = 0
        crew_count = 0

        with transaction.atomic():
            for td in teams_data:
                team_id = td.get('id')
                if not team_id:
                    continue
                try:
                    team = Team.objects.get(id=team_id)
                    team.receive_price = Decimal(str(td.get('receive_price', 0)))
                    team.pay_price = Decimal(str(td.get('pay_price', 0)))
                    team.default_overtime_cost = Decimal(str(td.get('default_overtime_cost', 0)))
                    team.save(update_fields=['receive_price', 'pay_price', 'default_overtime_cost'])
                    teams_count += 1
                except Team.DoesNotExist:
                    continue

            for ci in crew_data:
                code = ci.get('code')
                if not code:
                    continue
                try:
                    crew = CrewMember.objects.get(code=code)
                    crew.name = ci.get('name', code)
                    crew.phone = ci.get('phone', '')
                    crew.vehicle_number = ci.get('vehicle_number', '')
                    crew.is_new = False
                    crew.save(update_fields=['name', 'phone', 'vehicle_number', 'is_new'])
                    crew_count += 1
                except CrewMember.DoesNotExist:
                    continue

        return Response({'detail': f'{teams_count}개 팀 단가, {crew_count}명 배송원 등록'})

    @action(detail=True, methods=['post'])
    def set_overtime(self, request, pk=None):
        """사람 기준 특근 설정"""
        dispatch_upload = self.get_object()
        crew_data = request.data.get('crew', [])
        count = 0

        with transaction.atomic():
            for ci in crew_data:
                name = ci.get('name')
                is_ot = ci.get('is_overtime', False)
                cost = ci.get('overtime_cost', 0)
                if not name:
                    continue
                dispatch_upload.records.filter(manager_name=name).update(is_overtime=is_ot)
                count += 1
                try:
                    crew = CrewMember.objects.get(code=name)
                    if is_ot:
                        OvertimeSetting.objects.update_or_create(
                            dispatch_upload=dispatch_upload, crew_member=crew,
                            defaults={'is_overtime': True, 'overtime_cost': Decimal(str(cost)) if cost else 0}
                        )
                    else:
                        OvertimeSetting.objects.filter(dispatch_upload=dispatch_upload, crew_member=crew).delete()
                except CrewMember.DoesNotExist:
                    pass

        return Response({'detail': f'{count}명 특근 설정'})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """정산 생성 - 팀 단가 기반"""
        dispatch_upload = self.get_object()
        note = request.data.get('note', '')

        base_date = dispatch_upload.dispatch_date or date.today()
        period_start = base_date
        period_end = base_date

        if not dispatch_upload.team:
            return Response({'detail': '팀이 설정되지 않았습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        team = dispatch_upload.team
        receive_price = team.receive_price or Decimal('0')
        pay_price = team.pay_price or Decimal('0')

        records = dispatch_upload.records.filter(is_valid=True)
        crew_records = defaultdict(list)
        skipped_crew = []

        for rec in records:
            if not rec.manager_name:
                continue
            try:
                crew = CrewMember.objects.get(code=rec.manager_name)
                if crew.is_new:
                    if rec.manager_name not in skipped_crew:
                        skipped_crew.append(rec.manager_name)
                    continue
                crew_records[rec.manager_name].append(rec)
            except CrewMember.DoesNotExist:
                if rec.manager_name not in skipped_crew:
                    skipped_crew.append(rec.manager_name)

        with transaction.atomic():
            settlement, created = Settlement.objects.get_or_create(
                team=team, period_start=period_start, period_end=period_end,
                defaults={'status': 'DRAFT', 'note': note}
            )
            if not created:
                settlement.details.all().delete()

            total_receive = Decimal('0')
            total_pay = Decimal('0')
            total_overtime = Decimal('0')
            crew_details = []

            for crew_code, recs in crew_records.items():
                try:
                    crew = CrewMember.objects.get(code=crew_code)
                except CrewMember.DoesNotExist:
                    continue

                # 특근 조회
                ot_setting = OvertimeSetting.objects.filter(
                    dispatch_upload=dispatch_upload, crew_member=crew, is_overtime=True
                ).first()
                overtime_cost = Decimal(str(ot_setting.overtime_cost)) if ot_setting else Decimal('0')

                total_boxes = sum(r.boxes for r in recs)
                r_amount = receive_price * Decimal(str(total_boxes))
                p_amount = pay_price * Decimal(str(total_boxes))
                profit = r_amount - p_amount - overtime_cost

                # 권역별로 분리해서 저장
                region_map = defaultdict(int)
                for r in recs:
                    regions = split_region_codes(r.sub_region)
                    if regions:
                        per = r.boxes // len(regions)
                        rem = r.boxes % len(regions)
                        for i, rc in enumerate(regions):
                            region_map[rc] += per + (1 if i < rem else 0)
                    elif r.sub_region:
                        region_map[r.sub_region] += r.boxes

                crew_regions = []
                for rc, boxes in region_map.items():
                    ra = receive_price * Decimal(str(boxes))
                    pa = pay_price * Decimal(str(boxes))
                    crew_regions.append({'region': rc, 'boxes': boxes,
                                         'receive_amount': int(ra), 'pay_amount': int(pa),
                                         'overtime_cost': 0, 'profit': int(ra - pa)})

                # 특근비는 첫 권역에 귀속
                if crew_regions and overtime_cost > 0:
                    crew_regions[0]['overtime_cost'] = int(overtime_cost)
                    crew_regions[0]['profit'] = int(Decimal(str(crew_regions[0]['receive_amount'])) -
                                                     Decimal(str(crew_regions[0]['pay_amount'])) - overtime_cost)

                # SettlementDetail 저장
                for cr in crew_regions:
                    SettlementDetail.objects.create(
                        settlement=settlement, crew_member=crew,
                        region=cr['region'], delivery_type='SAME_DAY',
                        boxes=cr['boxes'], receive_amount=cr['receive_amount'],
                        pay_amount=cr['pay_amount'], overtime_cost=cr['overtime_cost'],
                        profit=cr['profit'],
                    )

                total_receive += r_amount
                total_pay += p_amount
                total_overtime += overtime_cost

                crew_details.append({
                    'crew_code': crew_code, 'crew_name': crew.name,
                    'regions': crew_regions, 'total_boxes': total_boxes,
                    'total_receive': int(r_amount), 'total_pay': int(p_amount),
                    'total_overtime': int(overtime_cost), 'total_profit': int(profit),
                })

            settlement.total_receive = total_receive
            settlement.total_pay = total_pay
            settlement.total_overtime = total_overtime
            settlement.total_profit = total_receive - total_pay - total_overtime
            settlement.status = 'CONFIRMED'
            settlement.save()
            dispatch_upload.status = 'CONFIRMED'
            dispatch_upload.save()

        return Response({
            'detail': '정산 생성 완료',
            'settlement': {
                'id': settlement.id,
                'team': team.name,
                'period_start': str(period_start), 'period_end': str(period_end),
                'total_receive': int(settlement.total_receive),
                'total_pay': int(settlement.total_pay),
                'total_overtime': int(settlement.total_overtime),
                'total_profit': int(settlement.total_profit),
                'status': settlement.status,
            },
            'crew_details': crew_details,
            'skipped_crew': skipped_crew,
        }, status=status.HTTP_201_CREATED)


class DispatchRecordViewSet(viewsets.ModelViewSet):
    serializer_class = DispatchRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        upload_id = self.request.query_params.get('upload_id')
        if upload_id:
            try:
                du = DispatchUpload.objects.get(id=upload_id)
                user = self.request.user
                if not user.is_staff and (not hasattr(user, 'is_admin') or not user.is_admin()):
                    # 자기 팀이거나 자기가 올린 것만
                    is_own_team = hasattr(user, 'team') and user.team and du.team == user.team
                    is_own_upload = du.uploaded_by == user
                    if not is_own_team and not is_own_upload:
                        return DispatchRecord.objects.none()
                return du.records.all()
            except DispatchUpload.DoesNotExist:
                return DispatchRecord.objects.none()
        return DispatchRecord.objects.none()

    def list(self, request, *args, **kwargs):
        if not request.query_params.get('upload_id'):
            return Response({'detail': 'upload_id 필수'}, status=status.HTTP_400_BAD_REQUEST)
        return super().list(request, *args, **kwargs)
