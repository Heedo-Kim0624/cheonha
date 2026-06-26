import re
from collections import defaultdict
from decimal import Decimal

from apps.settlement.models import SettlementDetail


REGION_CODE_PATTERN = re.compile(r'(\d+)([A-Za-z])(\d+)')
DEFAULT_YONGCHA_PAY_PRICE = Decimal('3000')
ZERO_PERCENT = Decimal('0')


ROUND_FLAG_FIELDS = {
    1: 'round_1_is_yongcha',
    2: 'round_2_is_yongcha',
    3: 'round_3_is_yongcha',
}

REGULAR_TEAM_ROUND_PAY_FIELDS = {
    1: 'round_1_yongcha_pay_price',
    2: 'round_2_yongcha_pay_price',
    3: 'round_3_yongcha_pay_price',
}

YONGCHA_TEAM_ROUND_PAY_FIELDS = {
    1: 'yongcha_round_1_pay_price',
    2: 'yongcha_round_2_pay_price',
    3: 'yongcha_round_3_pay_price',
}

PERSONAL_ROUND_PAY_FIELDS = {
    1: 'personal_round_1_yongcha_pay_price',
    2: 'personal_round_2_yongcha_pay_price',
    3: 'personal_round_3_yongcha_pay_price',
}

REGULAR_FIXED_PAY_FIELDS = {
    1: 'regular_round_1_base_pay',
    2: 'regular_round_2_base_pay',
    3: 'regular_round_3_base_pay',
}


def round_flag_enabled(crew_member, round_no):
    field_name = ROUND_FLAG_FIELDS.get(round_no)
    if not field_name or not crew_member:
        return False
    return bool(getattr(crew_member, field_name, False))


def is_effective_yongcha(crew_member, round_no=None, explicit_yongcha=False):
    if explicit_yongcha:
        return True
    if not crew_member:
        return False
    if crew_member.is_yongcha:
        return True
    return round_flag_enabled(crew_member, round_no)


def _safe_decimal(value):
    return Decimal(str(value or 0))


def _team_general_yongcha_pay_price(team):
    if not team:
        return DEFAULT_YONGCHA_PAY_PRICE
    team_value = getattr(team, 'yongcha_pay_price', None)
    if Decimal(str(team_value or 0)) > 0:
        return _safe_decimal(team_value)
    return DEFAULT_YONGCHA_PAY_PRICE


def _team_regular_round_yongcha_pay_price(team, round_no=None):
    if team and round_no in REGULAR_TEAM_ROUND_PAY_FIELDS:
        round_value = getattr(team, REGULAR_TEAM_ROUND_PAY_FIELDS[round_no], None)
        if Decimal(str(round_value or 0)) > 0:
            return _safe_decimal(round_value)
    return _team_general_yongcha_pay_price(team)


def _team_yongcha_driver_round_pay_price(team, round_no=None):
    if team and round_no in YONGCHA_TEAM_ROUND_PAY_FIELDS:
        round_value = getattr(team, YONGCHA_TEAM_ROUND_PAY_FIELDS[round_no], None)
        if Decimal(str(round_value or 0)) > 0:
            return _safe_decimal(round_value)
    return None


def _member_personal_round_pay_price(crew_member, round_no=None):
    if not crew_member or round_no not in PERSONAL_ROUND_PAY_FIELDS:
        return None
    value = getattr(crew_member, PERSONAL_ROUND_PAY_FIELDS[round_no], None)
    if Decimal(str(value or 0)) > 0:
        return _safe_decimal(value)
    return None


def resolve_yongcha_pay_price(crew_member=None, team=None, round_no=None, explicit_yongcha=False):
    effective_team = team or getattr(crew_member, 'team', None)
    if explicit_yongcha or (crew_member and crew_member.is_yongcha):
        member_round_value = _member_personal_round_pay_price(crew_member, round_no=round_no)
        if member_round_value is not None and member_round_value > 0:
            return member_round_value
        team_round_value = _team_yongcha_driver_round_pay_price(effective_team, round_no=round_no)
        if team_round_value is not None and team_round_value > 0:
            return team_round_value
        member_value = _safe_decimal(getattr(crew_member, 'yongcha_pay_price', 0))
        if member_value > 0:
            return member_value
        return _team_general_yongcha_pay_price(effective_team)
    if crew_member and round_no and round_flag_enabled(crew_member, round_no):
        member_round_value = _member_personal_round_pay_price(crew_member, round_no=round_no)
        if member_round_value is not None and member_round_value > 0:
            return member_round_value
        return _team_regular_round_yongcha_pay_price(effective_team, round_no=round_no)
    return _team_regular_round_yongcha_pay_price(effective_team, round_no=round_no)


def resolve_regular_fixed_pay(crew_member=None, round_no=None):
    if not crew_member or round_no not in REGULAR_FIXED_PAY_FIELDS:
        return None
    value = _safe_decimal(getattr(crew_member, REGULAR_FIXED_PAY_FIELDS[round_no], 0))
    return value if value > 0 else None


def resolve_yongcha_group_pay(crew_member=None, round_no=None, total_households=0):
    pay_group = getattr(crew_member, 'yongcha_pay_group', None)
    if not pay_group or round_no not in (1, 2, 3):
        return None

    base_pay = _safe_decimal(getattr(pay_group, f'round_{round_no}_base_pay', 0))
    base_households = int(getattr(pay_group, f'round_{round_no}_base_households', 0) or 0)
    extra_pay = _safe_decimal(getattr(pay_group, f'round_{round_no}_extra_household_pay', 0))
    if base_pay <= 0 and base_households <= 0 and extra_pay <= 0:
        return None

    excess_households = max(0, int(total_households or 0) - base_households)
    return base_pay + (extra_pay * Decimal(str(excess_households)))


def resolve_yongcha_group_household_pay_price(crew_member=None, round_no=None):
    pay_group = getattr(crew_member, 'yongcha_pay_group', None)
    if not pay_group or round_no not in (1, 2, 3):
        return None

    extra_pay = _safe_decimal(getattr(pay_group, f'round_{round_no}_extra_household_pay', 0))
    return extra_pay if extra_pay > 0 else None


def should_exclude_yongcha_group_base_pay_on_multi_round(crew_member=None):
    pay_group = getattr(crew_member, 'yongcha_pay_group', None)
    return bool(pay_group and getattr(pay_group, 'exclude_base_pay_on_multi_round', False))


def crew_identity_values(crew_member):
    if not crew_member:
        return set()
    return {
        value
        for value in {
            str(getattr(crew_member, 'code', '') or '').strip(),
            str(getattr(crew_member, 'name', '') or '').strip(),
        }
        if value
    }


def _upload_round_key(dispatch_upload):
    round_no = getattr(dispatch_upload, 'round_no', None)
    if round_no in (1, 2, 3):
        return f'round:{round_no}'
    return f'upload:{getattr(dispatch_upload, "id", "")}'


def build_daily_yongcha_round_counts(crew_members, dispatch_upload):
    crew_members = [crew for crew in crew_members if crew]
    if not crew_members or not dispatch_upload:
        return {}

    delivery_date = getattr(dispatch_upload, 'dispatch_date', None)
    team_id = getattr(dispatch_upload, 'team_id', None)
    if not delivery_date or not team_id:
        return {}

    crew_by_id = {crew.id: crew for crew in crew_members if getattr(crew, 'id', None)}
    names_to_crew_ids = defaultdict(set)
    for crew in crew_by_id.values():
        for name in crew_identity_values(crew):
            names_to_crew_ids[name].add(crew.id)
    if not names_to_crew_ids:
        return {}

    from apps.dispatch.models import DispatchUpload

    rounds_by_crew = defaultdict(set)
    uploads = (
        DispatchUpload.objects
        .filter(team_id=team_id, dispatch_date=delivery_date)
        .exclude(status='ERROR')
        .prefetch_related('records')
    )
    for upload in uploads:
        present_crew_ids = set()
        explicit_yongcha_by_crew = defaultdict(bool)
        for record in upload.records.all():
            if not getattr(record, 'is_valid', False):
                continue
            if int(getattr(record, 'boxes', 0) or 0) <= 0 and int(getattr(record, 'households', 0) or 0) <= 0:
                continue
            manager_name = str(getattr(record, 'manager_name', '') or '').strip()
            if not manager_name:
                continue
            crew_ids = names_to_crew_ids.get(manager_name)
            if not crew_ids:
                continue
            for crew_id in crew_ids:
                present_crew_ids.add(crew_id)
                if getattr(record, 'is_yongcha', False):
                    explicit_yongcha_by_crew[crew_id] = True

        round_key = _upload_round_key(upload)
        for crew_id in present_crew_ids:
            crew = crew_by_id.get(crew_id)
            if is_effective_yongcha(
                crew,
                round_no=getattr(upload, 'round_no', None),
                explicit_yongcha=explicit_yongcha_by_crew[crew_id],
            ):
                rounds_by_crew[crew_id].add(round_key)

    return {crew_id: len(rounds) for crew_id, rounds in rounds_by_crew.items()}


def count_daily_yongcha_rounds(crew_member, dispatch_upload):
    counts = build_daily_yongcha_round_counts([crew_member], dispatch_upload)
    return counts.get(getattr(crew_member, 'id', None), 0)


def allocate_whole_amount(total, weights):
    total_int = int(_safe_decimal(total))
    weights = [int(weight or 0) for weight in weights]
    if not weights:
        return []
    if total_int == 0:
        return [Decimal('0') for _ in weights]

    total_weight = sum(max(weight, 0) for weight in weights)
    if total_weight <= 0:
        return [Decimal(str(total_int if index == 0 else 0)) for index, _ in enumerate(weights)]

    allocations = []
    used = 0
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            share = total_int - used
        else:
            share = int((Decimal(str(total_int)) * Decimal(str(max(weight, 0)))) / Decimal(str(total_weight)))
            used += share
        allocations.append(Decimal(str(share)))
    return allocations


def split_region_codes(raw):
    if not raw:
        return []
    raw = str(raw).strip()
    if raw in ('', '-'):
        return []
    parts = [part.strip() for part in raw.split(',')]
    return [part for part in parts if part and REGION_CODE_PATTERN.match(part)]


def _split_counts(total, parts):
    total = int(total or 0)
    parts = max(int(parts or 0), 1)
    base = total // parts
    remainder = total % parts
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def _record_regions(record):
    regions = split_region_codes(getattr(record, 'sub_region', '') or '')
    if regions:
        return regions

    detail_region = str(getattr(record, 'detail_region', '') or '').strip()
    if detail_region:
        return [detail_region]
    return []


def build_region_allocations(records):
    allocations = defaultdict(lambda: {'boxes': 0, 'households': 0})
    for record in records:
        regions = _record_regions(record)
        if not regions:
            continue

        box_parts = _split_counts(getattr(record, 'boxes', 0), len(regions))
        household_parts = _split_counts(getattr(record, 'households', 0), len(regions))
        for index, region_code in enumerate(regions):
            allocations[region_code]['boxes'] += box_parts[index]
            allocations[region_code]['households'] += household_parts[index]
    return allocations


def build_crew_settlement_payload(
    crew_member,
    dispatch_upload,
    records,
    receive_price,
    overtime_cost=0,
    daily_yongcha_round_count=None,
):
    round_no = getattr(dispatch_upload, 'round_no', None)
    team = getattr(dispatch_upload, 'team', None) or getattr(crew_member, 'team', None)
    explicit_yongcha = any(bool(getattr(record, 'is_yongcha', False)) for record in records)
    is_yongcha = is_effective_yongcha(crew_member, round_no=round_no, explicit_yongcha=explicit_yongcha)

    total_boxes = sum(int(getattr(record, 'boxes', 0) or 0) for record in records)
    total_households = sum(int(getattr(record, 'households', 0) or 0) for record in records)
    pay_unit = (
        resolve_yongcha_pay_price(
            crew_member=crew_member,
            team=team,
            round_no=round_no,
            explicit_yongcha=explicit_yongcha,
        )
        if is_yongcha
        else _safe_decimal(crew_member.pay_price)
    )
    pay_quantity = total_households if is_yongcha else total_boxes
    fixed_pay_total = None
    pay_basis = 'households' if is_yongcha else 'boxes'

    if is_yongcha:
        if daily_yongcha_round_count is None:
            daily_yongcha_round_count = count_daily_yongcha_rounds(crew_member, dispatch_upload)
        daily_yongcha_round_count = int(daily_yongcha_round_count or 0)
        if daily_yongcha_round_count <= 0:
            daily_yongcha_round_count = 1
        exclude_base_pay_on_multi_round = should_exclude_yongcha_group_base_pay_on_multi_round(crew_member)
        if daily_yongcha_round_count <= 1 or not exclude_base_pay_on_multi_round:
            fixed_pay_total = resolve_yongcha_group_pay(
                crew_member=crew_member,
                round_no=round_no,
                total_households=total_households,
            )
            if fixed_pay_total is not None:
                pay_basis = 'yongcha_pay_group'
        else:
            group_household_pay = resolve_yongcha_group_household_pay_price(
                crew_member=crew_member,
                round_no=round_no,
            )
            if group_household_pay is not None:
                pay_unit = group_household_pay
    else:
        fixed_pay_total = resolve_regular_fixed_pay(
            crew_member=crew_member,
            round_no=round_no,
        )
        if fixed_pay_total is not None:
            pay_basis = 'regular_fixed'

    receive_total = _safe_decimal(receive_price) * Decimal(str(total_boxes))
    pay_total = fixed_pay_total if fixed_pay_total is not None else pay_unit * Decimal(str(pay_quantity))
    overtime_total = _safe_decimal(overtime_cost)
    profit_total = receive_total - pay_total - overtime_total

    allocations = build_region_allocations(records)
    region_rows = []
    for region_code, values in allocations.items():
        boxes = int(values['boxes'] or 0)
        households = int(values['households'] or 0)
        region_receive = _safe_decimal(receive_price) * Decimal(str(boxes))
        region_rows.append({
            'region': region_code,
            'boxes': boxes,
            'households': households,
            'receive_amount': region_receive,
            'pay_amount': Decimal('0'),
            'overtime_cost': Decimal('0'),
            'profit': region_receive,
        })

    region_rows.sort(key=lambda item: item['region'])
    if fixed_pay_total is not None:
        pay_weights = [
            row['households'] if is_yongcha else row['boxes']
            for row in region_rows
        ]
        region_pay_amounts = allocate_whole_amount(pay_total, pay_weights)
    else:
        region_pay_amounts = [
            pay_unit * Decimal(str(row['households'] if is_yongcha else row['boxes']))
            for row in region_rows
        ]
    for region_row, region_pay in zip(region_rows, region_pay_amounts):
        region_row['pay_amount'] = region_pay
        region_row['profit'] = region_row['receive_amount'] - region_pay

    if region_rows and overtime_total > 0:
        region_rows[0]['overtime_cost'] = overtime_total
        region_rows[0]['profit'] = region_rows[0]['profit'] - overtime_total

    return {
        'is_yongcha': is_yongcha,
        'round_no': round_no,
        'total_boxes': total_boxes,
        'total_households': total_households,
        'total_receive': receive_total,
        'total_pay': pay_total,
        'total_overtime': overtime_total,
        'total_profit': profit_total,
        'regions': region_rows,
        'pay_basis': pay_basis,
        'daily_yongcha_round_count': int(daily_yongcha_round_count or 0) if is_yongcha else 0,
    }


def detail_rows_for_crew_upload(
    crew_member,
    dispatch_upload,
    records,
    receive_price,
    overtime_cost=0,
):
    payload = build_crew_settlement_payload(
        crew_member=crew_member,
        dispatch_upload=dispatch_upload,
        records=records,
        receive_price=receive_price,
        overtime_cost=overtime_cost,
    )
    rows = []
    for region_row in payload['regions']:
        rows.append({
            'crew_member': crew_member,
            'dispatch_upload': dispatch_upload,
            'shipper_code': getattr(dispatch_upload, 'shipper_code', None) or 'kurly',
            'is_yongcha': payload['is_yongcha'],
            'region': region_row['region'],
            'delivery_type': 'SAME_DAY',
            'boxes': region_row['boxes'],
            'receive_amount': region_row['receive_amount'],
            'pay_amount': region_row['pay_amount'],
            'overtime_cost': region_row['overtime_cost'],
            'profit': region_row['profit'],
        })
    return payload, rows


def replace_settlement_details_for_crew_upload(
    settlement,
    crew_member,
    dispatch_upload,
    records,
    receive_price,
    overtime_cost=0,
):
    payload, rows = detail_rows_for_crew_upload(
        crew_member=crew_member,
        dispatch_upload=dispatch_upload,
        records=records,
        receive_price=receive_price,
        overtime_cost=overtime_cost,
    )
    SettlementDetail.objects.filter(
        settlement=settlement,
        dispatch_upload=dispatch_upload,
        crew_member=crew_member,
    ).delete()

    for row in rows:
        SettlementDetail.objects.create(settlement=settlement, **row)

    return payload


def refresh_settlement_totals(settlement_ids):
    from django.db.models import Sum
    from apps.settlement.models import Settlement

    for settlement_id in settlement_ids:
        settlement = SettlementDetail.objects.filter(settlement_id=settlement_id).values(
            'settlement_id'
        ).annotate(
            receive=Sum('receive_amount'),
            pay=Sum('pay_amount'),
            overtime=Sum('overtime_cost'),
            other=Sum('other_cost'),
            profit=Sum('profit'),
        ).order_by('settlement_id').first()
        if not settlement:
            continue
        Settlement.objects.filter(id=settlement_id).update(
            total_receive=settlement['receive'] or 0,
            total_pay=settlement['pay'] or 0,
            total_overtime=settlement['overtime'] or 0,
            total_other_cost=settlement['other'] or 0,
            total_profit=settlement['profit'] or 0,
        )


def refresh_upload_summaries(upload_ids):
    from apps.crew.models import CrewMember
    from apps.dispatch.models import DispatchUpload

    for upload in DispatchUpload.objects.filter(id__in=upload_ids).prefetch_related('records').select_related('team'):
        records = [record for record in upload.records.all() if record.is_valid and int(record.boxes or 0) > 0]
        crew_names = {
            str(record.manager_name or '').strip()
            for record in records
            if str(record.manager_name or '').strip()
        }
        regular_count = 0
        yongcha_count = 0
        for name in crew_names:
            explicit_yongcha = any(
                str(record.manager_name or '').strip() == name and record.is_yongcha
                for record in records
            )
            crew = CrewMember.objects.filter(team=upload.team, code=name).first() if upload.team_id else None
            if not crew:
                crew = CrewMember.objects.filter(code=name).first()
            if is_effective_yongcha(crew, round_no=upload.round_no, explicit_yongcha=explicit_yongcha):
                yongcha_count += 1
            else:
                regular_count += 1
        upload.mor_total_boxes = sum(int(record.boxes or 0) for record in records)
        upload.mor_regular_crew_count = regular_count
        upload.mor_yongcha_crew_count = yongcha_count
        upload.save(update_fields=[
            'mor_total_boxes',
            'mor_regular_crew_count',
            'mor_yongcha_crew_count',
            'updated_at',
        ])


def rebuild_team_settlements(team):
    from apps.crew.models import OvertimeSetting

    detail_groups = {}
    queryset = SettlementDetail.objects.exclude(dispatch_upload=None).exclude(crew_member=None).filter(
        settlement__team=team
    ).select_related(
        'settlement', 'dispatch_upload', 'crew_member', 'dispatch_upload__team'
    )
    for detail in queryset.iterator():
        key = (detail.settlement_id, detail.dispatch_upload_id, detail.crew_member_id)
        detail_groups[key] = (detail.settlement, detail.dispatch_upload, detail.crew_member)

    settlement_ids = set()
    upload_ids = set()
    rebuilt = 0
    for settlement, dispatch_upload, crew_member in detail_groups.values():
        matching_records = list(
            dispatch_upload.records.filter(
                is_valid=True,
                manager_name__in=[name for name in {crew_member.code, crew_member.name} if name],
            )
        )
        overtime_setting = OvertimeSetting.objects.filter(
            dispatch_upload=dispatch_upload,
            crew_member=crew_member,
            is_overtime=True,
        ).first()
        overtime_cost = Decimal(str(overtime_setting.overtime_cost or 0)) if overtime_setting else Decimal('0')
        receive_price = Decimal(str(dispatch_upload.team.receive_price if dispatch_upload.team else 0))
        replace_settlement_details_for_crew_upload(
            settlement=settlement,
            crew_member=crew_member,
            dispatch_upload=dispatch_upload,
            records=matching_records,
            receive_price=receive_price,
            overtime_cost=overtime_cost,
        )
        settlement_ids.add(settlement.id)
        upload_ids.add(dispatch_upload.id)
        rebuilt += 1

    refresh_settlement_totals(settlement_ids)
    refresh_upload_summaries(upload_ids)
    return {
        'rebuilt_groups': rebuilt,
        'settlement_count': len(settlement_ids),
        'upload_count': len(upload_ids),
    }
