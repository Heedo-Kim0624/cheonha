import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.management import BaseCommand, call_command
from django.db import transaction

from openpyxl import load_workbook

from apps.accounts.models import Team
from apps.crew.models import CrewMember, OvertimeSetting
from apps.dispatch.models import DispatchRecord, DispatchUpload
from apps.inquiry.models import InquiryMessage, SettlementInquiry
from apps.manpower.models import Manpower
from apps.mobile.models import MobileAppUser, MobilePassword
from apps.partner.models import Partner
from apps.region.models import Region, RegionPrice
from apps.settlement.models import Settlement, SettlementDetail
from apps.territory.models import Territory, TerritoryBoxRecord, extract_group_letter
from apps.tracking.models import TrackingSession


CREWS = [
    {'code': 'P001', 'name': '박철수', 'team': 'X', 'vehicle': '서울90바8676', 'phone': '010-1000-0001', 'pay': 920},
    {'code': 'P002', 'name': '김민준', 'team': 'X', 'vehicle': '서울12배1234', 'phone': '010-1000-0002', 'pay': 900},
    {'code': 'P003', 'name': '이서연', 'team': 'X', 'vehicle': '서울34사5678', 'phone': '010-1000-0003', 'pay': 910},
    {'code': 'P004', 'name': '장원철', 'team': 'R', 'vehicle': '서울56아2468', 'phone': '010-1000-0004', 'pay': 900},
    {'code': 'P005', 'name': '최유진', 'team': 'R', 'vehicle': '서울78자1357', 'phone': '010-1000-0005', 'pay': 890},
]


def _safe_int(value, default=0):
    try:
        text = str(value or '').replace(',', '').strip()
        if not text or text == '-':
            return default
        return int(float(text))
    except Exception:
        return default


def _split_region_codes(value):
    return [x.strip() for x in str(value or '').split(',') if x and x.strip() and x.strip() != '-']


def _group_from_region(code):
    return extract_group_letter(code)


def _norm_name(value):
    text = str(value or '').strip()
    return text[2:] if text.startswith('EV') and len(text) > 2 else text


def _find_dir(name):
    base = Path(settings.BASE_DIR)
    candidates = [
        base / name,
        base.parent / name,
        Path('/app') / name,
        Path('/') / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _date_from_filename(path):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', path.name)
    if not m:
        return None
    return datetime.strptime(m.group(1), '%Y-%m-%d').date()


def _load_dispatch_rows(dispatch_dir):
    rows = []
    if not dispatch_dir or not dispatch_dir.exists():
        return rows

    for path in sorted(dispatch_dir.glob('*.xlsx')):
        file_date = _date_from_filename(path)
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if hasattr(ws, 'reset_dimensions'):
            ws.reset_dimensions()
        for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if idx == 1:
                continue
            delivery_type = str(row[0] or '').strip() if len(row) > 0 else ''
            partner_name = str(row[1] or '').strip() if len(row) > 1 else ''
            manager_name = _norm_name(row[2] if len(row) > 2 else '')
            sub_region = str(row[3] or '').strip() if len(row) > 3 else ''
            detail_region = str(row[4] or '').strip() if len(row) > 4 else ''
            households = _safe_int(row[5] if len(row) > 5 else 0)
            boxes = _safe_int(row[6] if len(row) > 6 else 0)
            if not manager_name or not boxes:
                continue
            codes = _split_region_codes(sub_region)
            if not codes:
                continue
            rows.append({
                'source_file': path.name,
                'source_date': file_date,
                'delivery_type': delivery_type,
                'partner_name': partner_name,
                'manager_name': manager_name,
                'sub_region': ', '.join(codes),
                'detail_region': detail_region,
                'households': households,
                'boxes': boxes,
            })
        wb.close()
    return rows


def _fixture_path():
    return Path(__file__).resolve().parents[2] / 'fixtures' / 'xr_territories.json'


def _distance_m(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(x)))


class Command(BaseCommand):
    help = 'X/R GPKG 기반 권역 + 약 일주일치 배차/정산/추적 데모 데이터를 생성'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='기존 업무 데이터를 삭제 후 생성')
        parser.add_argument('--start-date', default='2026-04-10')
        parser.add_argument('--days', type=int, default=7)
        parser.add_argument('--skip-tracking', action='store_true')

    def handle(self, *args, **opts):
        start_date = datetime.strptime(opts['start_date'], '%Y-%m-%d').date()
        days = max(1, int(opts['days']))

        with transaction.atomic():
            if opts['clear']:
                self._clear_data()

            teams = self._create_teams()
            territories = self._load_territories(teams)
            crews = self._create_crews(teams)
            self._create_manpower(territories)
            dispatch_rows = _load_dispatch_rows(_find_dir('천하데이터'))
            self._create_dispatch_and_settlements(start_date, days, teams, crews, territories, dispatch_rows)

        if not opts['skip_tracking']:
            self._seed_tracking(start_date + timedelta(days=days - 1))

        self.stdout.write(self.style.SUCCESS(
            f'XR 데모 데이터 생성 완료: Team {Team.objects.count()} / '
            f'Territory {Territory.objects.count()} / Crew {CrewMember.objects.count()} / '
            f'Dispatch {DispatchUpload.objects.count()}'
        ))

    def _clear_data(self):
        InquiryMessage.objects.all().delete()
        SettlementInquiry.objects.all().delete()
        MobilePassword.objects.all().delete()
        MobileAppUser.objects.all().delete()
        TrackingSession.objects.all().delete()
        TerritoryBoxRecord.objects.all().delete()
        Territory.objects.all().delete()
        SettlementDetail.objects.all().delete()
        Settlement.objects.all().delete()
        OvertimeSetting.objects.all().delete()
        DispatchRecord.objects.all().delete()
        DispatchUpload.objects.all().delete()
        CrewMember.objects.all().delete()
        RegionPrice.objects.all().delete()
        Region.objects.all().delete()
        Manpower.objects.all().delete()
        Partner.objects.all().delete()
        Team.objects.all().delete()
        self.stdout.write(self.style.WARNING('기존 업무 데이터 삭제 완료'))

    def _create_teams(self):
        specs = {
            'X': {'name': 'X조', 'receive_price': 1200, 'pay_price': 900, 'color': '#2563EB'},
            'R': {'name': 'R조', 'receive_price': 1180, 'pay_price': 890, 'color': '#EC4899'},
        }
        teams = {}
        for code, spec in specs.items():
            team, _ = Team.objects.update_or_create(
                code=code,
                defaults={
                    'name': spec['name'],
                    'receive_price': spec['receive_price'],
                    'pay_price': spec['pay_price'],
                    'default_overtime_cost': 30000,
                    'is_active': True,
                },
            )
            teams[code] = team
        return teams

    def _load_territories(self, teams):
        data = json.loads(_fixture_path().read_text(encoding='utf-8'))
        by_group = defaultdict(list)
        for item in data:
            code = item['code']
            group = _group_from_region(code)
            if group not in teams:
                continue
            t, _ = Territory.objects.update_or_create(
                code=code,
                defaults={
                    'team': teams[group],
                    'geometry': item['geometry'],
                    'color': item.get('color') or ('#2563EB' if group == 'X' else '#EC4899'),
                    'note': 'GPKG 기반 데모 권역',
                },
            )
            Region.objects.update_or_create(
                code=code,
                team=teams[group],
                defaults={'name': code, 'is_active': True},
            )
            by_group[group].append(t)

        for group, rows in by_group.items():
            for region in Region.objects.filter(team=teams[group]):
                RegionPrice.objects.update_or_create(
                    region=region,
                    delivery_type='SAME_DAY',
                    start_date=datetime(2026, 4, 1).date(),
                    defaults={
                        'receive_price': teams[group].receive_price,
                        'pay_price': teams[group].pay_price,
                    },
                )
            rows.sort(key=lambda x: x.code)
        return by_group

    def _create_crews(self, teams):
        partner, _ = Partner.objects.get_or_create(name='이브이앤솔루션 주식회사')
        out = defaultdict(list)
        for spec in CREWS:
            team = teams[spec['team']]
            crew, _ = CrewMember.objects.update_or_create(
                code=spec['code'],
                team=team,
                defaults={
                    'name': spec['name'],
                    'phone': spec['phone'],
                    'vehicle_number': spec['vehicle'],
                    'partner': partner,
                    'pay_price': spec['pay'],
                    'is_active': True,
                    'is_new': False,
                    'region': '',
                },
            )
            mobile, _ = MobileAppUser.objects.update_or_create(
                crew_member=crew,
                defaults={
                    'name': crew.name,
                    'team_code': team.code,
                    'status': MobileAppUser.Status.APPROVED,
                    'is_active': True,
                },
            )
            MobilePassword.objects.update_or_create(
                mobile_user=mobile,
                defaults={'password_hash': make_password('0000'), 'is_default': True},
            )
            out[team.code].append(crew)
        return out

    def _create_manpower(self, territories):
        center = {}
        for group, rows in territories.items():
            if not rows:
                continue
            center[group] = (
                sum(t.centroid_lat or 0 for t in rows) / len(rows),
                sum(t.centroid_lon or 0 for t in rows) / len(rows),
            )
        samples = [
            ('장원철', True, '서울56아2468', 40, '010-2000-0001', 'R', 42),
            ('강민호', True, '서울22가4567', 8, '010-2000-0002', 'X', 36),
            ('유지민', False, '', 3, '010-2000-0003', 'X', 29),
            ('한도윤', True, '서울44나8899', 12, '010-2000-0004', 'R', 47),
            ('서지후', True, '서울77다1122', 5, '010-2000-0005', 'X', 33),
        ]
        for i, (name, has_vehicle, vehicle, exp, phone, group, age) in enumerate(samples):
            lat, lon = center.get(group, (37.5, 127.0))
            Manpower.objects.update_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'has_vehicle': has_vehicle,
                    'vehicle_number': vehicle,
                    'experience_years': exp,
                    'address': f'{group}조 권역 인근',
                    'lat': lat + 0.003 * ((i % 3) - 1),
                    'lon': lon + 0.003 * (i - 2),
                    'note': f'데모 나이 {age}세',
                    'is_active': True,
                },
            )

    def _create_dispatch_and_settlements(self, start_date, days, teams, crews, territories, dispatch_rows):
        r_rows = [r for r in dispatch_rows if any(_group_from_region(c) == 'R' for c in _split_region_codes(r['sub_region']))]
        if not r_rows:
            r_rows = []
            for i, t in enumerate(territories['R'][:12]):
                r_rows.append({'delivery_type': 'DP(다회차)', 'partner_name': '이브이앤솔루션 주식회사',
                               'manager_name': 'R데모', 'sub_region': t.code, 'detail_region': t.code,
                               'households': 40 + i, 'boxes': 80 + i * 4})

        for offset in range(days):
            d = start_date + timedelta(days=offset)
            self._create_team_day('X', d, teams['X'], crews['X'], territories['X'])
            selected_r = [r_rows[(offset * 2 + i) % len(r_rows)] for i in range(min(4, len(r_rows)))]
            self._create_team_day('R', d, teams['R'], crews['R'], territories['R'], selected_r)

    def _create_team_day(self, group, d, team, crew_list, territory_list, source_rows=None):
        upload = DispatchUpload.objects.create(
            original_filename=f'XR_DEMO_{group}_{d.isoformat()}.xlsx',
            dispatch_date=d,
            team=team,
            total_rows=0,
            success_rows=0,
            error_rows=0,
            status='CONFIRMED',
        )
        upload.file.save(f'XR_DEMO_{group}_{d.isoformat()}.txt', ContentFile(b'demo'), save=True)

        records = []
        if source_rows:
            for idx, row in enumerate(source_rows):
                crew = crew_list[idx % len(crew_list)]
                codes = [c for c in _split_region_codes(row['sub_region']) if _group_from_region(c) == group]
                codes = [c for c in codes if any(t.code == c for t in territory_list)]
                if not codes:
                    codes = [territory_list[(idx + len(records)) % len(territory_list)].code]
                records.append((crew, ', '.join(codes), row['boxes'], row['households'], row.get('detail_region', '')))
        else:
            for idx, crew in enumerate(crew_list):
                first = (idx * 2) % max(1, len(territory_list))
                codes = [territory_list[(first + j) % len(territory_list)].code for j in range(2)]
                boxes = 84 + idx * 13 + (d.day % 7) * 5
                households = max(1, int(boxes * 0.48))
                records.append((crew, ', '.join(codes), boxes, households, ', '.join(codes)))

        partner_name = '이브이앤솔루션 주식회사'
        partner, _ = Partner.objects.get_or_create(name=partner_name)
        total_rows = 0
        for row_num, (crew, region_text, boxes, households, detail_region) in enumerate(records, start=2):
            total_rows += 1
            crew.partner = partner
            crew.region = region_text
            crew.save(update_fields=['partner', 'region'])
            DispatchRecord.objects.create(
                upload=upload,
                row_num=row_num,
                delivery_type='DP(다회차)',
                partner_name=partner_name,
                manager_name=crew.code,
                sub_region=region_text,
                detail_region=detail_region or region_text,
                households=households,
                boxes=boxes,
                original_boxes=boxes,
                is_valid=True,
            )

        upload.total_rows = total_rows
        upload.success_rows = total_rows
        upload.save(update_fields=['total_rows', 'success_rows'])
        self._create_settlement(upload)

    def _create_settlement(self, upload):
        team = upload.team
        settlement, _ = Settlement.objects.get_or_create(
            team=team,
            period_start=upload.dispatch_date,
            period_end=upload.dispatch_date,
            defaults={'status': 'CONFIRMED', 'note': 'XR 데모 정산'},
        )
        settlement.details.filter(dispatch_upload=upload).delete()
        receive_price = Decimal(team.receive_price or 0)

        totals = defaultdict(Decimal)
        for rec in upload.records.filter(is_valid=True):
            crew = CrewMember.objects.filter(code=rec.manager_name, team=team).first()
            if not crew:
                continue
            codes = _split_region_codes(rec.sub_region)
            if not codes:
                continue
            per = rec.boxes // len(codes)
            rem = rec.boxes % len(codes)
            for i, code in enumerate(codes):
                boxes = per + (1 if i < rem else 0)
                pay_price = Decimal(crew.pay_price or team.pay_price or 0)
                receive_amount = receive_price * boxes
                pay_amount = pay_price * boxes
                detail = SettlementDetail.objects.create(
                    settlement=settlement,
                    dispatch_upload=upload,
                    crew_member=crew,
                    region=code,
                    delivery_type='SAME_DAY',
                    boxes=boxes,
                    receive_amount=receive_amount,
                    pay_amount=pay_amount,
                    overtime_cost=0,
                    other_cost=0,
                    profit=receive_amount - pay_amount,
                )
                totals['receive'] += detail.receive_amount
                totals['pay'] += detail.pay_amount
                totals['profit'] += detail.profit

        settlement.total_receive = totals['receive']
        settlement.total_pay = totals['pay']
        settlement.total_overtime = 0
        settlement.total_other_cost = 0
        settlement.total_profit = totals['profit']
        settlement.status = 'CONFIRMED'
        settlement.save()

    def _seed_tracking(self, target_date):
        try:
            call_command('seed_tracking', date=target_date.isoformat(), team='X', crew='P001')
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f'추적 세션 seed 건너뜀: {exc}'))
