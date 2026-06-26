"""
SettlementDetail 의 region/boxes 값을 TerritoryBoxRecord 로 동기화.

동작:
  1) 각 SettlementDetail 마다 region 을 권역 코드로 해석해 해당 Territory 에
     TerritoryBoxRecord(date=settlement.period_start~period_end, box_count) 를 upsert.
     기간이 여러 날이면 날수로 나눠 분배.
  2) 정산 매칭되는 region 이 없는 권역들도 동일 날짜 범위의 mock 박스수를 생성
     (운행기록 없어도 권역 상세에서 박스 그래프가 보이도록).

사용: python manage.py sync_box_records [--clear] [--no-mock]
"""
import random
from datetime import timedelta, date as date_cls
from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.settlement.models import SettlementDetail
from apps.territory.models import Territory, TerritoryBoxRecord


class Command(BaseCommand):
    help = 'SettlementDetail → TerritoryBoxRecord 동기화 (권역 코드로 매칭)'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='기존 TerritoryBoxRecord 전부 삭제 후 재생성')
        parser.add_argument('--no-mock', action='store_true',
                            help='정산 매칭이 없는 권역은 비워둔다 (기본은 mock 생성)')

    def handle(self, *args, **opts):
        if opts['clear']:
            n, _ = TerritoryBoxRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'기존 TerritoryBoxRecord 삭제: {n}건'))

        # 권역 코드 → Territory 캐시
        t_by_code = {t.code: t for t in Territory.objects.all()}

        created = updated = skipped = 0
        # 같은 (territory, date) 에 여러 SettlementDetail(여러 crew) 이 있을 수 있으니 합산
        accum = {}  # (territory_id, date) → total_boxes
        split_flag = {}

        for d in SettlementDetail.objects.select_related('settlement').iterator():
            region = (d.region or '').strip()
            t = t_by_code.get(region)
            if not t:
                skipped += 1
                continue
            settlement = d.settlement
            days = (settlement.period_end - settlement.period_start).days + 1
            if days <= 0:
                continue
            per_day = float(d.boxes) / days
            is_split = days > 1
            cur = settlement.period_start
            for _ in range(days):
                key = (t.id, cur)
                accum[key] = accum.get(key, 0.0) + per_day
                if is_split:
                    split_flag[key] = True
                cur += timedelta(days=1)

        for (tid, date), box_count in accum.items():
            _, was_created = TerritoryBoxRecord.objects.update_or_create(
                territory_id=tid, date=date,
                defaults={
                    'box_count': round(box_count, 2),
                    'is_split': split_flag.get((tid, date), False),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ 박스 기록 동기화 — 생성 {created}, 갱신 {updated}, '
            f'권역 매칭 실패(skip) {skipped}'
        ))

        if opts.get('no_mock'):
            return

        # ---------- mock fill for unmatched territories ----------
        matched_ids = {tid for (tid, _) in accum.keys()}
        all_dates = sorted({d for (_, d) in accum.keys()}) if accum else []
        if not all_dates:
            # 정산이 전혀 없으면 오늘 기준 최근 7일 사용
            today = date_cls.today()
            all_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]

        mock_created = 0
        for t in Territory.objects.all():
            if t.id in matched_ids:
                continue
            # 권역 코드 기반 시드로 결정론적인 박스 값
            base = 80 + (hash(t.code) % 180)  # 80~260
            rng = random.Random(t.code)
            for d in all_dates:
                # 날짜별 소폭 변동 (±20)
                boxes = max(0, base + rng.randint(-25, 25))
                _, was_created = TerritoryBoxRecord.objects.update_or_create(
                    territory=t, date=d,
                    defaults={'box_count': boxes, 'is_split': False},
                )
                if was_created:
                    mock_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Mock 박스 기록 생성 (정산 매칭 없는 권역): {mock_created}건'
        ))
