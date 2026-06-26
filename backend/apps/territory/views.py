import csv as _csv
import io
import math
import re
from collections import defaultdict
from datetime import timedelta
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from .models import Territory, TerritoryBoxRecord, extract_group_letter
from .serializers import TerritorySerializer, TerritoryBoxRecordSerializer
from .geometry import point_in_geometry, bbox_of_geometry

# 다른 앱 참조
from apps.manpower.views import (
    FIXED_MANPOWER_SHEET_URL,
    _normalize_sheet_to_csv_url,
    _fetch_url,
)
from apps.manpower.sigungu import lookup as sigungu_lookup
from apps.tracking.models import CameraCapture, Cycle, STATE_SEARCHING, STATE_DELIVERING
from apps.accounts.models import Team
from apps.common.company_scope import get_company_app_from_request

TERRITORY_SETTLEMENT_SYNC_CACHE_KEY = 'territory:settlement-sync:last'
TERRITORY_SETTLEMENT_SYNC_LOCK_KEY = 'territory:settlement-sync:lock'
TERRITORY_SETTLEMENT_SYNC_TTL = 600


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def _parse_int(value, default=0):
    try:
        return int(float(str(value or '').replace('년', '').replace('세', '').strip() or default))
    except Exception:
        return default


def _fallback_age(seed):
    text = str(seed or '')
    return 28 + (sum(ord(ch) for ch in text) % 28)


def _resolve_team_from_code(code):
    group = extract_group_letter(code)
    if not group:
        return None
    return Team.objects.filter(code__iexact=group, is_active=True).first()


def _resolve_team_from_code_for_company(code, company_app):
    group = extract_group_letter(code)
    if not group:
        return None
    return Team.objects.filter(
        code__iexact=group,
        is_active=True,
        company_app=company_app,
    ).first()


def _make_rect_geometry(cx, cy, width=0.012, height=0.008):
    hx = width / 2
    hy = height / 2
    return {
        'type': 'Polygon',
        'coordinates': [[
            [cx - hx, cy - hy],
            [cx + hx, cy - hy],
            [cx + hx, cy + hy],
            [cx - hx, cy + hy],
            [cx - hx, cy - hy],
        ]],
    }


def _placeholder_geometry_for_code(code):
    """
    정산처리에만 있고 아직 GeoJSON 이 없는 권역을 지도에 보이게 하기 위한 임시 폴리곤.
    실제 권역 좌표가 들어오면 GeoJSON 업로드/지도 그리기로 이 geometry 를 교체한다.
    """
    group = extract_group_letter(code) or 'X'
    base_by_group = {
        'A': (126.912, 37.520),
        'H': (127.043, 37.508),
        'R': (127.010, 37.590),
        'T': (126.978, 37.566),
    }
    base_lon, base_lat = base_by_group.get(group[0], (126.978, 37.566))

    nums = [int(x) for x in re.findall(r'\d+', str(code or ''))]
    prefix = nums[0] if nums else 10
    suffix = nums[-1] if nums else 1
    row = max(0, int(prefix / 10) - 1)
    col = max(0, suffix - 1)

    cx = base_lon + (col % 6) * 0.014
    cy = base_lat - row * 0.010 - int(col / 6) * 0.010
    return _make_rect_geometry(cx, cy)


def _ensure_settlement_territories(force=False):
    from apps.settlement.models import SettlementDetail

    if not force and cache.get(TERRITORY_SETTLEMENT_SYNC_CACHE_KEY):
        return 0, 0
    if not cache.add(TERRITORY_SETTLEMENT_SYNC_LOCK_KEY, True, timeout=60):
        return 0, 0

    try:
        codes = sorted({
            str(code or '').strip()
            for code in SettlementDetail.objects.values_list('region', flat=True)
            if str(code or '').strip()
        })
        existing = {
            str(code or '').strip()
            for code in Territory.objects.values_list('code', flat=True)
        }
        gpkg_backed_groups = {
            str(group or '').strip().upper()
            for group in Territory.objects.filter(note__icontains='GPKG').values_list('group_letter', flat=True)
            if str(group or '').strip()
        }

        created = 0
        updated = 0
        for code in codes:
            team = _resolve_team_from_code(code)
            group = extract_group_letter(code)
            if code not in existing:
                if group in gpkg_backed_groups:
                    continue
                Territory.objects.create(
                    code=code,
                    team=team,
                    geometry=_placeholder_geometry_for_code(code),
                    color='#64748B',
                    note='???? ?? ?? ?? - ?? ??? GeoJSON ??? ?? ?? ???? ??',
                )
                created += 1
                continue
            if team:
                n = Territory.objects.filter(code=code, team__isnull=True).update(team=team)
                updated += n

        cache.set(
            TERRITORY_SETTLEMENT_SYNC_CACHE_KEY,
            timezone.now().isoformat(),
            timeout=TERRITORY_SETTLEMENT_SYNC_TTL,
        )
        return created, updated
    finally:
        cache.delete(TERRITORY_SETTLEMENT_SYNC_LOCK_KEY)


def _settlement_box_series(territory):
    """
    권역별 박스수는 정산 상세를 기준 데이터로 본다.
    같은 권역/날짜에 여러 배송원이 있으면 합산하고, 정산 기간이 여러 날이면 일자별로 분배한다.
    """
    from apps.settlement.models import SettlementDetail

    accum = defaultdict(float)
    split_flag = defaultdict(bool)
    qs = (
        SettlementDetail.objects
        .select_related('settlement')
        .filter(region=territory.code)
    )
    for detail in qs:
        settlement = detail.settlement
        if not settlement or not settlement.period_start or not settlement.period_end:
            continue
        days = (settlement.period_end - settlement.period_start).days + 1
        if days <= 0:
            continue
        per_day = float(detail.boxes or 0) / days
        current = settlement.period_start
        for _ in range(days):
            accum[current] += per_day
            if days > 1:
                split_flag[current] = True
            current += timedelta(days=1)

    return accum, split_flag


class TerritoryViewSet(viewsets.ModelViewSet):
    queryset = Territory.objects.all()
    serializer_class = TerritorySerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = Territory.objects.all()
        user = self.request.user
        if user.is_admin():
            queryset = queryset.filter(team__company_app=get_company_app_from_request(self.request))
        elif user.team:
            queryset = queryset.filter(Q(team=user.team) | Q(group_letter__iexact=user.team.code))
        else:
            return queryset.none()

        team_filter = str(self.request.query_params.get('team') or '').strip()
        if team_filter:
            team_q = Q(team__code__iexact=team_filter) | Q(team__name=team_filter)
            if team_filter.isdigit():
                team_q = team_q | Q(team_id=int(team_filter))
            queryset = queryset.filter(team_q)

        group_filter = str(
            self.request.query_params.get('group') or self.request.query_params.get('group_letter') or ''
        ).strip()
        if group_filter:
            queryset = queryset.filter(group_letter__iexact=group_filter)

        return queryset

    def list(self, request, *args, **kwargs):
        _ensure_settlement_territories()
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        save_kwargs = {'created_by': self.request.user}
        if not serializer.validated_data.get('team'):
            team = _resolve_team_from_code_for_company(
                serializer.validated_data.get('code'),
                get_company_app_from_request(self.request),
            )
            if team:
                save_kwargs['team'] = team
        serializer.save(**save_kwargs)

    def perform_update(self, serializer):
        save_kwargs = {'updated_by': self.request.user}
        if 'team' not in serializer.validated_data:
            code = serializer.validated_data.get('code', serializer.instance.code)
            team = _resolve_team_from_code_for_company(
                code,
                get_company_app_from_request(self.request),
            )
            if team:
                save_kwargs['team'] = team
        serializer.save(**save_kwargs)

    # -------------------------------------------------------
    @action(detail=False, methods=['post'], url_path='import_geojson',
            parser_classes=[JSONParser, MultiPartParser, FormParser])
    def import_geojson(self, request):
        """
        GeoJSON FeatureCollection 업로드 → Territory 레코드 upsert.
        feature.properties.name 에서 권역 코드 추출.
        payload: {"features":[...]}  또는 multipart file (json)
        """
        payload = request.data
        if 'file' in request.FILES:
            import json
            try:
                payload = json.loads(request.FILES['file'].read().decode('utf-8-sig'))
            except Exception as e:
                return Response({'detail': f'GeoJSON 파싱 실패: {e}'},
                                status=status.HTTP_400_BAD_REQUEST)

        fc = payload.get('features') if isinstance(payload, dict) else None
        if not fc:
            return Response({'detail': 'FeatureCollection 이 필요합니다'},
                            status=status.HTTP_400_BAD_REQUEST)

        created = updated = 0
        for feat in fc:
            props = feat.get('properties') or {}
            geom = feat.get('geometry') or {}
            code = (str(props.get('name') or props.get('code') or props.get('NAME') or '')
                    .strip() or f'T{created + updated + 1}')
            team = _resolve_team_from_code(code)
            defaults = {
                'geometry': geom,
                'group_letter': extract_group_letter(code),
            }
            if team:
                defaults['team'] = team
            obj, was_created = Territory.objects.update_or_create(
                code=code,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return Response({'created': created, 'updated': updated})

    # -------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='box_series')
    def box_series(self, request, pk=None):
        """일별 박스 수 시계열."""
        t = self.get_object()
        settlement_boxes, settlement_split = _settlement_box_series(t)
        manual_records = {item.date: item for item in t.box_records.all()}

        dates = sorted(set(settlement_boxes.keys()) | set(manual_records.keys()))
        rows = []
        for item_date in dates:
            manual = manual_records.get(item_date)
            if item_date in settlement_boxes:
                rows.append({
                    'id': manual.id if manual else None,
                    'territory': t.id,
                    'date': item_date.isoformat(),
                    'box_count': round(settlement_boxes[item_date], 2),
                    'is_split': settlement_split[item_date],
                    'source': 'settlement',
                })
            elif manual:
                rows.append({
                    'id': manual.id,
                    'territory': t.id,
                    'date': manual.date.isoformat(),
                    'box_count': manual.box_count,
                    'is_split': manual.is_split,
                    'source': 'manual',
                })
        return Response(rows)

    @action(detail=True, methods=['post'], url_path='box_set')
    def box_set(self, request, pk=None):
        """수동 박스수 입력 (개별/여러 건)."""
        t = self.get_object()
        items = request.data if isinstance(request.data, list) else [request.data]
        saved = 0
        for it in items:
            date = it.get('date')
            if not date:
                continue
            TerritoryBoxRecord.objects.update_or_create(
                territory=t, date=date,
                defaults={
                    'box_count': float(it.get('box_count') or 0),
                    'is_split': bool(it.get('is_split') or False),
                },
            )
            saved += 1
        return Response({'saved': saved})

    # -------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='nearby_manpower')
    def nearby_manpower(self, request, pk=None):
        """
        권역 centroid 로부터 radius_m 내 인력 (구글 공유시트 → 시군구 룩업 → 거리).
        DB 저장 없이 실시간 시트 데이터를 사용.
        """
        t = self.get_object()
        if not (t.centroid_lat and t.centroid_lon):
            return Response([])

        radius_m = float(request.query_params.get('radius_m') or 10000)

        csv_url = _normalize_sheet_to_csv_url(FIXED_MANPOWER_SHEET_URL)
        try:
            content = _fetch_url(csv_url)
        except Exception as e:
            return Response({'detail': f'시트 조회 실패: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
        if content[:200].lstrip().lower().startswith('<!doctype html') or '<html' in content[:200].lower():
            return Response({'detail': '시트가 비공개입니다'}, status=status.HTTP_403_FORBIDDEN)

        try:
            rows = list(_csv.reader(io.StringIO(content)))
        except Exception as e:
            return Response({'detail': f'CSV 파싱 실패: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        if not rows:
            return Response([])

        header = [str(c or '').strip() for c in rows[0]]

        def col_index(*keywords):
            for i, h in enumerate(header):
                for kw in keywords:
                    if kw in h:
                        return i
            return -1

        idx_name = col_index('이름', '성명')
        idx_addr = col_index('거주', '주소')
        idx_phone = col_index('휴대', '전화', '연락')
        idx_veh = col_index('차량')
        idx_exp = col_index('경력')
        idx_age = col_index('나이', '연령', 'age')

        out = []
        for row in rows[1:]:
            def cell(i):
                return row[i] if 0 <= i < len(row) else None
            name = str(cell(idx_name) or '').strip() if idx_name >= 0 else ''
            if not name:
                continue
            addr = str(cell(idx_addr) or '').strip() if idx_addr >= 0 else ''
            coord = sigungu_lookup(addr)
            if not coord:
                continue
            lat, lon = coord
            d = _haversine_m(t.centroid_lat, t.centroid_lon, lat, lon)
            if d > radius_m:
                continue

            veh_raw = str(cell(idx_veh) or '').strip().lower() if idx_veh >= 0 else ''
            has_veh = veh_raw in ('y', 'yes', 'o', 'true', '1', '유', '있', '있음')
            exp = _parse_int(cell(idx_exp) if idx_exp >= 0 else 0)
            age = _parse_int(cell(idx_age) if idx_age >= 0 else 0)
            if not age:
                age = _fallback_age(f'{name}{cell(idx_phone)}')

            out.append({
                'name': name,
                'phone': str(cell(idx_phone) or '').strip() if idx_phone >= 0 else '',
                'address': addr,
                'age': age,
                'experience_years': exp,
                'has_vehicle': has_veh,
                'lat': lat,
                'lon': lon,
                'distance_m': round(d, 1),
            })

        deduped = {}
        for item in out:
            name_key = re.sub(r'\s+', '', str(item.get('name') or '')).lower()
            phone_key = re.sub(r'\D+', '', str(item.get('phone') or ''))
            key = name_key or phone_key
            if not key:
                continue
            current = deduped.get(key)
            if (
                current is None
                or item['distance_m'] < current['distance_m']
                or (
                    item['distance_m'] == current['distance_m']
                    and (
                        int(bool(item.get('has_vehicle'))) > int(bool(current.get('has_vehicle')))
                        or int(item.get('experience_years') or 0) > int(current.get('experience_years') or 0)
                    )
                )
            ):
                deduped[key] = item

        out = list(deduped.values())
        out.sort(key=lambda x: x['distance_m'])
        return Response(out)

    # -------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='cycles_inside')
    def cycles_inside(self, request, pk=None):
        """
        ?? ??? ??? camera end(captured_at) ???? ???? cycle ???
        ?? IV/SR/DL ??? ????.
        """
        t = self.get_object()
        if not t.geometry:
            return Response({'cycles': [], 'summary': {}})
        cache_key = f'territory:cycles_inside:{t.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        bbox = bbox_of_geometry(t.geometry) or (-180, -90, 180, 90)
        caps = (
            CameraCapture.objects
            .filter(
                lon__gte=bbox[0],
                lon__lte=bbox[2],
                lat__gte=bbox[1],
                lat__lte=bbox[3],
                lat__isnull=False,
                lon__isnull=False,
            )
            .select_related('session__crew_member')
        )
        caps_in = [c for c in caps if point_in_geometry(c.lon, c.lat, t.geometry)]

        if not caps_in:
            return Response({
                'cycles': [],
                'summary': {
                    'capture_count': 0,
                    'cycle_count': 0,
                    'iv_cycle_count': 0,
                    'avg_iv_sec': 0,
                    'avg_sr_sec': 0,
                    'avg_dl_sec': 0,
                },
            })

        session_ids = sorted({c.session_id for c in caps_in if c.session_id})
        cycles_by_session = defaultdict(list)
        prev_cycle_by_id = {}
        for cyc in (
            Cycle.objects
            .filter(session_id__in=session_ids)
            .select_related('session__crew_member')
            .order_by('session_id', 'cycle_no')
        ):
            session_cycles = cycles_by_session[cyc.session_id]
            prev_cycle_by_id[cyc.id] = session_cycles[-1] if session_cycles else None
            session_cycles.append(cyc)

        matched_cycles = {}
        capture_count_by_cycle = defaultdict(int)
        for c in caps_in:
            if not c.captured_at:
                continue
            for cyc in cycles_by_session.get(c.session_id, ()):
                if cyc.started_at <= c.captured_at <= cyc.ended_at:
                    matched_cycles[cyc.id] = cyc
                    capture_count_by_cycle[cyc.id] += 1
                    break

        out_cycles = []
        sum_iv = 0
        sum_sr = 0
        sum_dl = 0
        iv_count = 0
        for cy in sorted(matched_cycles.values(), key=lambda item: (item.session_id, item.cycle_no)):
            prev_cycle = prev_cycle_by_id.get(cy.id)
            iv_seconds = None
            if prev_cycle:
                iv_seconds = max(0, int((cy.started_at - prev_cycle.ended_at).total_seconds()))
                sum_iv += iv_seconds
                iv_count += 1
            route_started_at = prev_cycle.ended_at if prev_cycle else cy.started_at

            out_cycles.append({
                'cycle_id': cy.id,
                'cycle_no': cy.cycle_no,
                'session_id': cy.session_id,
                'crew_name': getattr(cy.session.crew_member, 'name', ''),
                'date': cy.session.session_date.isoformat(),
                'previous_cycle_no': prev_cycle.cycle_no if prev_cycle else None,
                'iv_seconds': iv_seconds,
                'route_started_at': route_started_at.isoformat(),
                'route_ended_at': cy.ended_at.isoformat(),
                'started_at': cy.started_at.isoformat(),
                'ended_at': cy.ended_at.isoformat(),
                'sr_seconds': cy.sr_seconds,
                'dl_seconds': cy.dl_seconds,
                'capture_count': capture_count_by_cycle.get(cy.id, 0),
            })
            sum_sr += cy.sr_seconds
            sum_dl += cy.dl_seconds

        n = len(out_cycles)
        out_cycles.sort(key=lambda x: (x['date'], x['cycle_no']))
        payload = {
            'cycles': out_cycles,
            'summary': {
                'capture_count': len(caps_in),
                'cycle_count': n,
                'iv_cycle_count': iv_count,
                'avg_iv_sec': int(sum_iv / iv_count) if iv_count else 0,
                'avg_sr_sec': int(sum_sr / n) if n else 0,
                'avg_dl_sec': int(sum_dl / n) if n else 0,
            },
        }
        cache.set(cache_key, payload, 60)
        return Response(payload)
