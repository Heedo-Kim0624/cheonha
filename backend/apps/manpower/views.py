import csv as _csv
import io
import math
import re
from urllib.request import Request, urlopen

from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from openpyxl import load_workbook

from .models import Manpower
from .serializers import ManpowerSerializer
from .services import geocode_address


# 고정 공유 시트 URL (공유: 링크 있는 사람 뷰어 이상)
FIXED_MANPOWER_SHEET_URL = (
    'https://docs.google.com/spreadsheets/d/'
    '18HgZlaTuqyYtDkNCEhL-V18tnS6HRPMpyNIdygdr6AI/edit?gid=0#gid=0'
)


def _normalize_sheet_to_csv_url(url: str) -> str:
    """
    다양한 Google Sheets 링크를 CSV export URL 로 표준화한다.
    - 이미 CSV export 형식이면 그대로
    - 'Publish to web' URL (/pub?output=csv) 은 그대로
    - 일반 공유/편집 URL 이면 시트 ID + gid 를 추출해 export?format=csv URL 생성
    """
    url = url.strip()
    if not url:
        return ''
    if 'format=csv' in url or '/pub' in url and 'output=csv' in url:
        return url
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9\-_]+)', url)
    if not m:
        return url  # 형식 알 수 없으면 그대로 시도
    sheet_id = m.group(1)
    gid = '0'
    gid_m = re.search(r'[#?&]gid=(\d+)', url)
    if gid_m:
        gid = gid_m.group(1)
    return f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'


def _fetch_url(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (cheonha-manpower/1.0)',
    })
    with urlopen(req, timeout=timeout) as r:
        raw = r.read()
    # Google Sheets CSV 는 UTF-8 기본
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('cp949', errors='ignore')


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


class ManpowerViewSet(viewsets.ModelViewSet):
    queryset = Manpower.objects.filter(is_active=True)
    serializer_class = ManpowerSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    # ---------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def geocode(self, request, pk=None):
        """단일 인력의 거주지 주소를 VWorld 로 지오코딩."""
        mp = self.get_object()
        lat, lon, err = geocode_address(mp.address)
        mp.lat, mp.lon = lat, lon
        mp.geocoded_at = timezone.now() if lat is not None else mp.geocoded_at
        mp.geocode_error = err
        mp.save(update_fields=['lat', 'lon', 'geocoded_at', 'geocode_error'])
        return Response(ManpowerSerializer(mp).data)

    @action(detail=False, methods=['post'], url_path='geocode_all')
    def geocode_all(self, request):
        """좌표 없는 전 인력 일괄 지오코딩."""
        only_missing = request.data.get('only_missing', True)
        qs = self.get_queryset()
        if only_missing:
            qs = qs.filter(lat__isnull=True)
        ok = fail = 0
        for mp in qs.iterator():
            if not mp.address:
                continue
            lat, lon, err = geocode_address(mp.address)
            mp.lat, mp.lon = lat, lon
            mp.geocoded_at = timezone.now() if lat is not None else mp.geocoded_at
            mp.geocode_error = err
            mp.save(update_fields=['lat', 'lon', 'geocoded_at', 'geocode_error'])
            if lat is not None:
                ok += 1
            else:
                fail += 1
        return Response({'ok': ok, 'fail': fail})

    # ---------------------------------------------------------------
    def _upsert_rows(self, rows):
        """
        rows: 2D list-like (header + data rows) — 헤더 유연 매칭.
        반환: (created, updated)
        """
        if not rows:
            return (0, 0, '빈 데이터')
        header = [str(c or '').strip() for c in rows[0]]

        def col_index(*keywords):
            for i, h in enumerate(header):
                for kw in keywords:
                    if kw in h:
                        return i
            return -1

        idx_name = col_index('이름', '성명', 'name')
        idx_veh = col_index('차량')
        idx_exp = col_index('경력', 'exp')
        idx_addr = col_index('거주', '주소', 'address')
        idx_phone = col_index('휴대', '전화', '연락', 'phone')

        if idx_name < 0:
            return (0, 0, '이름 컬럼을 찾지 못했습니다')

        created = updated = 0
        for row in rows[1:]:
            if row is None:
                continue
            def cell(i):
                return row[i] if 0 <= i < len(row) else None
            name = str(cell(idx_name) or '').strip()
            if not name:
                continue
            phone = str(cell(idx_phone) or '').strip() if idx_phone >= 0 else ''
            addr = str(cell(idx_addr) or '').strip() if idx_addr >= 0 else ''
            exp_raw = cell(idx_exp) if idx_exp >= 0 else 0
            veh_raw = cell(idx_veh) if idx_veh >= 0 else ''

            try:
                exp = int(float(str(exp_raw).replace('년', '').strip() or 0))
            except Exception:
                exp = 0

            has_veh = False
            if veh_raw:
                s = str(veh_raw).strip().lower()
                has_veh = s in ('y', 'yes', 'o', 'true', '1', '유', '있', '있음')

            defaults = dict(
                name=name, phone=phone, address=addr,
                experience_years=exp, has_vehicle=has_veh,
            )

            if phone:
                _, was_created = Manpower.objects.update_or_create(
                    phone=phone, defaults=defaults,
                )
            else:
                _, was_created = Manpower.objects.update_or_create(
                    name=name, phone='', defaults=defaults,
                )
            if was_created:
                created += 1
            else:
                updated += 1
        return (created, updated, '')

    @action(detail=False, methods=['post'], url_path='import_xlsx',
            parser_classes=[MultiPartParser, FormParser])
    def import_xlsx(self, request):
        """xlsx 파일 업로드 → upsert (공유시트 대체용 수동 업로드 경로)."""
        f = request.FILES.get('file')
        if not f:
            return Response({'detail': 'file 파라미터 필요'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            wb = load_workbook(f, read_only=True, data_only=True)
        except Exception as e:
            return Response({'detail': f'xlsx 파싱 실패: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        rows = list(wb.active.iter_rows(values_only=True))
        wb.close()
        created, updated, err = self._upsert_rows(rows)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'created': created, 'updated': updated})

    @action(detail=False, methods=['get'], url_path='sheet', permission_classes=[permissions.IsAuthenticated])
    def sheet(self, request):
        """
        고정 공유 시트를 CSV 로 가져와 headers + rows 로 반환 (DB 저장 없이 실시간 프록시).
        주기적으로 호출되면 시트 변경이 즉시 웹에 반영된다.
        """
        csv_url = _normalize_sheet_to_csv_url(FIXED_MANPOWER_SHEET_URL)
        try:
            content = _fetch_url(csv_url)
        except Exception as e:
            return Response(
                {'detail': f'시트 가져오기 실패: {e}', 'csv_url': csv_url},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if content[:200].lstrip().lower().startswith('<!doctype html') or '<html' in content[:200].lower():
            return Response(
                {'detail': '시트가 비공개입니다. 공유 → "링크 있는 사용자 모두 뷰어" 로 설정해주세요.',
                 'csv_url': csv_url},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            reader = _csv.reader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            return Response({'detail': f'CSV 파싱 실패: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        if not rows:
            return Response({'headers': [], 'rows': []})
        headers = [str(c or '') for c in rows[0]]
        data_rows = [[str(c or '') for c in r] for r in rows[1:]]
        return Response({'headers': headers, 'rows': data_rows})

    @action(detail=False, methods=['post'], url_path='sync_sheet',
            parser_classes=[JSONParser])
    def sync_sheet(self, request):
        """
        공유 구글 시트(URL) → CSV export → upsert.
        허용 URL:
          1) 'Publish to web' → CSV 직접 링크
          2) 편집/공유 URL — 시트가 '링크 있는 사람 보기' 이상으로 공개되어야 함
        첫 번째 시트(또는 URL 의 gid) 를 헤더 포함 CSV 로 읽어 들인다.
        """
        url = (request.data.get('url') or '').strip()
        if not url:
            return Response({'detail': 'url 파라미터 필요'}, status=status.HTTP_400_BAD_REQUEST)

        csv_url = _normalize_sheet_to_csv_url(url)
        try:
            content = _fetch_url(csv_url)
        except Exception as e:
            return Response(
                {'detail': f'시트 가져오기 실패 — 공개 설정을 확인하세요: {e}',
                 'csv_url': csv_url},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Google Sheets 가 오류 시 HTML 을 내려줄 수 있음 → 앞부분 검사
        if content[:200].lstrip().lower().startswith('<!doctype html') or '<html' in content[:200].lower():
            return Response(
                {'detail': '시트가 비공개이거나 URL 이 잘못되었습니다. '
                           '공유 설정을 "링크 있는 사람 모두 뷰어" 이상으로 바꾸거나 '
                           '"웹에 게시 → CSV" 링크를 사용해주세요.',
                 'csv_url': csv_url},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reader = _csv.reader(io.StringIO(content))
            rows = list(reader)
        except Exception as e:
            return Response({'detail': f'CSV 파싱 실패: {e}'},
                            status=status.HTTP_400_BAD_REQUEST)

        created, updated, err = self._upsert_rows(rows)
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'created': created, 'updated': updated,
            'csv_url': csv_url, 'row_count': max(0, len(rows) - 1),
        })

    # ---------------------------------------------------------------
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        좌표 근처 인력 조회.
        ?lat=..&lon=..&radius_m=3000
        반환: 지오코딩된 인력 중 거리순 정렬 (해당 반경 내).
        """
        try:
            lat = float(request.query_params.get('lat'))
            lon = float(request.query_params.get('lon'))
        except (TypeError, ValueError):
            return Response({'detail': 'lat/lon 필수'}, status=status.HTTP_400_BAD_REQUEST)
        radius_m = float(request.query_params.get('radius_m') or 3000)

        out = []
        for mp in self.get_queryset().exclude(lat__isnull=True).iterator():
            d = _haversine_m(lat, lon, mp.lat, mp.lon)
            if d <= radius_m:
                data = ManpowerSerializer(mp).data
                data['distance_m'] = round(d, 1)
                out.append(data)
        out.sort(key=lambda x: x['distance_m'])
        return Response(out)
