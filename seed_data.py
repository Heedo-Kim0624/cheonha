from decimal import Decimal
from datetime import date, timedelta
from apps.accounts.models import Team, User
from apps.crew.models import CrewMember
from apps.partner.models import Partner
from apps.region.models import Region
from apps.settlement.models import Settlement, SettlementDetail
from apps.dispatch.models import DispatchUpload, DispatchRecord
from django.core.files.base import ContentFile

# 1. 팀 2개
team_a, _ = Team.objects.update_or_create(
    code='A', defaults={'name': 'A조', 'receive_price': 3500, 'pay_price': 0, 'default_overtime_cost': 50000, 'is_active': True}
)
team_h, _ = Team.objects.update_or_create(
    code='H', defaults={'name': 'H조', 'receive_price': 3800, 'pay_price': 0, 'default_overtime_cost': 45000, 'is_active': True}
)
print('Teams:', Team.objects.count())

# 2. 팀장 계정
tl, created = User.objects.get_or_create(
    username='teamleader',
    defaults={'email': 'tl@cheonha.local', 'role': 'TEAM_LEADER', 'team': team_a, 'first_name': '홍길동', 'is_active': True}
)
if created:
    tl.set_password('test1234!')
    tl.save()
print('TeamLeader:', tl.username, 'team:', tl.team.code if tl.team else None)

# 3. 파트너
partner, _ = Partner.objects.get_or_create(name='천하택배', defaults={'is_active': True})

# 4. 배송원
crew_data_a = [('김민수', '2500'), ('이영희', '2600'), ('박철수', '2700'), ('최지훈', '2800'), ('정수빈', '2500')]
crew_data_h = [('강지우', '2700'), ('견강현', '2800'), ('구자룡', '2900'), ('권도연', '2700'), ('김성민', '2800')]
for name, pay in crew_data_a:
    CrewMember.objects.update_or_create(
        code=name, team=team_a,
        defaults={'name': name, 'phone': '010-1111-2222', 'pay_price': Decimal(pay), 'partner': partner, 'is_active': True, 'is_new': False}
    )
for name, pay in crew_data_h:
    CrewMember.objects.update_or_create(
        code=name, team=team_h,
        defaults={'name': name, 'phone': '010-3333-4444', 'pay_price': Decimal(pay), 'partner': partner, 'is_active': True, 'is_new': False}
    )
print('Crew:', CrewMember.objects.count())

# 5. 권역
for code, team in [('10A1', team_a), ('10A2', team_a), ('20A1', team_a), ('10H1', team_h), ('10H2', team_h), ('20H3', team_h)]:
    Region.objects.get_or_create(code=code, defaults={'team': team, 'name': code, 'is_active': True})
print('Regions:', Region.objects.count())

# 6. 더미 배차 + 정산 (최근 7일)
today = date.today()
for i in range(7):
    d = today - timedelta(days=i)
    for team, crews, regions in [(team_a, crew_data_a, ['10A1', '10A2', '20A1']), (team_h, crew_data_h, ['10H1', '10H2', '20H3'])]:
        upload, created = DispatchUpload.objects.get_or_create(
            team=team, dispatch_date=d,
            defaults={
                'original_filename': f'배차현황_{d}_{team.code}.xlsx',
                'status': 'CONFIRMED', 'total_rows': len(crews), 'success_rows': len(crews)
            }
        )
        if not created:
            continue
        upload.file.save(f'dispatch_{d}_{team.code}.txt', ContentFile(b'dummy'))

        settlement, _ = Settlement.objects.get_or_create(
            team=team, period_start=d, period_end=d,
            defaults={'status': 'CONFIRMED'}
        )

        total_r = total_p = total_o = total_pr = Decimal('0')
        for idx, (name, pay_str) in enumerate(crews):
            region = regions[idx % len(regions)]
            boxes = 80 + idx * 10 + i * 5
            crew = CrewMember.objects.get(code=name, team=team)
            recv = team.receive_price * boxes
            pay = Decimal(pay_str) * boxes
            ot = Decimal('0')
            profit = recv - pay - ot

            DispatchRecord.objects.create(
                upload=upload, row_num=idx + 2, manager_name=name,
                sub_region=region, boxes=boxes, original_boxes=boxes, is_valid=True
            )
            SettlementDetail.objects.create(
                settlement=settlement, dispatch_upload=upload, crew_member=crew,
                region=region, delivery_type='SAME_DAY', boxes=boxes,
                receive_amount=recv, pay_amount=pay, overtime_cost=ot, profit=profit
            )
            total_r += recv
            total_p += pay
            total_o += ot
            total_pr += profit

        settlement.total_receive = total_r
        settlement.total_pay = total_p
        settlement.total_overtime = total_o
        settlement.total_profit = total_pr
        settlement.save()

print('Uploads:', DispatchUpload.objects.count())
print('Settlements:', Settlement.objects.count())
print('Details:', SettlementDetail.objects.count())
print('DONE')
