"""
카메라 캡처 위치 클러스터 기반 데모 권역 생성.

사용: python manage.py seed_demo_territories_from_captures [--team A] [--cells 3]

카메라 캡처 포인트들을 격자(~400m) 로 묶어 가장 포인트가 많은 cell 을 골라
해당 범위 + 패딩으로 사각 폴리곤 생성, 지정된 팀에 배정.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.accounts.models import Team
from apps.tracking.models import CameraCapture
from apps.territory.models import Territory, extract_group_letter


class Command(BaseCommand):
    help = '카메라 캡처 위치 기반 데모 권역 생성'

    def add_arguments(self, parser):
        parser.add_argument('--team', default='A')
        parser.add_argument('--cells', type=int, default=3,
                            help='생성할 권역 개수')

    def handle(self, *args, **opts):
        team = Team.objects.filter(code=opts['team']).first()
        if not team:
            self.stdout.write(self.style.ERROR(f'팀 {opts["team"]} 없음'))
            return

        caps = list(CameraCapture.objects.filter(
            lat__isnull=False, lon__isnull=False,
        ).values_list('lat', 'lon'))

        if not caps:
            self.stdout.write(self.style.WARNING('카메라 캡처 없음 - 종료'))
            return

        # 격자 셀 크기 ~= 400m (위도 약 0.0036, 경도 약 0.0045 at 37°)
        cell_lat, cell_lon = 0.004, 0.005
        buckets = defaultdict(list)
        for lat, lon in caps:
            key = (int(lat / cell_lat), int(lon / cell_lon))
            buckets[key].append((lat, lon))

        top_cells = sorted(buckets.values(), key=len, reverse=True)[:opts['cells']]
        self.stdout.write(f'팀 {team.code} / 후보 cell {len(buckets)}개 → 상위 {len(top_cells)}개 채택')

        for i, pts in enumerate(top_cells, 1):
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]
            pad = 0.003  # ~300m 패딩
            min_lat = min(lats) - pad
            max_lat = max(lats) + pad
            min_lon = min(lons) - pad
            max_lon = max(lons) + pad

            geom = {
                'type': 'Polygon',
                'coordinates': [[
                    [min_lon, min_lat],
                    [max_lon, min_lat],
                    [max_lon, max_lat],
                    [min_lon, max_lat],
                    [min_lon, min_lat],
                ]],
            }
            # 권역 코드: 30A1, 30A2, 30A3 ... (기존 10A/20A 와 구분되는 데모 권역)
            code = f'30{team.code}{i}'
            Territory.objects.update_or_create(
                code=code,
                defaults={
                    'team': team,
                    'group_letter': extract_group_letter(code),
                    'geometry': geom,
                    'color': '#F59E0B',  # 데모 권역: 오렌지
                },
            )
            self.stdout.write(
                f'  + {code}  pts={len(pts)}  '
                f'bbox=({min_lat:.4f},{min_lon:.4f})-({max_lat:.4f},{max_lon:.4f})'
            )

        self.stdout.write(self.style.SUCCESS(f'✅ 데모 권역 {len(top_cells)}개 생성/갱신'))
