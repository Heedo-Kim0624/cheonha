"""
더미 권역 폴리곤 생성 — 기존 팀(A/H/R)에 매핑.

사용: python manage.py seed_territories [--clear]
  --clear : 기존 Territory 전부 삭제 후 새로 생성
  --drop-dummy-teams : YDPA/GNMB/SBGC 같은 과거 더미 팀 레코드 삭제
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Team
from apps.territory.models import Territory, extract_group_letter


# team code(기존 DB 팀) → (지역이름, 색, 권역 정의[(code, lon, lat, w, h), ...])
TERRITORIES_BY_TEAM_CODE = {
    # 권역 코드는 SettlementDetail.region 과 일치하도록 맞춤 (박스수 자동 연동)
    'A': {
        'region_name': '영등포',
        'color': '#8B5CF6',
        'specs': [
            ('10A1', 126.905, 37.520, 0.012, 0.008),
            ('10A2', 126.918, 37.520, 0.012, 0.008),
            ('20A1', 126.905, 37.512, 0.012, 0.008),
            ('20A2', 126.918, 37.512, 0.012, 0.008),
        ],
    },
    'H': {
        'region_name': '강남',
        'color': '#06B6D4',
        'specs': [
            ('10H1', 127.035, 37.508, 0.014, 0.009),
            ('10H2', 127.050, 37.508, 0.014, 0.009),
            ('20H3', 127.035, 37.498, 0.014, 0.009),
            ('20H4', 127.050, 37.498, 0.014, 0.009),
        ],
    },
    'R': {
        'region_name': '성북',
        'color': '#EC4899',
        'specs': [
            ('10R1', 126.995, 37.590, 0.014, 0.009),
            ('10R2', 127.010, 37.590, 0.014, 0.009),
            ('20R3', 127.025, 37.590, 0.014, 0.009),
            ('10R4', 127.002, 37.580, 0.014, 0.009),
        ],
    },
}

# 과거 임시로 생성된 더미 팀 코드 — drop-dummy-teams 로 정리 가능
DUMMY_TEAM_CODES = ['YDPA', 'GNMB', 'SBGC']


def _make_square_polygon(cx, cy, w, h):
    hx, hy = w / 2, h / 2
    ring = [
        [cx - hx, cy - hy],
        [cx + hx, cy - hy],
        [cx + hx, cy + hy],
        [cx - hx, cy + hy],
        [cx - hx, cy - hy],
    ]
    return {'type': 'Polygon', 'coordinates': [ring]}


class Command(BaseCommand):
    help = '기존 팀(A/H/R)에 배정된 더미 권역 폴리곤 생성'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true')
        parser.add_argument('--drop-dummy-teams', action='store_true',
                            help=f'{", ".join(DUMMY_TEAM_CODES)} 팀 레코드 삭제')

    def handle(self, *args, **opts):
        if opts['clear']:
            n, _ = Territory.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'기존 Territory 삭제: {n}건'))

        if opts['drop_dummy_teams']:
            qs = Team.objects.filter(code__in=DUMMY_TEAM_CODES)
            if qs.exists():
                # 해당 팀에 걸린 territory, crew 등 FK 는 SET_NULL 로 되어 있으므로 안전
                codes = list(qs.values_list('code', flat=True))
                qs.delete()
                self.stdout.write(self.style.WARNING(f'더미 팀 삭제: {codes}'))

        with transaction.atomic():
            total = 0
            for team_code, cfg in TERRITORIES_BY_TEAM_CODE.items():
                team = Team.objects.filter(code=team_code).first()
                if not team:
                    self.stdout.write(self.style.ERROR(f'  ⚠ 팀 {team_code} 없음 - 건너뜀'))
                    continue
                for (code, cx, cy, w, h) in cfg['specs']:
                    Territory.objects.update_or_create(
                        code=code,
                        defaults={
                            'team': team,
                            'group_letter': extract_group_letter(code),
                            'geometry': _make_square_polygon(cx, cy, w, h),
                            'color': cfg['color'],
                        },
                    )
                    total += 1
                    self.stdout.write(f'  · {team.code}({cfg["region_name"]}) / {code}')

        self.stdout.write(self.style.SUCCESS(f'✅ Territory {total}개 생성/갱신'))
