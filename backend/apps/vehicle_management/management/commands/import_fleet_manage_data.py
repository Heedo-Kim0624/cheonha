"""Import fleet-management operation files.

This command is intentionally scoped to the vehicle-management site tables:
Vehicle, FleetVehicleRecord, FleetSubscriptionContract, FleetInsurancePolicy,
and FleetAccidentCase. It is idempotent by stable business keys so the same
source files can be re-run after a backup without creating duplicate rows.
"""
from __future__ import annotations

import math
import re
import hashlib
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.vehicle_management.models import (
    Company,
    FleetAccidentCase,
    FleetInsurancePolicy,
    FleetProfitImportBatch,
    FleetProfitRawEntry,
    FleetSubscriptionContract,
    FleetVehicleRecord,
    Vehicle,
)


SOURCE_TAG = '[fleet_manage_data]'
OPEN_END_DATE = date(2099, 12, 31)

STATUS_TO_LABEL = {
    '구독': '구독',
    '구독중': '구독',
    '직영': '직영',
    '직영운행': '직영',
    '판매': '판매',
    '판매완료': '판매',
    '유휴': '유휴',
    '휴업': '유휴',
    '휴업예정': '유휴',
    '대기': '유휴',
    '수리': 'A/S',
    '수리중': 'A/S',
    'a/s': 'A/S',
    'as': 'A/S',
}

LABEL_TO_FIELDS = {
    '유휴': ('IDLE', 'OTHER'),
    'A/S': ('REPAIRING', 'OTHER'),
    '판매': ('OPERATING', 'SALE'),
    '구독': ('OPERATING', 'SUBSCRIPTION'),
    '직영': ('OPERATING', 'DIRECT'),
}


def clean_text(value) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    text = str(value).strip()
    return '' if text.lower() in {'nan', 'nat', 'none'} else text


def header_key(value) -> str:
    return re.sub(r'[\s_./\\()\[\]-]+', '', clean_text(value)).lower()


def parse_int(value, default=0) -> int:
    text = clean_text(value)
    if not text or text in {'-', '0.0'}:
        return default
    text = re.sub(r'[^0-9.-]', '', text)
    if not text or text in {'-', '.', '-.'}:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not math.isnan(value):
        if int(value) == 0:
            return None
        parsed = pd.to_datetime(value, unit='D', origin='1899-12-30', errors='coerce')
    else:
        text = clean_text(value)
        if not text or text in {'0', '0.0', '-'}:
            return None
        text = text.replace('년', '-').replace('월', '-').replace('일', '')
        text = text.replace('.', '-').replace('/', '-')
        parsed = pd.to_datetime(text, errors='coerce')
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime().date()


def parse_datetime(value):
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors='coerce')
    if pd.isna(parsed):
        return None
    dt = parsed.to_pydatetime()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def parse_period(value):
    text = clean_text(value)
    if '~' not in text:
        return None, None
    start_raw, end_raw = [part.strip() for part in text.split('~', 1)]

    def parse_short(part):
        part = part.replace('.', '-').replace('/', '-')
        pieces = [p for p in part.split('-') if p]
        if len(pieces) == 3 and len(pieces[0]) == 2:
            pieces[0] = f'20{pieces[0]}'
            part = '-'.join(pieces)
        return parse_date(part)

    return parse_short(start_raw), parse_short(end_raw)


def vehicle_short(number: str) -> str:
    digits = re.sub(r'\D', '', clean_text(number))
    return digits[-4:] if len(digits) >= 4 else digits


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def json_clean(value):
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def normalize_status(value) -> str:
    text = clean_text(value)
    return STATUS_TO_LABEL.get(text, STATUS_TO_LABEL.get(text.lower(), text if text in LABEL_TO_FIELDS else '유휴'))


def source_note(kind: str, filename: str, **values) -> str:
    parts = [f'{key}={value}' for key, value in values.items() if clean_text(value)]
    suffix = '; '.join(parts)
    return f'{SOURCE_TAG} {kind}; file={filename}' + (f'; {suffix}' if suffix else '')


def merge_note(existing: str, new_note: str) -> str:
    existing_lines = [
        line for line in clean_text(existing).splitlines()
        if line.strip() and not line.strip().startswith(SOURCE_TAG)
    ]
    return '\n'.join([*existing_lines, new_note]).strip()


def find_header_row(frame, required):
    required_keys = {header_key(item) for item in required}
    for idx, row in frame.iterrows():
        present = {header_key(value) for value in row.tolist() if clean_text(value)}
        if required_keys.issubset(present):
            return idx
    return None


def mapped_rows(frame, header_index):
    headers = {idx: clean_text(value) for idx, value in enumerate(frame.iloc[header_index].tolist())}
    for _, raw in frame.iloc[header_index + 1:].iterrows():
        item = {}
        for idx, name in headers.items():
            if name:
                item[name] = raw.iloc[idx] if idx < len(raw) else None
        if any(clean_text(value) for value in item.values()):
            yield item


def get_by_header(item, *names):
    wanted = {header_key(name) for name in names}
    for key, value in item.items():
        if header_key(key) in wanted:
            return value
    return None


def find_vehicle(company, vehicle_number):
    if not vehicle_number:
        return None
    return Vehicle.objects.filter(company=company, vehicle_number=vehicle_number).first()


def find_record(company, vehicle_number, target_date=None, vin=''):
    qs = FleetVehicleRecord.objects.filter(company=company, vehicle_number=vehicle_number)
    if vin:
        vin_match = qs.filter(vin=vin).order_by('-start_date', '-id').first()
        if vin_match and not target_date:
            return vin_match
    if target_date:
        bounded = qs.filter(start_date__lte=target_date).filter(
            end_date__isnull=True
        ).order_by('-start_date', '-id').first()
        if bounded:
            return bounded
        bounded = qs.filter(start_date__lte=target_date, end_date__gte=target_date).order_by('-start_date', '-id').first()
        if bounded:
            return bounded
    return qs.order_by('-start_date', '-id').first()


class Importer:
    def __init__(self, *, company, user, dry_run=False, stdout=None):
        self.company = company
        self.user = user
        self.dry_run = dry_run
        self.stdout = stdout
        self.summary = {
            'vehicles_created': 0,
            'vehicles_updated': 0,
            'records_created': 0,
            'records_updated': 0,
            'subscriptions_created': 0,
            'subscriptions_updated': 0,
            'insurances_created': 0,
            'insurances_updated': 0,
            'accidents_created': 0,
            'accidents_updated': 0,
            'profit_raw_created': 0,
            'profit_raw_updated': 0,
            'skipped': 0,
            'warnings': [],
        }

    def warn(self, message):
        self.summary['warnings'].append(message)

    def bump(self, created_key, updated_key, created):
        self.summary[created_key if created else updated_key] += 1

    def upsert_vehicle(self, *, vehicle_number, vin='', model='', acquired_at=None, fleet='', driver='', status_label='유휴', note=''):
        vehicle_number = clean_text(vehicle_number)
        if not vehicle_number:
            self.summary['skipped'] += 1
            return None
        placement, operation = LABEL_TO_FIELDS.get(status_label, LABEL_TO_FIELDS['유휴'])
        defaults = {
            'vehicle_number_short': vehicle_short(vehicle_number),
            'vin_tid': clean_text(vin),
            'model': clean_text(model),
            'shipped_at': acquired_at,
            'fleet': clean_text(fleet),
            'driver': clean_text(driver),
            'placement_status': placement,
            'operation_type': operation,
            'notes': note,
            'is_active': True,
        }
        if self.dry_run:
            self.summary['vehicles_updated'] += int(find_vehicle(self.company, vehicle_number) is not None)
            self.summary['vehicles_created'] += int(find_vehicle(self.company, vehicle_number) is None)
            return None
        vehicle = find_vehicle(self.company, vehicle_number)
        if vehicle:
            for field, value in defaults.items():
                if field == 'notes':
                    value = merge_note(vehicle.notes, note) if note else vehicle.notes
                setattr(vehicle, field, value)
            vehicle.save(update_fields=[*defaults.keys(), 'updated_at'])
            self.summary['vehicles_updated'] += 1
            return vehicle
        vehicle = Vehicle.objects.create(company=self.company, vehicle_number=vehicle_number, **defaults)
        self.summary['vehicles_created'] += 1
        return vehicle

    def upsert_record(self, *, vehicle=None, vehicle_number, vin='', model='', start_date=None, end_date=None, status='유휴', note=''):
        vehicle_number = clean_text(vehicle_number)
        if not vehicle_number:
            self.summary['skipped'] += 1
            return None
        start_date = start_date or date(1900, 1, 1)
        vin = clean_text(vin) or (vehicle.vin_tid if vehicle else '')
        qs = FleetVehicleRecord.objects.filter(
            company=self.company,
            vehicle_number=vehicle_number,
            start_date=start_date,
        )
        if vin:
            qs = qs.filter(vin=vin)
        record = qs.order_by('-id').first()
        if self.dry_run:
            self.bump('records_created', 'records_updated', record is None)
            return record
        defaults = {
            'vehicle': vehicle,
            'vin': vin,
            'model': clean_text(model) or (vehicle.model if vehicle else ''),
            'end_date': end_date,
            'status': clean_text(status) or '유휴',
            'note': note,
        }
        if record:
            for field, value in defaults.items():
                if field == 'note':
                    value = merge_note(record.note, note) if note else record.note
                setattr(record, field, value)
            record.save(update_fields=[*defaults.keys(), 'updated_at'])
            self.summary['records_updated'] += 1
            return record
        record = FleetVehicleRecord.objects.create(
            company=self.company,
            vehicle_number=vehicle_number,
            start_date=start_date,
            created_by=self.user,
            **defaults,
        )
        self.summary['records_created'] += 1
        return record

    def upsert_subscription(self, *, vehicle=None, record=None, vehicle_number, customer, start_date, end_date=None,
                            monthly_fee=0, deposit=0, status='', note=''):
        if not vehicle_number or not start_date or not customer:
            self.summary['skipped'] += 1
            return None
        resolved_end = end_date or OPEN_END_DATE
        resolved_status = status or ('종료' if end_date and end_date < timezone.localdate() else '구독중')
        existing = FleetSubscriptionContract.objects.filter(
            company=self.company,
            vehicle_number=vehicle_number,
            customer=customer,
            start_date=start_date,
        ).order_by('-id').first()
        if self.dry_run:
            self.bump('subscriptions_created', 'subscriptions_updated', existing is None)
            return existing
        if not vehicle:
            vehicle = find_vehicle(self.company, vehicle_number)
        if not record:
            record = find_record(self.company, vehicle_number, start_date, vehicle.vin_tid if vehicle else '')
        defaults = {
            'vehicle': vehicle,
            'vehicle_record': record,
            'end_date': resolved_end,
            'monthly_fee': monthly_fee or (existing.monthly_fee if existing else 0),
            'deposit': deposit,
            'status': resolved_status,
            'sign_status': '서명완료',
            'note': note,
        }
        if existing:
            for field, value in defaults.items():
                if field == 'note':
                    value = merge_note(existing.note, note) if note else existing.note
                setattr(existing, field, value)
            existing.save(update_fields=[*defaults.keys(), 'updated_at'])
            self.summary['subscriptions_updated'] += 1
            return existing
        obj = FleetSubscriptionContract.objects.create(
            company=self.company,
            vehicle_number=vehicle_number,
            customer=customer,
            contact='',
            start_date=start_date,
            created_by=self.user,
            **defaults,
        )
        self.summary['subscriptions_created'] += 1
        return obj

    def upsert_insurance(self, *, vehicle=None, record=None, vehicle_number, insurer, period_text, model='', payments=None, note=''):
        start_date, end_date = parse_period(period_text)
        if not vehicle_number or not insurer or not start_date or not end_date:
            self.summary['skipped'] += 1
            return None
        policy_no = f'AUTO-{vehicle_number}-{start_date:%Y%m%d}-{end_date:%Y%m%d}'
        existing = FleetInsurancePolicy.objects.filter(
            company=self.company,
            vehicle_number=vehicle_number,
            policy_no=policy_no,
        ).first()
        if self.dry_run:
            self.bump('insurances_created', 'insurances_updated', existing is None)
            return existing
        if not vehicle:
            vehicle = find_vehicle(self.company, vehicle_number)
        if not record:
            record = find_record(self.company, vehicle_number, start_date, vehicle.vin_tid if vehicle else '')
        today = timezone.localdate()
        policy_status = '가입중' if start_date <= today <= end_date else ('예정' if today < start_date else '종료')
        defaults = {
            'vehicle': vehicle,
            'vehicle_record': record,
            'insurer': insurer,
            'start_date': start_date,
            'end_date': end_date,
            'previous_rate': 0,
            'current_rate': 0,
            'status': policy_status,
            'payments': payments or [],
            'note': note or model,
        }
        if existing:
            for field, value in defaults.items():
                if field == 'note':
                    value = merge_note(existing.note, note) if note else existing.note
                setattr(existing, field, value)
            existing.save(update_fields=[*defaults.keys(), 'updated_at'])
            self.summary['insurances_updated'] += 1
            return existing
        obj = FleetInsurancePolicy.objects.create(
            company=self.company,
            vehicle_number=vehicle_number,
            policy_no=policy_no,
            created_by=self.user,
            **defaults,
        )
        self.summary['insurances_created'] += 1
        return obj

    def upsert_accident(self, *, source_key, vehicle_number, driver, accident_at, location, status, raw):
        if not vehicle_number or not accident_at:
            self.summary['skipped'] += 1
            return None
        vehicle = find_vehicle(self.company, vehicle_number)
        record = find_record(
            self.company,
            vehicle_number,
            timezone.localtime(accident_at).date(),
            vehicle.vin_tid if vehicle else '',
        )
        existing = None
        if source_key:
            existing = FleetAccidentCase.objects.filter(company=self.company, source_key=source_key).first()
        if not existing:
            existing = FleetAccidentCase.objects.filter(
                company=self.company,
                vehicle_number=vehicle_number,
                accident_at=accident_at,
                driver=driver,
            ).first()
        if self.dry_run:
            self.bump('accidents_created', 'accidents_updated', existing is None)
            return existing
        defaults = {
            'vehicle': vehicle,
            'vehicle_record': record,
            'vehicle_number': vehicle_number,
            'vehicle_vin': record.vin if record else (vehicle.vin_tid if vehicle else ''),
            'driver': driver,
            'accident_at': accident_at,
            'location': location,
            'description': '',
            'coverage': '',
            'victim': '',
            'manager': '',
            'status': status or '진행중',
            'items': [{'kind': 'uploaded_source', 'source': '사고전체이력', 'raw': raw}],
        }
        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            if source_key:
                existing.source_key = source_key
            existing.save(update_fields=[*defaults.keys(), 'source_key', 'updated_at'])
            self.summary['accidents_updated'] += 1
            return existing
        obj = FleetAccidentCase.objects.create(
            company=self.company,
            source_key=source_key,
            compensation=0,
            personal_compensation=0,
            property_compensation=0,
            paid=0,
            created_by=self.user,
            **defaults,
        )
        self.summary['accidents_created'] += 1
        return obj

    def upsert_profit_raw(self, *, batch, entry_type, sheet, row_number, vehicle_number, amount=0, period_month=None, raw=None):
        vehicle_number = clean_text(vehicle_number)
        if not vehicle_number:
            self.summary['skipped'] += 1
            return None
        source_key = f'{SOURCE_TAG}:profit:{batch.file_hash}:{sheet}:{row_number}:{entry_type}:{vehicle_number}'
        vehicle = find_vehicle(self.company, vehicle_number)
        record = find_record(self.company, vehicle_number, None, vehicle.vin_tid if vehicle else '')
        existing = FleetProfitRawEntry.objects.filter(company=self.company, source_key=source_key).first()
        if self.dry_run:
            self.bump('profit_raw_created', 'profit_raw_updated', existing is None)
            return existing
        defaults = {
            'batch': batch,
            'entry_type': entry_type,
            'source_sheet': sheet,
            'source_row': row_number,
            'vehicle': vehicle,
            'vehicle_record': record,
            'vehicle_number': vehicle_number,
            'period_month': period_month,
            'amount': parse_int(amount),
            'raw': raw or {},
        }
        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save(update_fields=[*defaults.keys()])
            self.summary['profit_raw_updated'] += 1
            return existing
        obj = FleetProfitRawEntry.objects.create(
            company=self.company,
            source_key=source_key,
            **defaults,
        )
        self.summary['profit_raw_created'] += 1
        return obj

    def import_profit_source_sheets(self, path: Path):
        file_hash = file_sha256(path)
        if self.dry_run:
            batch = SimpleNamespace(source_file=path.name, file_hash=file_hash)
        else:
            batch, _created = FleetProfitImportBatch.objects.get_or_create(
                company=self.company,
                file_hash=file_hash,
                defaults={
                    'source_file': path.name,
                    'status': 'applied',
                    'summary': {'source': SOURCE_TAG, 'purpose': 'fleet_profit_source'},
                    'created_by': self.user,
                },
            )
        sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)

        def raw_payload(row):
            return {str(index + 1): json_clean(value) for index, value in enumerate(row.tolist())}

        monthly_depreciation = sheets.get('월감가')
        if monthly_depreciation is not None:
            for idx, row in monthly_depreciation.iterrows():
                vehicle_number = clean_text(row.iloc[0] if len(row) else '')
                if not vehicle_number:
                    continue
                self.upsert_profit_raw(
                    batch=batch,
                    entry_type='depreciation',
                    sheet='월감가',
                    row_number=int(idx) + 1,
                    vehicle_number=vehicle_number,
                    amount=row.iloc[1] if len(row) > 1 else 0,
                    raw=raw_payload(row),
                )

        residual = sheets.get('잔가')
        if residual is not None:
            for idx, row in residual.iloc[1:].iterrows():
                vehicle_number = clean_text(row.iloc[0] if len(row) else '')
                if not vehicle_number:
                    continue
                self.upsert_profit_raw(
                    batch=batch,
                    entry_type='residual',
                    sheet='잔가',
                    row_number=int(idx) + 1,
                    vehicle_number=vehicle_number,
                    amount=row.iloc[1] if len(row) > 1 else 0,
                    raw=raw_payload(row),
                )

        insurance = sheets.get('보험료')
        if insurance is not None:
            for idx, row in insurance.iloc[2:].iterrows():
                vehicle_number = clean_text(row.iloc[1] if len(row) > 1 else '')
                if not vehicle_number:
                    continue
                total_premium = parse_int(row.iloc[5] if len(row) > 5 else 0)
                monthly_cost = int(total_premium / 12) if total_premium else 0
                self.upsert_profit_raw(
                    batch=batch,
                    entry_type='insurance',
                    sheet='보험료',
                    row_number=int(idx) + 1,
                    vehicle_number=vehicle_number,
                    amount=monthly_cost,
                    raw=raw_payload(row),
                )

    def import_master_file(self, path: Path):
        filename = path.name
        frame = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
        header_index = find_header_row(frame, ['차량번호', '차대번호'])
        if header_index is None:
            raise CommandError(f'{filename}: 차량 마스터 헤더를 찾을 수 없습니다.')
        for item in mapped_rows(frame, header_index):
            vehicle_number = clean_text(get_by_header(item, '차량번호'))
            vin = clean_text(get_by_header(item, '차대번호'))
            if not vehicle_number or not vin:
                continue
            raw_status = clean_text(get_by_header(item, '구분'))
            status_label = normalize_status(raw_status)
            acquired_at = parse_date(get_by_header(item, '취득연월'))
            model = clean_text(get_by_header(item, '차종'))
            owner = clean_text(get_by_header(item, '소유주'))
            location = clean_text(get_by_header(item, '현위치(수리/대기)'))
            contract_start = parse_date(get_by_header(item, '계약 시작 일자'))
            return_date = parse_date(get_by_header(item, '반납 일자'))
            customer = clean_text(get_by_header(item, '계약자'))
            driver = clean_text(get_by_header(item, '운전자'))
            monthly_fee = parse_int(get_by_header(item, 'Ⅰ . 매 출 액(구독료)', '차량임대수입'))
            note = source_note(
                'master',
                filename,
                raw_status=raw_status,
                owner=owner,
                location=location,
                base_value=parse_int(get_by_header(item, '기초가액')),
                residual=clean_text(get_by_header(item, '당월말잔가')),
            )
            vehicle = self.upsert_vehicle(
                vehicle_number=vehicle_number,
                vin=vin,
                model=model,
                acquired_at=acquired_at,
                fleet=customer or location,
                driver=driver,
                status_label=status_label,
                note=note,
            )
            record = self.upsert_record(
                vehicle=vehicle,
                vehicle_number=vehicle_number,
                vin=vin,
                model=model,
                start_date=acquired_at or contract_start,
                end_date=return_date,
                status=status_label,
                note=note,
            )
            if status_label == '구독' and contract_start and customer and monthly_fee:
                self.upsert_subscription(
                    vehicle=vehicle,
                    record=record,
                    vehicle_number=vehicle_number,
                    customer=customer,
                    start_date=contract_start,
                    end_date=return_date,
                    monthly_fee=monthly_fee,
                    status='종료' if return_date and return_date < timezone.localdate() else '구독중',
                    note=source_note('current_subscription', filename, driver=driver, raw_status=raw_status),
                )

        xl = pd.ExcelFile(path)
        if '보험료' in xl.sheet_names:
            self.import_insurance_sheet(path, filename)

    def import_insurance_sheet(self, path: Path, filename: str):
        frame = pd.read_excel(path, sheet_name='보험료', header=None, dtype=object)
        header_index = find_header_row(frame, ['차량번호', '보험사', '보험기간'])
        if header_index is None:
            self.warn(f'{filename}: 보험료 시트 헤더를 찾지 못했습니다.')
            return
        for item in mapped_rows(frame, header_index):
            vehicle_number = clean_text(get_by_header(item, '차량번호'))
            insurer = clean_text(get_by_header(item, '보험사'))
            period = clean_text(get_by_header(item, '보험기간'))
            if not vehicle_number or not insurer or not period:
                continue
            model = clean_text(get_by_header(item, '차량명'))
            payments = []
            for key, value in item.items():
                if header_key(key) in {
                    header_key('보험료 총액'),
                    header_key('초회분담금'),
                    header_key('1차'),
                    header_key('2차'),
                    header_key('3차'),
                    header_key('4차'),
                    header_key('5차'),
                    header_key('6차'),
                }:
                    amount = parse_int(value, default=None)
                    if amount not in (None, 0):
                        payments.append({'label': clean_text(key), 'amount': amount, 'paid': False})
            self.upsert_insurance(
                vehicle_number=vehicle_number,
                insurer=insurer,
                period_text=period,
                model=model,
                payments=payments,
                note=source_note('insurance', filename, model=model, total=parse_int(get_by_header(item, '보험료 총액'))),
            )

    def import_subscription_history(self, path: Path):
        filename = path.name
        frame = pd.read_excel(path, sheet_name=0, header=None, dtype=object)
        header_index = find_header_row(frame, ['고객명', '차량번호', '계약시작일자'])
        if header_index is None:
            raise CommandError(f'{filename}: 구독 이력 헤더를 찾을 수 없습니다.')
        for item in mapped_rows(frame, header_index):
            customer = clean_text(get_by_header(item, '고객명'))
            vehicle_number = clean_text(get_by_header(item, '차량번호'))
            start_date = parse_date(get_by_header(item, '계약시작일자'))
            if not customer or not vehicle_number or not start_date:
                continue
            end_date = parse_date(get_by_header(item, '반납일자'))
            running = clean_text(get_by_header(item, '가동여부')).replace(' ', '')
            status = '구독중' if running == '사용중' and not end_date else '종료'
            model = clean_text(get_by_header(item, '차종'))
            form = clean_text(get_by_header(item, '형식'))
            ev_no = clean_text(get_by_header(item, 'EV'))
            deposit = parse_int(get_by_header(item, '보증금'))
            vehicle = find_vehicle(self.company, vehicle_number)
            record = self.upsert_record(
                vehicle=vehicle,
                vehicle_number=vehicle_number,
                vin=vehicle.vin_tid if vehicle else '',
                model=model or (vehicle.model if vehicle else ''),
                start_date=start_date,
                end_date=end_date,
                status='구독' if status == '구독중' else '반납',
                note=source_note('subscription_history_record', filename, customer=customer, ev=ev_no, form=form),
            )
            current_fee = 0
            existing_current = FleetSubscriptionContract.objects.filter(
                company=self.company,
                vehicle_number=vehicle_number,
                customer=customer,
                monthly_fee__gt=0,
            ).order_by('-start_date', '-id').first()
            if existing_current:
                current_fee = existing_current.monthly_fee
            self.upsert_subscription(
                vehicle=vehicle,
                record=record,
                vehicle_number=vehicle_number,
                customer=customer,
                start_date=start_date,
                end_date=end_date,
                monthly_fee=current_fee,
                deposit=deposit,
                status=status,
                note=source_note('subscription_history', filename, ev=ev_no, contract_type=clean_text(get_by_header(item, '계약구분')), form=form),
            )

    def import_accident_history(self, path: Path):
        filename = path.name
        frame = pd.read_excel(path, sheet_name=0, header=None, dtype=object, engine='xlrd' if path.suffix.lower() == '.xls' else None)
        header_index = find_header_row(frame, ['사고번호', '차량번호', '사고일시'])
        if header_index is None:
            raise CommandError(f'{filename}: 사고 이력 헤더를 찾을 수 없습니다.')
        for item in mapped_rows(frame, header_index):
            source_key = clean_text(get_by_header(item, '사고번호'))
            vehicle_number = clean_text(get_by_header(item, '차량번호'))
            accident_at = parse_datetime(get_by_header(item, '사고일시'))
            if not vehicle_number or not accident_at:
                continue
            raw = {key: clean_text(value) for key, value in item.items()}
            self.upsert_accident(
                source_key=source_key,
                vehicle_number=vehicle_number,
                driver=clean_text(get_by_header(item, '운전자')),
                accident_at=accident_at,
                location=clean_text(get_by_header(item, '사고장소')),
                status=clean_text(get_by_header(item, '상태')),
                raw=raw,
            )


class Command(BaseCommand):
    help = 'Import fleet_manage_data Excel files into vehicle-management tables.'

    def add_arguments(self, parser):
        parser.add_argument('data_dir', type=str)
        parser.add_argument('--company', default='CHEONHA')
        parser.add_argument('--user', default='clever_admin')
        parser.add_argument('--apply', action='store_true', help='Actually write rows. Without this, dry-run only.')

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir']).expanduser()
        if not data_dir.exists():
            raise CommandError(f'Data directory does not exist: {data_dir}')
        company = Company.objects.filter(code=options['company']).first()
        if not company:
            raise CommandError(f'Unknown company code: {options["company"]}')
        User = get_user_model()
        user = User.objects.filter(username=options['user']).first()
        dry_run = not options['apply']

        files = {
            'master': next(iter(sorted(data_dir.glob('260625*.xlsx'))), None),
            'subscriptions': next(iter(sorted(data_dir.glob('260626*.xlsx'))), None),
            'accidents': next(iter(sorted(data_dir.glob('사고전체이력.xls*'))), None),
        }
        missing = [key for key, value in files.items() if value is None]
        if missing:
            raise CommandError(f'Missing source files: {", ".join(missing)}')

        importer = Importer(company=company, user=user, dry_run=dry_run, stdout=self.stdout)
        mode = 'APPLY' if options['apply'] else 'DRY-RUN'
        self.stdout.write(f'[{mode}] Importing fleet files for {company.name} ({company.code})')
        with transaction.atomic():
            importer.import_master_file(files['master'])
            importer.import_profit_source_sheets(files['master'])
            importer.import_subscription_history(files['subscriptions'])
            importer.import_accident_history(files['accidents'])
            if dry_run:
                transaction.set_rollback(True)

        for key, value in importer.summary.items():
            if key == 'warnings':
                continue
            self.stdout.write(f'{key}: {value}')
        if importer.summary['warnings']:
            self.stdout.write('warnings:')
            for warning in importer.summary['warnings'][:50]:
                self.stdout.write(f' - {warning}')
        self.stdout.write(self.style.SUCCESS('Fleet manage data import finished.'))
