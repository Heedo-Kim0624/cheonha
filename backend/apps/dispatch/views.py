import re
import logging
import csv
import math
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from datetime import date, time, timedelta
from decimal import Decimal
from collections import defaultdict

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Sum, Case, When, IntegerField
from django.http import FileResponse, HttpResponse
from django.utils.dateparse import parse_date
import openpyxl

from apps.accounts.models import Team
from apps.accounts.shipper_utils import (
    FILE_UPLOAD_SHIPPERS,
    TEXT_UPLOAD_SHIPPERS,
    normalize_shipper_code,
    shipper_is_enabled,
)
from apps.common.company_scope import get_company_app_from_request
from apps.region.models import Region, RegionPrice
from apps.crew.models import CrewMember, OvertimeSetting
from apps.settlement.models import Settlement, SettlementDetail
from apps.partner.models import Partner
from .models import DispatchUpload, DispatchRecord
from .date_utils import date_iso, to_delivery_date, to_work_date
from .settlement_services import (
    build_daily_yongcha_round_counts,
    build_crew_settlement_payload,
    is_effective_yongcha,
)
from .operation_report_services import (
    build_operation_report_amount_lookup,
    build_operation_report_summary,
    write_operation_report_csv,
)
from .text_parsers import parse_coupang_dispatch_text
from .serializers import (
    DispatchUploadSerializer, DispatchUploadSummarySerializer, DispatchUploadCreateSerializer,
    DispatchRecordSerializer, DispatchValidationSerializer
)

logger = logging.getLogger(__name__)

REGION_CODE_PATTERN = re.compile(r'(\d+)([A-Za-z])(\d+)')
DATE_PATTERN = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
YONGCHA_SUFFIX_PATTERN = re.compile(r'\s*[vV]\s*$')
TIME_COLON_PATTERN = re.compile(r'(?<!\d)([01]?\d|2[0-3])\s*:\s*([0-5]\d)(?!\d)')
TIME_HOUR_PATTERN = re.compile(r'(?<!\d)([01]?\d|2[0-3])\s*시(?:\s*([0-5]?\d)\s*분)?')
TIME_SEPARATED_PATTERN = re.compile(r'(?<!\d)([01]?\d|2[0-3])[_-]([0-5]\d)(?:[_-][0-5]\d)?(?!\d)')
ROUND_PATTERN = re.compile('(\\d+)\\s*(?:\ucc28|\ud68c\ucc28)')


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


def clean_crew_name(name):
    """이름에서 선행 알파벳(ZD 등) 제거"""
    if not name:
        return name
    return re.sub(r'^[A-Za-z]+', '', name.strip())


def normalize_crew_name(raw_name):
    name = clean_crew_name(str(raw_name or '').strip()) or ''
    is_yongcha = bool(name and YONGCHA_SUFFIX_PATTERN.search(name))
    if is_yongcha:
        name = YONGCHA_SUFFIX_PATTERN.sub('', name).strip()
    return name, is_yongcha


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


def parse_dispatch_filename_info(filename):
    """
    파일명에서 날짜/시간/n차를 추출한다.
    15:00 이전 배차표는 전날 근무로 반영한다.
    예: 2월 25일 02시 -> 근무일 2월 24일, 2월 24일 18시 -> 근무일 2월 24일.
    """
    text = str(filename or '')
    source_date = None
    date_span = None

    date_patterns = [
        re.compile(r'(\d{4})[-._년\s]*(\d{1,2})[-._월\s]*(\d{1,2})(?:일)?'),
        re.compile(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
        re.compile(r'(?<!\d)(\d{1,2})[-._](\d{1,2})(?!\d)'),
    ]

    for idx, pattern in enumerate(date_patterns):
        match = pattern.search(text)
        if not match:
            continue
        try:
            if idx == 0:
                year, month, day = map(int, match.groups())
            else:
                today = date.today()
                year = today.year
                month, day = map(int, match.groups())
                # 연초에 전년도 12월 파일을 처리하는 경우를 보정한다.
                if today.month == 1 and month == 12:
                    year -= 1
            source_date = date(year, month, day)
            date_span = match.span()
            break
        except (TypeError, ValueError):
            source_date = None

    dispatch_time = None
    time_match = TIME_COLON_PATTERN.search(text)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        try:
            dispatch_time = time(hour, minute)
        except ValueError:
            dispatch_time = None
    else:
        time_match = TIME_HOUR_PATTERN.search(text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            try:
                dispatch_time = time(hour, minute)
            except ValueError:
                dispatch_time = None
        else:
            separated_matches = [
                m for m in TIME_SEPARATED_PATTERN.finditer(text)
                if not (date_span and m.start() >= date_span[0] and m.end() <= date_span[1])
            ]
            if separated_matches:
                time_match = separated_matches[-1]
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                try:
                    dispatch_time = time(hour, minute)
                except ValueError:
                    dispatch_time = None

    round_no = None
    round_match = ROUND_PATTERN.search(text)
    if round_match:
        round_no = safe_int(round_match.group(1)) or None

    work_date = source_date
    if source_date and dispatch_time and dispatch_time < time(15, 0):
        work_date = source_date - timedelta(days=1)

    return {
        'source_date': source_date,
        'work_date': work_date,
        'dispatch_date': to_delivery_date(work_date),
        'dispatch_time': dispatch_time,
        'round_no': round_no,
    }


def _parse_report_date(value, fallback):
    parsed = parse_date(str(value or ''))
    return parsed or fallback


def _format_ratio(value):
    return round(float(value), 2)


class DispatchUploadViewSet(viewsets.ModelViewSet):
    queryset = DispatchUpload.objects.all()
    serializer_class = DispatchUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DispatchUploadCreateSerializer
        if self.action == 'list' and str(self.request.query_params.get('summary') or '').lower() in ('1', 'true', 'yes'):
            return DispatchUploadSummarySerializer
        return DispatchUploadSerializer

    def _validate_shipper_code(self, request, value=None):
        company_app = get_company_app_from_request(request)
        shipper_code = normalize_shipper_code(value or request.data.get('shipper_code') or request.query_params.get('shipper_code'))
        if not shipper_is_enabled(company_app, shipper_code):
            raise ValueError('현재 회사에서 사용할 수 없는 화주사입니다.')
        return shipper_code

    def _shipper_filter(self, request):
        raw = str(request.query_params.get('shipper_code') or '').strip().lower()
        if not raw:
            return None
        return normalize_shipper_code(raw)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or (hasattr(user, 'is_admin') and user.is_admin()):
            queryset = DispatchUpload.objects.filter(team__company_app=get_company_app_from_request(self.request))
            if self.action == 'list':
                queryset = queryset.select_related('team', 'uploaded_by').defer('raw_text')
            return queryset
        # 자기 팀 또는 자기가 올린 데이터
        from django.db.models import Q
        q = Q(uploaded_by=user)
        if hasattr(user, 'team') and user.team:
            q = q | Q(team=user.team)
        queryset = DispatchUpload.objects.filter(q)
        if self.action == 'list':
            queryset = queryset.select_related('team', 'uploaded_by').defer('raw_text')
        return queryset

    def destroy(self, request, *args, **kwargs):
        """업로드 삭제 - 연관 정산 detail 삭제, 빈 settlement 정리"""
        dispatch_upload = self.get_object()
        with transaction.atomic():
            # 이 upload의 settlement detail 삭제
            SettlementDetail.objects.filter(dispatch_upload=dispatch_upload).delete()

            # detail이 0개인 settlement 삭제, 나머지는 합계 재계산
            from django.db.models import Sum
            for s in Settlement.objects.all():
                if s.details.count() == 0:
                    s.delete()
                else:
                    agg = s.details.aggregate(r=Sum('receive_amount'), p=Sum('pay_amount'), o=Sum('overtime_cost'), pr=Sum('profit'))
                    s.total_receive = agg['r'] or 0
                    s.total_pay = agg['p'] or 0
                    s.total_overtime = agg['o'] or 0
                    s.total_profit = agg['pr'] or 0
                    s.save()

            # OvertimeSetting 삭제
            OvertimeSetting.objects.filter(dispatch_upload=dispatch_upload).delete()
            # 업로드 + 레코드 삭제
            dispatch_upload.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = serializer.validated_data.get('team')
        try:
            shipper_code = self._validate_shipper_code(request, serializer.validated_data.get('shipper_code'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if shipper_code not in FILE_UPLOAD_SHIPPERS:
            return Response({'detail': '파일 업로드는 현재 컬리 화주사에서만 지원합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data['file']
        original_filename = uploaded_file.name or ''
        filename_info = parse_dispatch_filename_info(original_filename)

        dispatch_upload = DispatchUpload.objects.create(
            uploaded_by=request.user,
            team=team,
            file=uploaded_file,
            original_filename=original_filename,
            shipper_code=shipper_code,
            input_type='FILE',
            dispatch_date=filename_info['dispatch_date'],
            source_date=filename_info['source_date'],
            dispatch_time=filename_info['dispatch_time'],
            round_no=filename_info['round_no'],
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
                manager_name, is_yongcha = normalize_crew_name(row[2])
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
                    current = detected_crew.get(manager_name)
                    if current:
                        current['is_yongcha'] = current['is_yongcha'] or is_yongcha
                        if sub_region_raw:
                            current['sub_region_raw'] = sub_region_raw
                        if partner_name:
                            current['partner_name'] = partner_name
                    else:
                        detected_crew[manager_name] = {
                            'partner_name': partner_name,
                            'sub_region_raw': sub_region_raw,
                            'is_yongcha': is_yongcha,
                        }

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
                        is_yongcha=is_yongcha,
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
            obj, _ = Team.objects.get_or_create(
                code=tc,
                company_app=get_company_app_from_request(self.request),
                defaults={'name': f'{tc}조', 'is_active': True},
            )
            team_objects[tc] = obj

        # 권역 자동 생성
        for rc, tc in sorted(detected_regions):
            team_obj = team_objects.get(tc)
            if team_obj:
                Region.objects.get_or_create(code=rc, defaults={'team': team_obj, 'name': rc, 'is_active': True})

        # 배송원 감지
        for manager_name, crew_info in detected_crew.items():
            partner_name = crew_info.get('partner_name', '')
            sub_region_raw = crew_info.get('sub_region_raw', '')
            is_yongcha = crew_info.get('is_yongcha', False)
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
                              'partner': partner_obj, 'region': sub_region_raw, 'is_active': True,
                              'is_new': not is_yongcha, 'is_yongcha': is_yongcha}
                )
                update_fields = []
                if not created and partner_obj:
                    crew_obj.partner = partner_obj
                    update_fields.append('partner')
                if not created and sub_region_raw:
                    crew_obj.region = sub_region_raw
                    update_fields.append('region')
                if not created and is_yongcha and not crew_obj.is_yongcha:
                    crew_obj.is_yongcha = True
                    crew_obj.is_new = False
                    update_fields.extend(['is_yongcha', 'is_new'])
                if update_fields:
                    crew_obj.save(update_fields=sorted(set(update_fields)))

        # 팀 연결
        if not dispatch_upload.team and team_objects:
            dispatch_upload.team = list(team_objects.values())[0]

        dispatch_upload.total_rows = total_rows
        dispatch_upload.success_rows = success_rows
        dispatch_upload.error_rows = error_rows
        dispatch_upload.status = 'PENDING'
        dispatch_upload.save()
        self._update_mor_summary(dispatch_upload)

    def _update_mor_summary(self, dispatch_upload):
        """MOR용 회차별 총 물량/정규·용차 인원 집계"""
        records = dispatch_upload.records.filter(is_valid=True, boxes__gt=0)
        total_boxes = sum(int(r.boxes or 0) for r in records)
        crew_names = {
            str(r.manager_name or '').strip()
            for r in records
            if str(r.manager_name or '').strip()
        }
        regular_count = 0
        yongcha_count = 0

        for name in crew_names:
            rec_yongcha = records.filter(manager_name=name, is_yongcha=True).exists()
            crew = None
            if dispatch_upload.team:
                crew = CrewMember.objects.filter(code=name, team=dispatch_upload.team).first()
            if not crew:
                crew = CrewMember.objects.filter(code=name).first()
            is_yongcha = is_effective_yongcha(
                crew,
                round_no=dispatch_upload.round_no,
                explicit_yongcha=rec_yongcha,
            )
            if is_yongcha:
                yongcha_count += 1
            else:
                regular_count += 1

        dispatch_upload.mor_total_boxes = total_boxes
        dispatch_upload.mor_regular_crew_count = regular_count
        dispatch_upload.mor_yongcha_crew_count = yongcha_count
        dispatch_upload.save(update_fields=[
            'mor_total_boxes', 'mor_regular_crew_count',
            'mor_yongcha_crew_count', 'updated_at',
        ])

    def _get_detected_info(self, dispatch_upload):
        records = dispatch_upload.records.filter(is_valid=True)
        teams_set = set()
        regions_set = set()
        crew_set = set()
        crew_yongcha_map = {}

        for rec in records:
            if rec.sub_region:
                for rc in split_region_codes(rec.sub_region):
                    tc = extract_team_code(rc)
                    if tc:
                        teams_set.add(tc)
                        regions_set.add(rc)
            if rec.manager_name:
                crew_set.add(rec.manager_name)
                crew_yongcha_map[rec.manager_name] = (
                    crew_yongcha_map.get(rec.manager_name, False) or rec.is_yongcha
                )

        teams_info = []
        for tc in sorted(teams_set):
            try:
                t = Team.objects.get(code=tc, company_app=get_company_app_from_request(self.request))
                teams_info.append({
                    'code': tc, 'name': t.name, 'id': t.id, 'exists': True,
                    'receive_price': int(t.receive_price), 'pay_price': int(t.pay_price),
                    'default_overtime_cost': int(t.default_overtime_cost),
                    'has_price': t.receive_price > 0,
                })
            except Team.DoesNotExist:
                teams_info.append({'code': tc, 'name': f'{tc}조', 'exists': False,
                                   'receive_price': 0, 'pay_price': 0, 'default_overtime_cost': 0, 'has_price': False})

        if dispatch_upload.team and not any(item.get('id') == dispatch_upload.team_id for item in teams_info):
            t = dispatch_upload.team
            teams_info.insert(0, {
                'code': t.code, 'name': t.name, 'id': t.id, 'exists': True,
                'receive_price': int(t.receive_price), 'pay_price': int(t.pay_price),
                'default_overtime_cost': int(t.default_overtime_cost),
                'has_price': t.receive_price > 0,
            })

        crew_info = []
        upload_team = dispatch_upload.team
        for mn in sorted(crew_set):
            crews = CrewMember.objects.filter(code=mn, team=upload_team) if upload_team else CrewMember.objects.filter(code=mn)
            if crews.exists():
                c = crews.first()
                crew_info.append({'code': mn, 'name': c.name, 'id': c.id, 'is_new': c.is_new,
                                  'is_yongcha': c.is_yongcha,
                                  'pay_price': int(c.pay_price or 0),
                                  'yongcha_pay_price': int(c.yongcha_pay_price or 3000),
                                  'round_1_is_yongcha': bool(c.round_1_is_yongcha),
                                  'round_2_is_yongcha': bool(c.round_2_is_yongcha),
                                  'round_3_is_yongcha': bool(c.round_3_is_yongcha),
                                  'phone': c.phone, 'vehicle_number': c.vehicle_number, 'exists': True})
            else:
                is_yongcha = crew_yongcha_map.get(mn, False)
                crew_info.append({'code': mn, 'name': mn, 'is_new': not is_yongcha,
                                  'is_yongcha': is_yongcha, 'pay_price': 0,
                                  'yongcha_pay_price': 3000,
                                  'round_1_is_yongcha': False,
                                  'round_2_is_yongcha': False,
                                  'round_3_is_yongcha': False,
                                  'phone': '', 'vehicle_number': '', 'exists': False})

        return {
            'teams': teams_info,
            'regions': list(sorted(regions_set)),
            'crew_members': crew_info,
        }

    @action(detail=True, methods=['get'])
    def detected_info(self, request, pk=None):
        return Response(self._get_detected_info(self.get_object()))

    def _validate_text_upload_payload(self, request):
        try:
            shipper_code = self._validate_shipper_code(request, request.data.get('shipper_code'))
        except ValueError as exc:
            return None, Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if shipper_code not in TEXT_UPLOAD_SHIPPERS:
            return None, Response({'detail': '현재 텍스트 업로드는 쿠팡 화주사만 지원합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        raw_text = str(request.data.get('raw_text') or '').strip()
        if not raw_text:
            return None, Response({'detail': '붙여넣기 텍스트를 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        date_basis = str(request.data.get('date_basis') or 'delivery').strip().lower()
        if date_basis not in ('delivery', 'work'):
            return None, Response({'detail': '날짜 기준은 배송일 또는 출근일이어야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        input_date = parse_date(str(request.data.get('input_date') or request.data.get('dispatch_date') or ''))
        if not input_date:
            return None, Response({'detail': '날짜를 선택해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        dispatch_date = input_date + timedelta(days=1) if date_basis == 'work' else input_date

        round_code = str(request.data.get('round_code') or '').strip().upper()
        round_code_map = {'W1': 1, 'W2': 2, 'D1': 1, 'D2': 2, 'D3': 3}
        if round_code:
            round_no = round_code_map.get(round_code, 0)
        else:
            try:
                round_no = int(request.data.get('round_no') or 0)
            except (TypeError, ValueError):
                round_no = 0
        if round_no not in (1, 2, 3):
            return None, Response({'detail': '회차는 W1, W2, D1, D2, D3 중 하나여야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        team_id = request.data.get('team_id') or request.data.get('team')
        if not team_id:
            return None, Response({'detail': '조를 선택해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            team = Team.objects.get(
                id=team_id,
                company_app=get_company_app_from_request(request),
                shipper_code=shipper_code,
                is_active=True,
            )
        except Team.DoesNotExist:
            return None, Response({'detail': '선택한 화주사에서 사용할 수 없는 조입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        parsed = parse_coupang_dispatch_text(raw_text)
        payload = {
            'shipper_code': shipper_code,
            'raw_text': raw_text,
            'input_date': input_date,
            'date_basis': date_basis,
            'dispatch_date': dispatch_date,
            'round_no': round_no,
            'round_code': round_code or f'{round_no}R',
            'team': team,
            'parsed': parsed,
        }
        return payload, None

    @action(detail=False, methods=['post'], url_path='text-preview')
    def text_preview(self, request):
        payload, error = self._validate_text_upload_payload(request)
        if error:
            return error
        parsed = payload['parsed']
        return Response({
            'shipper_code': payload['shipper_code'],
            'team_id': payload['team'].id,
            'team_name': payload['team'].name,
            'input_date': date_iso(payload['input_date']),
            'date_basis': payload['date_basis'],
            'dispatch_date': date_iso(payload['dispatch_date']),
            'round_no': payload['round_no'],
            'round_code': payload['round_code'],
            'rows': parsed.rows,
            'total_boxes': parsed.total_boxes,
            'total_households': parsed.total_households,
            'errors': parsed.errors,
        })

    @action(detail=False, methods=['post'], url_path='text')
    def text_upload(self, request):
        payload, error = self._validate_text_upload_payload(request)
        if error:
            return error
        parsed = payload['parsed']
        if parsed.errors:
            return Response({
                'detail': '파싱 오류를 먼저 수정해 주세요.',
                'errors': parsed.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        if not parsed.rows:
            return Response({'detail': '저장할 데이터 행이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        team = payload['team']
        dispatch_date = payload['dispatch_date']
        raw_text = payload['raw_text']
        shipper_code = payload['shipper_code']
        round_no = payload['round_no']
        round_code = payload['round_code']
        input_date = payload['input_date']
        date_basis = payload['date_basis']
        filename = f'{shipper_code}_{team.code}_{dispatch_date.isoformat()}_{round_code}.txt'
        file_content = ContentFile(raw_text.encode('utf-8'), name=filename)

        with transaction.atomic():
            dispatch_upload = DispatchUpload.objects.create(
                uploaded_by=request.user,
                team=team,
                file=file_content,
                original_filename=filename,
                shipper_code=shipper_code,
                input_type='TEXT',
                raw_text=raw_text,
                dispatch_date=dispatch_date,
                source_date=input_date,
                round_no=round_no,
                note=f'쿠팡 회차 {round_code} / 날짜기준 {"출근일" if date_basis == "work" else "배송일"}',
                status='PENDING',
            )

            for index, row in enumerate(parsed.rows, start=1):
                DispatchRecord.objects.create(
                    upload=dispatch_upload,
                    row_num=index,
                    delivery_type=row['delivery_type'],
                    partner_name=row['partner_name'],
                    manager_name=row['manager_name'],
                    sub_region=row['sub_region'],
                    detail_region=row['detail_region'],
                    households=row['households'],
                    boxes=row['boxes'],
                    original_boxes=row['boxes'],
                    is_split=False,
                    split_group=0,
                    is_yongcha=False,
                    is_valid=True,
                )
                CrewMember.objects.get_or_create(
                    code=row['manager_name'],
                    team=team,
                    defaults={
                        'name': row['manager_name'],
                        'phone': '',
                        'vehicle_number': '',
                        'region': row['sub_region'],
                        'is_active': True,
                        'is_new': True,
                        'is_yongcha': False,
                    },
                )

            dispatch_upload.total_rows = len(parsed.rows)
            dispatch_upload.success_rows = len(parsed.rows)
            dispatch_upload.error_rows = 0
            dispatch_upload.save(update_fields=['total_rows', 'success_rows', 'error_rows', 'updated_at'])
            self._update_mor_summary(dispatch_upload)

        response_data = DispatchUploadSerializer(dispatch_upload).data
        response_data['detected_info'] = self._get_detected_info(dispatch_upload)
        response_data['records'] = DispatchRecordSerializer(dispatch_upload.records.all(), many=True).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='download-file')
    def download_file(self, request, pk=None):
        dispatch_upload = self.get_object()
        if not dispatch_upload.file:
            return Response({'detail': '저장된 원본 배차표 파일이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        storage_path = dispatch_upload.file.name
        if not default_storage.exists(storage_path):
            return Response({'detail': '서버에서 원본 배차표 파일을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        filename = dispatch_upload.original_filename or Path(storage_path).name or f'dispatch_{dispatch_upload.pk}.xlsx'
        response = FileResponse(
            default_storage.open(storage_path, 'rb'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @action(detail=False, methods=['get'])
    def check_date(self, request):
        """같은 날짜에 이미 업로드된 이력 조회"""
        dispatch_date = request.query_params.get('date')
        if not dispatch_date:
            return Response([])
        target_date = parse_date(str(dispatch_date))
        if not target_date:
            return Response([])
        existing = self.get_queryset().filter(status='CONFIRMED').filter(
            Q(dispatch_date=target_date) | Q(source_date=target_date)
        ).order_by('-upload_date')
        return Response([
            {
                'id': item.id,
                'original_filename': item.original_filename,
                'upload_date': item.upload_date,
                'total_rows': item.total_rows,
                'work_date': date_iso(to_work_date(item.dispatch_date)),
                'delivery_date': date_iso(item.dispatch_date),
                'dispatch_date': date_iso(item.dispatch_date),
            }
            for item in existing
        ])

    def _operation_report_uploads(self, request, include_settlement_details=True):
        today = date.today()
        end_date = _parse_report_date(request.query_params.get('end'), today)
        start_date = _parse_report_date(request.query_params.get('start'), end_date)
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        max_start = end_date - timedelta(days=370)
        if start_date < max_start:
            start_date = max_start

        qs = self.get_queryset().exclude(status='ERROR').filter(
            dispatch_date__gte=start_date,
            dispatch_date__lte=end_date,
        ).select_related('team').prefetch_related('records')
        shipper_code = self._shipper_filter(request)
        if shipper_code:
            qs = qs.filter(shipper_code=shipper_code)
        if include_settlement_details:
            qs = qs.prefetch_related('settlement_details__crew_member')

        team_filter = str(request.query_params.get('team') or '').strip()
        if team_filter:
            from django.db.models import Q
            team_q = Q(team__name=team_filter) | Q(team__code=team_filter)
            if team_filter.isdigit():
                team_q = team_q | Q(team_id=int(team_filter))
            qs = qs.filter(team_q)

        return list(qs), start_date, end_date

    def _operation_report_upload_values(self, request):
        today = date.today()
        end_date = _parse_report_date(request.query_params.get('end'), today)
        start_date = _parse_report_date(request.query_params.get('start'), end_date)
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        max_start = end_date - timedelta(days=370)
        if start_date < max_start:
            start_date = max_start

        qs = self.get_queryset().exclude(status='ERROR').filter(
            dispatch_date__gte=start_date,
            dispatch_date__lte=end_date,
        )
        shipper_code = self._shipper_filter(request)
        if shipper_code:
            qs = qs.filter(shipper_code=shipper_code)

        team_filter = str(request.query_params.get('team') or '').strip()
        if team_filter:
            team_q = Q(team__name=team_filter) | Q(team__code=team_filter)
            if team_filter.isdigit():
                team_q = team_q | Q(team_id=int(team_filter))
            qs = qs.filter(team_q)

        rows = qs.values(
            'id',
            'dispatch_date',
            'round_no',
            'team_id',
            'team__code',
            'team__name',
        ).order_by('dispatch_date', 'team__code', 'team__name', 'id')
        return list(rows), start_date, end_date

    def _operation_report_metric(self, request):
        metric = str(request.query_params.get('metric') or 'boxes').strip().lower()
        if metric in ('household', 'households', 'families', 'family'):
            return 'households', '가구수', '가구'
        return 'boxes', '박스수', '박스'

    def _operation_report_cache_key(self, request, namespace):
        user = request.user
        payload = {
            'namespace': namespace,
            'start': request.query_params.get('start') or '',
            'end': request.query_params.get('end') or '',
            'team': request.query_params.get('team') or '',
            'shipper_code': request.query_params.get('shipper_code') or '',
            'metric': request.query_params.get('metric') or '',
            'company_app': get_company_app_from_request(request),
            'user_id': getattr(user, 'id', None),
            'user_team_id': getattr(user, 'team_id', None),
            'is_staff': bool(getattr(user, 'is_staff', False)),
            'is_admin': bool(hasattr(user, 'is_admin') and user.is_admin()),
        }
        digest = hashlib.md5(
            json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
        ).hexdigest()
        return f'operation-report:{namespace}:{digest}'

    def _operation_report_static_cache_key(self, request, namespace, payload):
        user = request.user
        payload = {
            **payload,
            'namespace': namespace,
            'company_app': get_company_app_from_request(request),
            'user_id': getattr(user, 'id', None),
            'user_team_id': getattr(user, 'team_id', None),
            'is_staff': bool(getattr(user, 'is_staff', False)),
            'is_admin': bool(hasattr(user, 'is_admin') and user.is_admin()),
        }
        digest = hashlib.md5(
            json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
        ).hexdigest()
        return f'operation-report:{namespace}:{digest}'

    def _cached_operation_report_rows(self, request):
        cache_key = self._operation_report_cache_key(request, 'rows')
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        result = self._build_operation_report_rows_fast(request)
        cache.set(cache_key, result, 90)
        return result

    def _operation_report_amounts(self, request, start_date, end_date, team_ids):
        return build_operation_report_amount_lookup(
            start_date=start_date,
            end_date=end_date,
            team_ids=team_ids,
            user=request.user,
            company_app=get_company_app_from_request(request),
            shipper_code=self._shipper_filter(request),
        )

    def _build_operation_report_rows_fast(self, request):
        metric, metric_label, metric_unit = self._operation_report_metric(request)
        metric_field = 'households' if metric == 'households' else 'boxes'
        uploads, start_date, end_date = self._operation_report_upload_values(request)
        upload_ids = [row['id'] for row in uploads]
        if not upload_ids:
            return [], start_date, end_date, metric, metric_label, metric_unit

        yongcha_count_expr = Sum(
            Case(
                When(is_yongcha=True, then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        record_totals = {
            row['upload_id']: row
            for row in DispatchRecord.objects.filter(
                upload_id__in=upload_ids,
                is_valid=True,
            ).values('upload_id').annotate(
                boxes=Sum('boxes'),
                households=Sum('households'),
            )
        }
        record_rows = list(
            DispatchRecord.objects.filter(
                upload_id__in=upload_ids,
                is_valid=True,
            ).values(
                'upload_id',
                'manager_name',
            ).annotate(
                boxes=Sum('boxes'),
                households=Sum('households'),
                yongcha_count=yongcha_count_expr,
            )
        )
        upload_by_id = {row['id']: row for row in uploads}
        records_by_upload = defaultdict(list)
        crew_codes_by_team = defaultdict(set)
        for record in record_rows:
            upload = upload_by_id.get(record['upload_id'])
            name = str(record.get('manager_name') or '').strip()
            records_by_upload[record['upload_id']].append(record)
            if upload and upload.get('team_id') and name:
                crew_codes_by_team[upload['team_id']].add(name)

        crew_lookup = {}
        if crew_codes_by_team:
            team_ids = list(crew_codes_by_team.keys())
            all_codes = set()
            for codes in crew_codes_by_team.values():
                all_codes.update(codes)
            for crew in CrewMember.objects.filter(team_id__in=team_ids, code__in=all_codes):
                crew_lookup[(crew.team_id, crew.code)] = crew

        detail_rows = list(
            SettlementDetail.objects.filter(
                dispatch_upload_id__in=upload_ids,
                crew_member_id__isnull=False,
            ).values(
                'dispatch_upload_id',
                'crew_member_id',
            ).annotate(
                boxes=Sum('boxes'),
                yongcha_count=yongcha_count_expr,
            )
        )
        detail_crew_ids = {
            row['crew_member_id']
            for row in detail_rows
            if row.get('crew_member_id')
        }
        detail_crew_lookup = {
            crew.id: crew
            for crew in CrewMember.objects.filter(id__in=detail_crew_ids)
        } if detail_crew_ids else {}
        details_by_upload = defaultdict(list)
        for detail in detail_rows:
            details_by_upload[detail['dispatch_upload_id']].append(detail)

        weekday_labels = ['월', '화', '수', '목', '금', '토', '일']

        def empty_round():
            return {
                'volume': 0,
                'manager_names': set(),
                'yongcha_names': set(),
                'volume_by_name': defaultdict(int),
            }

        def empty_row(upload):
            delivery_date = upload['dispatch_date']
            return {
                'work_date': delivery_date,
                'delivery_date': delivery_date,
                'weekday': weekday_labels[delivery_date.weekday()],
                'team_id': upload['team_id'],
                'team_code': upload.get('team__code') or '',
                'team_name': upload.get('team__name') or '',
                'actual_total_boxes': 0,
                'boxes_per_household_boxes': 0,
                'boxes_per_household_households': 0,
                'rounds': {1: empty_round(), 2: empty_round(), 3: empty_round()},
            }

        rows_by_key = {}
        for upload in uploads:
            if not upload['dispatch_date'] or not upload['team_id']:
                continue
            upload_id = upload['id']
            delivery_date = upload['dispatch_date']
            key = (delivery_date.isoformat(), upload['team_id'])
            row = rows_by_key.setdefault(key, empty_row(upload))
            settlement_details = details_by_upload.get(upload_id, [])
            valid_records = records_by_upload.get(upload_id, [])
            record_total = record_totals.get(upload_id, {})
            use_settlement_details = metric == 'boxes' and settlement_details
            upload_volume = (
                sum(safe_int(detail.get('boxes')) for detail in settlement_details)
                if use_settlement_details
                else safe_int(record_total.get(metric_field))
            )
            ratio_boxes = (
                sum(safe_int(detail.get('boxes')) for detail in settlement_details)
                if settlement_details
                else safe_int(record_total.get('boxes'))
            )
            ratio_households = safe_int(record_total.get('households'))
            row['actual_total_boxes'] += upload_volume
            row['boxes_per_household_boxes'] += ratio_boxes
            row['boxes_per_household_households'] += ratio_households

            round_no = upload['round_no'] if upload['round_no'] in (1, 2, 3) else None
            if not round_no:
                continue

            round_data = row['rounds'][round_no]
            round_data['volume'] += upload_volume

            if use_settlement_details:
                for detail in settlement_details:
                    crew = detail_crew_lookup.get(detail.get('crew_member_id'))
                    name = str(crew.code or crew.name or '').strip() if crew else ''
                    if not name:
                        continue
                    name_volume = safe_int(detail.get('boxes'))
                    round_data['volume_by_name'][name] += name_volume

                    detail_is_yongcha = safe_int(detail.get('yongcha_count')) > 0
                    crew_is_yongcha = is_effective_yongcha(
                        crew,
                        round_no=upload['round_no'],
                        explicit_yongcha=detail_is_yongcha,
                    )
                    if detail_is_yongcha or crew_is_yongcha:
                        round_data['yongcha_names'].add(name)
                        round_data['manager_names'].discard(name)
                    elif name not in round_data['yongcha_names']:
                        round_data['manager_names'].add(name)
            else:
                for record in valid_records:
                    name = str(record.get('manager_name') or '').strip()
                    if not name:
                        continue
                    name_volume = safe_int(record.get(metric_field))
                    round_data['volume_by_name'][name] += name_volume

                    crew = crew_lookup.get((upload['team_id'], name))
                    record_is_yongcha = safe_int(record.get('yongcha_count')) > 0
                    crew_is_yongcha = is_effective_yongcha(
                        crew,
                        round_no=upload['round_no'],
                        explicit_yongcha=record_is_yongcha,
                    )
                    if record_is_yongcha or crew_is_yongcha:
                        round_data['yongcha_names'].add(name)
                        round_data['manager_names'].discard(name)
                    elif name not in round_data['yongcha_names']:
                        round_data['manager_names'].add(name)

        amount_lookup = self._operation_report_amounts(
            request,
            start_date,
            end_date,
            {row['team_id'] for row in rows_by_key.values() if row.get('team_id')},
        )

        report_rows = []
        for row in rows_by_key.values():
            row_date = row['work_date'].isoformat()
            amounts = amount_lookup.get((row_date, row['team_id']), {})
            ratio_households = row['boxes_per_household_households']
            boxes_per_household = (
                row['boxes_per_household_boxes'] / ratio_households
                if ratio_households else 0
            )
            data = {
                'work_date': row_date,
                'delivery_date': row_date,
                'weekday': row['weekday'],
                'team_id': row['team_id'],
                'team_code': row['team_code'],
                'team_name': row['team_name'],
                'actual_total_boxes': row['actual_total_boxes'],
                'amount_total_receive': amounts.get('amount_total_receive', 0),
                'amount_regular_pay': amounts.get('amount_regular_pay', 0),
                'amount_yongcha_pay': amounts.get('amount_yongcha_pay', 0),
                'amount_profit': amounts.get('amount_profit', 0),
                'boxes_per_household': _format_ratio(boxes_per_household),
            }

            for round_no in (1, 2, 3):
                round_data = row['rounds'][round_no]
                manager_count = len(round_data['manager_names'])
                yongcha_count = len(round_data['yongcha_names'])
                input_count = manager_count + yongcha_count
                yongcha_ratio = (yongcha_count / input_count * 100) if input_count else 0
                productivity = (round_data['volume'] / input_count) if input_count else 0

                data[f'round_{round_no}_boxes'] = round_data['volume']
                data[f'round_{round_no}_input_count'] = input_count
                data[f'round_{round_no}_manager_count'] = manager_count
                data[f'round_{round_no}_yongcha_count'] = yongcha_count
                data[f'round_{round_no}_yongcha_ratio'] = _format_ratio(yongcha_ratio)
                data[f'round_{round_no}_productivity'] = _format_ratio(productivity)

            round_1_volume_by_name = row['rounds'][1]['volume_by_name']
            round_3_volume_by_name = row['rounds'][3]['volume_by_name']
            multi_round_names = set(round_1_volume_by_name.keys()) & set(round_3_volume_by_name.keys())
            multi_round_volume = sum(
                round_1_volume_by_name[name] + round_3_volume_by_name[name]
                for name in multi_round_names
            )
            multi_round_count = len(multi_round_names)
            multi_round_productivity = (
                multi_round_volume / multi_round_count
                if multi_round_count else 0
            )

            data['multi_round_driver_count'] = multi_round_count
            data['multi_round_boxes'] = multi_round_volume
            data['multi_round_productivity'] = _format_ratio(multi_round_productivity)
            data['daily_average_productivity'] = data['multi_round_productivity']
            data['metric'] = metric
            report_rows.append(data)

        report_rows.sort(key=lambda x: (x['delivery_date'], x['team_code'], x['team_name']))
        return report_rows, start_date, end_date, metric, metric_label, metric_unit

    def _build_operation_report_rows(self, request):
        metric, metric_label, metric_unit = self._operation_report_metric(request)
        metric_field = 'households' if metric == 'households' else 'boxes'
        uploads, start_date, end_date = self._operation_report_uploads(request)
        crew_codes_by_team = defaultdict(set)

        for upload in uploads:
            if not upload.team_id:
                continue
            for record in upload.records.all():
                name = str(record.manager_name or '').strip()
                if record.is_valid and name:
                    crew_codes_by_team[upload.team_id].add(name)

        crew_lookup = {}
        if crew_codes_by_team:
            team_ids = list(crew_codes_by_team.keys())
            all_codes = set()
            for codes in crew_codes_by_team.values():
                all_codes.update(codes)
            for crew in CrewMember.objects.filter(team_id__in=team_ids, code__in=all_codes):
                crew_lookup[(crew.team_id, crew.code)] = crew

        weekday_labels = ['월', '화', '수', '목', '금', '토', '일']

        def empty_round():
            return {
                'volume': 0,
                'manager_names': set(),
                'yongcha_names': set(),
                'volume_by_name': defaultdict(int),
            }

        def empty_row(upload):
            delivery_date = upload.dispatch_date
            return {
                'work_date': delivery_date,
                'delivery_date': delivery_date,
                'weekday': weekday_labels[delivery_date.weekday()],
                'team_id': upload.team_id,
                'team_code': upload.team.code if upload.team else '',
                'team_name': upload.team.name if upload.team else '',
                'actual_total_boxes': 0,
                'boxes_per_household_boxes': 0,
                'boxes_per_household_households': 0,
                'rounds': {1: empty_round(), 2: empty_round(), 3: empty_round()},
            }

        def record_volume(record):
            return safe_int(getattr(record, metric_field, 0))

        def record_boxes(record):
            return safe_int(record.boxes)

        def record_households(record):
            return safe_int(record.households)

        def detail_volume(detail):
            return safe_int(detail.boxes)

        rows_by_key = {}

        for upload in uploads:
            if not upload.dispatch_date or not upload.team_id:
                continue
            delivery_date = upload.dispatch_date
            key = (delivery_date.isoformat(), upload.team_id)
            row = rows_by_key.setdefault(key, empty_row(upload))
            settlement_details = [d for d in upload.settlement_details.all() if d.crew_member_id]
            valid_records = [r for r in upload.records.all() if r.is_valid]
            use_settlement_details = metric == 'boxes' and settlement_details
            upload_volume = (
                sum(detail_volume(d) for d in settlement_details)
                if use_settlement_details
                else sum(record_volume(r) for r in valid_records)
            )
            ratio_boxes = (
                sum(detail_volume(d) for d in settlement_details)
                if settlement_details
                else sum(record_boxes(r) for r in valid_records)
            )
            ratio_households = sum(record_households(r) for r in valid_records)
            row['actual_total_boxes'] += upload_volume
            row['boxes_per_household_boxes'] += ratio_boxes
            row['boxes_per_household_households'] += ratio_households

            round_no = upload.round_no if upload.round_no in (1, 2, 3) else None
            if not round_no:
                continue

            round_data = row['rounds'][round_no]
            round_data['volume'] += upload_volume

            if use_settlement_details:
                details_by_name = defaultdict(list)
                for detail in settlement_details:
                    crew = detail.crew_member
                    name = str(crew.code or crew.name or '').strip() if crew else ''
                    if name:
                        details_by_name[name].append(detail)

                for name, details in details_by_name.items():
                    name_volume = sum(detail_volume(d) for d in details)
                    round_data['volume_by_name'][name] += name_volume

                    crew = details[0].crew_member
                    detail_is_yongcha = any(d.is_yongcha for d in details)
                    crew_is_yongcha = is_effective_yongcha(
                        crew,
                        round_no=upload.round_no,
                        explicit_yongcha=detail_is_yongcha,
                    )
                    if detail_is_yongcha or crew_is_yongcha:
                        round_data['yongcha_names'].add(name)
                        round_data['manager_names'].discard(name)
                    elif name not in round_data['yongcha_names']:
                        round_data['manager_names'].add(name)
            else:
                records_by_name = defaultdict(list)
                for record in valid_records:
                    name = str(record.manager_name or '').strip()
                    if name:
                        records_by_name[name].append(record)

                for name, records in records_by_name.items():
                    name_volume = sum(record_volume(r) for r in records)
                    round_data['volume_by_name'][name] += name_volume

                    crew = crew_lookup.get((upload.team_id, name))
                    record_is_yongcha = any(r.is_yongcha for r in records)
                    crew_is_yongcha = is_effective_yongcha(
                        crew,
                        round_no=upload.round_no,
                        explicit_yongcha=record_is_yongcha,
                    )
                    if record_is_yongcha or crew_is_yongcha:
                        round_data['yongcha_names'].add(name)
                        round_data['manager_names'].discard(name)
                    elif name not in round_data['yongcha_names']:
                        round_data['manager_names'].add(name)

        amount_lookup = self._operation_report_amounts(
            request,
            start_date,
            end_date,
            {row['team_id'] for row in rows_by_key.values() if row.get('team_id')},
        )

        report_rows = []
        for row in rows_by_key.values():
            row_date = row['work_date'].isoformat()
            amounts = amount_lookup.get((row_date, row['team_id']), {})
            ratio_households = row['boxes_per_household_households']
            boxes_per_household = (
                row['boxes_per_household_boxes'] / ratio_households
                if ratio_households else 0
            )
            data = {
                'work_date': row_date,
                'delivery_date': row_date,
                'weekday': row['weekday'],
                'team_id': row['team_id'],
                'team_code': row['team_code'],
                'team_name': row['team_name'],
                'actual_total_boxes': row['actual_total_boxes'],
                'amount_total_receive': amounts.get('amount_total_receive', 0),
                'amount_regular_pay': amounts.get('amount_regular_pay', 0),
                'amount_yongcha_pay': amounts.get('amount_yongcha_pay', 0),
                'amount_profit': amounts.get('amount_profit', 0),
                'boxes_per_household': _format_ratio(boxes_per_household),
            }

            for round_no in (1, 2, 3):
                round_data = row['rounds'][round_no]
                manager_count = len(round_data['manager_names'])
                yongcha_count = len(round_data['yongcha_names'])
                input_count = manager_count + yongcha_count
                yongcha_ratio = (yongcha_count / input_count * 100) if input_count else 0
                productivity = (round_data['volume'] / input_count) if input_count else 0

                data[f'round_{round_no}_boxes'] = round_data['volume']
                data[f'round_{round_no}_input_count'] = input_count
                data[f'round_{round_no}_manager_count'] = manager_count
                data[f'round_{round_no}_yongcha_count'] = yongcha_count
                data[f'round_{round_no}_yongcha_ratio'] = _format_ratio(yongcha_ratio)
                data[f'round_{round_no}_productivity'] = _format_ratio(productivity)

            round_1_volume_by_name = row['rounds'][1]['volume_by_name']
            round_3_volume_by_name = row['rounds'][3]['volume_by_name']
            multi_round_names = set(round_1_volume_by_name.keys()) & set(round_3_volume_by_name.keys())
            multi_round_volume = sum(
                round_1_volume_by_name[name] + round_3_volume_by_name[name]
                for name in multi_round_names
            )
            multi_round_count = len(multi_round_names)
            multi_round_productivity = (
                multi_round_volume / multi_round_count
                if multi_round_count else 0
            )

            data['multi_round_driver_count'] = multi_round_count
            data['multi_round_boxes'] = multi_round_volume
            data['multi_round_productivity'] = _format_ratio(multi_round_productivity)
            # Backward compatibility for older frontends.
            data['daily_average_productivity'] = data['multi_round_productivity']
            data['metric'] = metric
            report_rows.append(data)

        report_rows.sort(key=lambda x: (x['delivery_date'], x['team_code'], x['team_name']))
        return report_rows, start_date, end_date, metric, metric_label, metric_unit

    @action(detail=False, methods=['get'], url_path='operation-report')
    def operation_report(self, request):
        rows, start_date, end_date, metric, metric_label, metric_unit = self._cached_operation_report_rows(request)
        summary = build_operation_report_summary(rows)
        return Response({
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'metric': metric,
            'metric_label': metric_label,
            'metric_unit': metric_unit,
            'summary': summary,
            'results': rows,
        })

    @action(detail=False, methods=['get'], url_path='operation-report-territories')
    def operation_report_territories(self, request):
        from apps.territory.models import Territory

        company_app = get_company_app_from_request(request)
        team_filter = str(request.query_params.get('team') or '').strip()
        cache_key = self._operation_report_static_cache_key(
            request,
            'territories-v1',
            {'team': team_filter},
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        territory_qs = (
            Territory.objects
            .filter(team__company_app=company_app)
            .select_related('team')
        )
        if team_filter:
            team_q = Q(team__name=team_filter) | Q(team__code=team_filter)
            if team_filter.isdigit():
                team_q = team_q | Q(team_id=int(team_filter))
            territory_qs = territory_qs.filter(team_q)

        results = [
            {
                'id': territory.id,
                'code': territory.code,
                'group_letter': territory.group_letter,
                'team_id': territory.team_id,
                'team_code': territory.team.code if territory.team else '',
                'team_name': territory.team.name if territory.team else '',
                'geometry': territory.geometry,
                'centroid_lat': territory.centroid_lat,
                'centroid_lon': territory.centroid_lon,
            }
            for territory in territory_qs.order_by('team__code', 'code')
        ]
        payload = {
            'count': len(results),
            'results': results,
        }
        cache.set(cache_key, payload, 600)
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='operation-report-yongcha-map')
    def operation_report_yongcha_map(self, request):
        from apps.territory.models import Territory

        include_geometry = str(request.query_params.get('include_geometry') or '').lower() in ('1', 'true', 'yes')
        cache_key = None
        if not include_geometry:
            cache_key = self._operation_report_cache_key(request, 'yongcha-map-v2')
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

        uploads, start_date, end_date = self._operation_report_uploads(
            request,
            include_settlement_details=False,
        )
        crew_codes_by_team = defaultdict(set)

        for upload in uploads:
            if not upload.team_id:
                continue
            for record in upload.records.all():
                name = str(record.manager_name or '').strip()
                if record.is_valid and name:
                    crew_codes_by_team[upload.team_id].add(name)

        crew_lookup = {}
        if crew_codes_by_team:
            team_ids = list(crew_codes_by_team.keys())
            all_codes = set()
            for codes in crew_codes_by_team.values():
                all_codes.update(codes)
            for crew in CrewMember.objects.filter(team_id__in=team_ids, code__in=all_codes):
                crew_lookup[(crew.team_id, crew.code)] = crew

        yongcha_round_details = defaultdict(dict)
        yongcha_record_count = 0
        unmatched_regions = defaultdict(int)

        for upload in uploads:
            round_no = upload.round_no if upload.round_no in (1, 2, 3) else None
            if not upload.team_id:
                continue
            delivery_date = upload.dispatch_date
            round_key = (
                delivery_date.isoformat() if delivery_date else '',
                upload.team_id,
                round_no or upload.id,
            )
            for record in upload.records.all():
                if not record.is_valid:
                    continue
                regions = sorted(set(split_region_codes(record.sub_region)))
                if not regions:
                    continue

                name = str(record.manager_name or '').strip()
                crew = crew_lookup.get((upload.team_id, name))
                record_is_yongcha = bool(record.is_yongcha)
                crew_is_yongcha = is_effective_yongcha(
                    crew,
                    round_no=round_no,
                    explicit_yongcha=record_is_yongcha,
                )
                if not (record_is_yongcha or crew_is_yongcha):
                    continue

                yongcha_record_count += 1
                driver_name = str(getattr(crew, 'name', '') or name or '이름 없음').strip()
                for region_code in regions:
                    detail = yongcha_round_details[region_code].setdefault(round_key, {
                        'date': delivery_date.isoformat() if delivery_date else '',
                        'round_no': round_no,
                        'drivers': set(),
                    })
                    detail['drivers'].add(driver_name)

        yongcha_counts = {
            region_code: len(rounds)
            for region_code, rounds in yongcha_round_details.items()
        }
        yongcha_round_count = sum(yongcha_counts.values())

        def serialize_region_rounds(region_code):
            by_date = defaultdict(lambda: defaultdict(set))
            for detail in yongcha_round_details.get(region_code, {}).values():
                date_key = detail.get('date') or ''
                round_no = detail.get('round_no')
                by_date[date_key][round_no].update(detail.get('drivers') or [])

            rows = []
            for date_key in sorted(by_date):
                rounds = []
                for round_no, drivers in sorted(
                    by_date[date_key].items(),
                    key=lambda item: (item[0] is None, item[0] or 0),
                ):
                    rounds.append({
                        'round_no': round_no,
                        'round_label': f'{round_no}회차' if round_no else '회차 미지정',
                        'drivers': sorted(drivers),
                    })
                rows.append({
                    'date': date_key,
                    'rounds': rounds,
                    'drivers': sorted({driver for item in rounds for driver in item['drivers']}),
                })
            return rows

        company_app = get_company_app_from_request(request)
        territory_qs = (
            Territory.objects
            .filter(team__company_app=company_app)
            .select_related('team')
        )

        team_filter = str(request.query_params.get('team') or '').strip()
        if team_filter:
            team_q = Q(team__name=team_filter) | Q(team__code=team_filter)
            if team_filter.isdigit():
                team_q = team_q | Q(team_id=int(team_filter))
            territory_qs = territory_qs.filter(team_q)

        max_count = max(yongcha_counts.values(), default=0)
        territory_codes = set()
        territories = []
        for territory in territory_qs.order_by('team__code', 'code'):
            count = int(yongcha_counts.get(territory.code, 0))
            level = 0
            if count and max_count:
                level = min(5, max(1, math.ceil(count / max_count * 5)))
            territory_codes.add(territory.code)
            territory_payload = {
                'id': territory.id,
                'code': territory.code,
                'group_letter': territory.group_letter,
                'team_id': territory.team_id,
                'team_code': territory.team.code if territory.team else '',
                'team_name': territory.team.name if territory.team else '',
                'centroid_lat': territory.centroid_lat,
                'centroid_lon': territory.centroid_lon,
                'yongcha_count': count,
                'yongcha_round_count': count,
                'yongcha_dates': serialize_region_rounds(territory.code),
                'level': level,
            }
            if include_geometry:
                territory_payload['geometry'] = territory.geometry
            territories.append(territory_payload)

        for region_code, count in yongcha_counts.items():
            if region_code not in territory_codes:
                unmatched_regions[region_code] += count

        top_territory = None
        positive_territories = [item for item in territories if item['yongcha_count'] > 0]
        if positive_territories:
            top_territory = max(
                positive_territories,
                key=lambda item: (item['yongcha_count'], item['code']),
            )

        summary_top_territory = None
        if top_territory:
            summary_top_territory = {
                key: value
                for key, value in top_territory.items()
                if key not in ('geometry', 'yongcha_dates')
            }

        payload = {
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'summary': {
                'territory_count': len(territories),
                'active_territory_count': len(positive_territories),
                'total_yongcha_records': yongcha_record_count,
                'total_yongcha_visits': yongcha_round_count,
                'total_yongcha_rounds': yongcha_round_count,
                'max_yongcha_count': max_count,
                'top_territory': summary_top_territory,
                'unmatched_region_count': len(unmatched_regions),
            },
            'unmatched_regions': [
                {'code': code, 'yongcha_count': count}
                for code, count in sorted(unmatched_regions.items())
            ],
            'results': territories,
        }
        if cache_key:
            cache.set(cache_key, payload, 90)
        return Response(payload)

    @action(detail=False, methods=['get'], url_path='operation-report-csv')
    def operation_report_csv(self, request):
        rows, start_date, end_date, metric, metric_label, metric_unit = self._cached_operation_report_rows(request)
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        filename = f'operation_report_{metric}_{start_date.isoformat()}_{end_date.isoformat()}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')

        writer = csv.writer(response)
        write_operation_report_csv(writer, rows, metric_label, metric_unit)
        return response

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
                    team = Team.objects.get(
                        id=team_id,
                        company_app=get_company_app_from_request(request),
                    )
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
                    crew = CrewMember.objects.get(code=code, team=dispatch_upload.team)
                    crew.name = ci.get('name', code)
                    crew.phone = ci.get('phone', '')
                    crew.vehicle_number = ci.get('vehicle_number', '')
                    pay_price = ci.get('pay_price')
                    yongcha_pay_price = ci.get('yongcha_pay_price')
                    pay_decimal = Decimal(str(pay_price if pay_price is not None else crew.pay_price or 0))
                    yongcha_pay_decimal = Decimal(str(
                        yongcha_pay_price if yongcha_pay_price is not None else crew.yongcha_pay_price or 3000
                    ))
                    if pay_price is not None:
                        crew.pay_price = pay_decimal
                    if yongcha_pay_price is not None:
                        crew.yongcha_pay_price = yongcha_pay_decimal
                    should_be_yongcha = bool(ci.get('is_yongcha')) or (crew.is_new and pay_decimal == 0)
                    crew.is_yongcha = should_be_yongcha
                    crew.is_new = False
                    crew.save(update_fields=[
                        'name', 'phone', 'vehicle_number', 'pay_price', 'yongcha_pay_price', 'is_new', 'is_yongcha'
                    ])
                    crew_count += 1
                except CrewMember.DoesNotExist:
                    continue

            self._update_mor_summary(dispatch_upload)

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
                    crew = CrewMember.objects.get(code=name, team=dispatch_upload.team)
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
        shipper_code = normalize_shipper_code(getattr(dispatch_upload, 'shipper_code', None))
        receive_price = team.receive_price or Decimal('0')

        records = dispatch_upload.records.filter(is_valid=True)
        crew_records = defaultdict(list)
        skipped_crew = []

        for rec in records:
            if not rec.manager_name:
                continue
            try:
                crew = CrewMember.objects.get(code=rec.manager_name, team=team)
                crew_pay_price = crew.pay_price or Decimal('0')
                should_be_yongcha = crew.is_yongcha or rec.is_yongcha or (crew.is_new and crew_pay_price == 0)
                if should_be_yongcha and (crew.is_new or not crew.is_yongcha):
                    crew.is_new = False
                    crew.is_yongcha = True
                    crew.save(update_fields=['is_new', 'is_yongcha'])
                if crew.is_new:
                    if rec.manager_name not in skipped_crew:
                        skipped_crew.append(rec.manager_name)
                    continue
                crew_records[rec.manager_name].append(rec)
            except CrewMember.DoesNotExist:
                if rec.is_yongcha:
                    CrewMember.objects.create(
                        code=rec.manager_name,
                        name=rec.manager_name,
                        team=team,
                        pay_price=0,
                        region=rec.sub_region or '',
                        is_active=True,
                        is_new=False,
                        is_yongcha=True,
                    )
                    crew_records[rec.manager_name].append(rec)
                elif rec.manager_name not in skipped_crew:
                    skipped_crew.append(rec.manager_name)

        with transaction.atomic():
            settlement, created = Settlement.objects.get_or_create(
                team=team, shipper_code=shipper_code, period_start=period_start, period_end=period_end,
                defaults={'status': 'DRAFT', 'note': note}
            )
            # 같은 날짜 합산: 이번 upload의 기존 detail만 삭제 (다른 upload 것은 유지)
            settlement.details.filter(dispatch_upload=dispatch_upload).delete()

            total_receive = Decimal('0')
            total_pay = Decimal('0')
            total_overtime = Decimal('0')
            crew_details = []
            crew_members_by_code = {
                crew.code: crew
                for crew in CrewMember.objects.filter(
                    code__in=crew_records.keys(),
                    team=team,
                ).select_related('yongcha_pay_group', 'team')
            }
            daily_yongcha_round_counts = build_daily_yongcha_round_counts(
                crew_members_by_code.values(),
                dispatch_upload,
            )

            for crew_code, recs in crew_records.items():
                crew = crew_members_by_code.get(crew_code)
                if not crew:
                    continue

                # 특근 조회
                ot_setting = OvertimeSetting.objects.filter(
                    dispatch_upload=dispatch_upload, crew_member=crew, is_overtime=True
                ).first()
                overtime_cost = Decimal(str(ot_setting.overtime_cost)) if ot_setting else Decimal('0')
                payload = build_crew_settlement_payload(
                    crew_member=crew,
                    dispatch_upload=dispatch_upload,
                    records=recs,
                    receive_price=receive_price,
                    overtime_cost=overtime_cost,
                    daily_yongcha_round_count=daily_yongcha_round_counts.get(crew.id),
                )

                total_boxes = payload['total_boxes']
                total_households = payload['total_households']
                r_amount = payload['total_receive']
                p_amount = payload['total_pay']
                profit = payload['total_profit']
                is_yongcha = payload['is_yongcha']
                crew_regions = payload['regions']

                for cr in crew_regions:
                    SettlementDetail.objects.create(
                        settlement=settlement, dispatch_upload=dispatch_upload,
                        crew_member=crew,
                        shipper_code=shipper_code,
                        is_yongcha=is_yongcha,
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
                    'is_yongcha': is_yongcha,
                    'regions': [{
                        'region': item['region'],
                        'boxes': item['boxes'],
                        'households': item['households'],
                        'receive_amount': int(item['receive_amount']),
                        'pay_amount': int(item['pay_amount']),
                        'overtime_cost': int(item['overtime_cost']),
                        'profit': int(item['profit']),
                    } for item in crew_regions],
                    'total_boxes': total_boxes,
                    'total_households': total_households,
                    'total_receive': int(r_amount), 'total_pay': int(p_amount),
                    'total_overtime': int(overtime_cost), 'total_profit': int(profit),
                    'pay_basis': payload['pay_basis'],
                    'daily_yongcha_round_count': payload.get('daily_yongcha_round_count', 0),
                })

            # 전체 detail에서 합계 재계산 (이전 upload + 이번 upload)
            from django.db.models import Sum
            agg = settlement.details.aggregate(
                r=Sum('receive_amount'), p=Sum('pay_amount'),
                o=Sum('overtime_cost'), pr=Sum('profit')
            )
            settlement.total_receive = agg['r'] or 0
            settlement.total_pay = agg['p'] or 0
            settlement.total_overtime = agg['o'] or 0
            settlement.total_profit = agg['pr'] or 0
            settlement.status = 'CONFIRMED'
            settlement.save()
            dispatch_upload.status = 'CONFIRMED'
            dispatch_upload.save()
            self._update_mor_summary(dispatch_upload)

        return Response({
            'detail': '정산 생성 완료',
            'settlement': {
                'id': settlement.id,
                'team': team.name,
                'shipper_code': settlement.shipper_code,
                'period_start': date_iso(period_start),
                'period_end': date_iso(period_end),
                'work_period_start': date_iso(to_work_date(period_start)),
                'work_period_end': date_iso(to_work_date(period_end)),
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
