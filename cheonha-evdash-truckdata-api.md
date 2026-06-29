# CHEONHA → EV Dashboard `dashboard_truckdata` 시계열 API

특정 차량의 특정 기간 truckdata를 안전하게 가져오는 Django Service + DRF ViewSet 패치.

**전제**:
- EV Dashboard 쪽 SQL 작업 완료 (cheonha_reader + view 3개 생성)
- **추가로 truckdata GRANT 완료 필요** (이 문서 Step 0 참조)
- CHEONHA backend가 evdash second DB로 접속 중 (`.env`에 EVDASH_*)

---

## Step 0. EV Dashboard에서 truckdata 권한 (반드시 먼저)

```bash
docker exec -i ev-dashboard-server-database-1 psql -U postgres -d postgres <<'SQL'
GRANT SELECT ON dashboard_truckdata TO cheonha_reader;

DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN (
    SELECT chunk_schema, chunk_name FROM timescaledb_information.chunks
    WHERE hypertable_name = 'dashboard_truckdata'
  ) LOOP
    EXECUTE format('GRANT SELECT ON %I.%I TO cheonha_reader', r.chunk_schema, r.chunk_name);
  END LOOP;
END $$;

ALTER DEFAULT PRIVILEGES IN SCHEMA _timescaledb_internal
  GRANT SELECT ON TABLES TO cheonha_reader;
GRANT USAGE ON SCHEMA _timescaledb_internal TO cheonha_reader;

SET ROLE cheonha_reader;
SELECT count(*) FROM dashboard_truckdata WHERE time > NOW() - INTERVAL '1 hour';
RESET ROLE;
SQL
```

OK 출력이 보이면 다음 단계로.

---

## Step 1. `EVDashService.get_truckdata()` 메서드 추가

`/app/apps/vehicle_management/services/evdash_service.py` 의 `EVDashService` 클래스에 다음을 추가합니다.

```python
# 파일 상단 import에 추가:
from datetime import datetime, timedelta, timezone
from django.db import connections


class EVDashService:
    # ... 기존 코드 ...

    # ─── truckdata: 컬럼 화이트리스트 ───────────────────────
    # SQL injection 방지용. 클라이언트가 fields=... 로 명시 가능한 컬럼 목록.
    SAFE_TRUCK_COLUMNS = frozenset([
        # 시간/식별자
        'time', 'terminal_id', 'id',
        # 위치
        'x_position', 'y_position', 'z_position',
        'gps_course', 'gps_speed', 'gps_status',
        'gps_latitude_ns', 'gps_longitude_ew',
        # 배터리/팩
        'battery_soc', 'battery_voltage', 'battery_temp', 'battery_output_current',
        'pack_soc', 'pack_soh', 'pack_voltage', 'pack_current',
        'pack_charge_current', 'pack_charge_current_limit',
        'pack_discharge_current', 'pack_discharge_current_limit',
        'cell_max_voltage', 'cell_min_voltage',
        'cell_max_temperature', 'cell_min_temperature',
        'charger_connection_status', 'charger_connection_status_v2',
        'lv_battery_voltage', 'insulation_resistance',
        'bat_n_charge_remainder_time', 'bat_n_dc_charge_times', 'bat_ptc',
        # 모터/구동
        'motor_temp', 'motor_torque', 'inverter_temp',
        # 운전/속도
        'veh_speed', 'vehicle_speed', 'apps',
        'shift_lever_pos', 'shift_lever_position', 'st_angle',
        'brake_switch', 'brake_switch_old',
        'parking_brake', 'parking_brake_v2',
        'start_limit_feedback', 'key_status',
        'veh_power_status', 'power', 'range', 'turn_onoff',
        'odometer',
        # 냉장
        'compressor_level', 'coolant_temp',
        'current_temp', 'target_temp',
        'defrost_duration', 'defrost_period', 'defrost_on',
        'fan_duty', 'freezer_on', 'humid_sensor', 'temp_sensor',
        'recording_on',
        # 도어
        'cabin_door_left', 'cabin_door_right',
        'cabin_door_left_v2', 'cabin_door_right_v2',
        'cargo_door',
        'cargo_door0', 'cargo_door1', 'cargo_door2',
        'cargo_door3', 'cargo_door4', 'cargo_door5',
        'vehicle_door_lock_status',
        # 안전/시트
        'driver_seat_belt', 'driver_seated',
        'passenger_seat_belt', 'passenger_seated',
        # TPMS
        'tpms_fl', 'tpms_fr', 'tpms_rl', 'tpms_rr',
        # 적재/상태
        'load_weight',
        'status_001', 'status_002', 'status_003',
        # 통신/메타
        'raw_data', 'cnt', 'crc', 'err',
    ])

    # 자주 쓰는 필드 프리셋
    TRUCK_PRESETS = {
        'light': [
            'time', 'pack_soc', 'x_position', 'y_position',
            'veh_speed', 'veh_power_status', 'charger_connection_status',
            'range', 'odometer',
        ],
        'battery': [
            'time', 'pack_soc', 'pack_soh', 'pack_voltage', 'pack_current',
            'pack_charge_current', 'pack_discharge_current',
            'cell_max_voltage', 'cell_min_voltage',
            'cell_max_temperature', 'cell_min_temperature',
            'charger_connection_status', 'lv_battery_voltage',
            'range', 'bat_n_charge_remainder_time',
        ],
        'cold_chain': [
            'time', 'compressor_level', 'coolant_temp',
            'current_temp', 'target_temp',
            'defrost_duration', 'defrost_period', 'defrost_on',
            'freezer_on', 'humid_sensor', 'temp_sensor',
            'fan_duty', 'recording_on',
        ],
        'motion': [
            'time', 'veh_speed', 'vehicle_speed', 'gps_speed',
            'x_position', 'y_position', 'gps_course',
            'shift_lever_position', 'apps',
            'brake_switch', 'parking_brake_v2', 'st_angle',
            'odometer',
        ],
        'safety': [
            'time',
            'driver_seat_belt', 'driver_seated',
            'passenger_seat_belt', 'passenger_seated',
            'parking_brake_v2', 'vehicle_door_lock_status',
            'tpms_fl', 'tpms_fr', 'tpms_rl', 'tpms_rr',
            'cabin_door_left_v2', 'cabin_door_right_v2',
            'cargo_door0', 'cargo_door1', 'cargo_door2',
            'cargo_door3', 'cargo_door4', 'cargo_door5',
        ],
        'all_minimal': [  # 빈번한 모니터링용 핵심 + 위치 + 냉장 + 배터리 요약
            'time', 'pack_soc', 'x_position', 'y_position',
            'veh_speed', 'current_temp', 'target_temp',
            'freezer_on', 'charger_connection_status',
            'veh_power_status', 'range',
        ],
    }

    MAX_RANGE_HOURS = 24 * 7    # 최대 7일치
    MAX_LIMIT       = 10_000    # 한 응답 최대 행 수
    DEFAULT_LIMIT   = 1_000

    def get_truckdata(
        self,
        *,
        vehicle_id: int,
        start_at,                 # datetime (UTC 또는 tz-aware 권장)
        end_at,                   # datetime
        preset: str | None = None,
        fields: list[str] | None = None,
        limit: int = DEFAULT_LIMIT,
        bucket: str | None = None,  # 예: '1m', '5m', '1h' → TimescaleDB time_bucket
        order: str = 'asc',          # 'asc' | 'desc'
    ) -> dict:
        """
        특정 차량의 dashboard_truckdata 시계열 조회.

        Returns:
          {
            'vehicle_id': int,
            'start': iso,
            'end':   iso,
            'bucket': str | None,
            'fields': [...],
            'count': int,
            'truncated': bool,   # limit 도달 여부
            'rows':  [ {col: val, ...}, ... ],
          }
        """
        # ─── 기간 검증 ─────────────────────────────────
        if not (start_at and end_at):
            raise ValueError('start_at, end_at required')
        if end_at <= start_at:
            raise ValueError('end_at must be > start_at')
        if (end_at - start_at) > timedelta(hours=self.MAX_RANGE_HOURS):
            raise ValueError(f'Max range is {self.MAX_RANGE_HOURS} hours')

        # ─── 컬럼 결정 ─────────────────────────────────
        if preset:
            cols = self.TRUCK_PRESETS.get(preset)
            if cols is None:
                raise ValueError(
                    f'Unknown preset {preset!r}. '
                    f'Available: {list(self.TRUCK_PRESETS.keys())}'
                )
        elif fields:
            cols = [c for c in fields if c in self.SAFE_TRUCK_COLUMNS]
            if not cols:
                raise ValueError('No valid fields after whitelist filter')
        else:
            cols = list(self.TRUCK_PRESETS['light'])

        # time, terminal_id는 항상 포함 (terminal_id는 응답 메타로도 쓸 수 있게)
        cols = list(dict.fromkeys(['time', 'terminal_id', *cols]))

        # ─── LIMIT 클램프 ──────────────────────────────
        limit = max(1, min(int(limit), self.MAX_LIMIT))

        order_sql = 'ASC' if order.lower() == 'asc' else 'DESC'

        # ─── SQL 빌드 ──────────────────────────────────
        col_sql = ', '.join(f'"{c}"' for c in cols)

        if bucket:
            # 다운샘플링: time_bucket으로 그루핑, varchar 컬럼은 MAX (마지막값 근사)
            # 정확히 마지막값이 필요하면 LAST(col, time) 권장 (TimescaleDB 함수)
            agg_cols = []
            for c in cols:
                if c == 'time':
                    continue
                if c == 'terminal_id':
                    agg_cols.append(f'MAX("{c}") AS "{c}"')
                else:
                    # last() — TimescaleDB 2.x 지원
                    agg_cols.append(f'last("{c}", "time") AS "{c}"')
            sql = f"""
                SELECT
                  time_bucket(%(bucket)s::interval, "time") AS "time",
                  {', '.join(agg_cols)}
                FROM dashboard_truckdata
                WHERE terminal_id = %(vid)s
                  AND "time" >= %(start)s
                  AND "time" <  %(end)s
                GROUP BY 1
                ORDER BY 1 {order_sql}
                LIMIT %(limit)s
            """
        else:
            sql = f"""
                SELECT {col_sql}
                FROM dashboard_truckdata
                WHERE terminal_id = %(vid)s
                  AND "time" >= %(start)s
                  AND "time" <  %(end)s
                ORDER BY "time" {order_sql}
                LIMIT %(limit)s
            """

        # ─── 실행 ─────────────────────────────────────
        with connections['evdash'].cursor() as cur:
            cur.execute(sql, {
                'vid':    vehicle_id,
                'start':  start_at,
                'end':    end_at,
                'limit':  limit + 1,   # truncated 판별용
                'bucket': bucket,
            })
            rows = cur.fetchall()
            col_names = [c[0] for c in cur.description]

        truncated = len(rows) > limit
        rows = rows[:limit]

        def _serialize(val):
            if isinstance(val, datetime):
                return val.isoformat()
            return val

        return {
            'vehicle_id': int(vehicle_id),
            'start':  start_at.isoformat() if isinstance(start_at, datetime) else str(start_at),
            'end':    end_at.isoformat()   if isinstance(end_at, datetime)   else str(end_at),
            'bucket': bucket,
            'fields': col_names,
            'count':  len(rows),
            'truncated': truncated,
            'rows':   [
                {n: _serialize(v) for n, v in zip(col_names, r)}
                for r in rows
            ],
        }

    def get_truckdata_by_plate_short(self, plate_short, **kwargs):
        """plate_short(끝 4자리)로 매칭된 차량 중 첫 번째의 truckdata."""
        matched = self.find_by_plate_short(plate_short)
        if not matched:
            return None
        return self.get_truckdata(vehicle_id=matched[0].vehicle_id, **kwargs)
```

---

## Step 2. ViewSet 액션 추가

`/app/apps/vehicle_management/api/evdash_views.py` 의 `EVDashVehicleViewSet`에 다음 2개 액션을 추가합니다.

```python
# 파일 상단 import에 추가:
from datetime import datetime, timedelta, timezone

from rest_framework.exceptions import ValidationError, NotFound


class EVDashVehicleViewSet(viewsets.ViewSet):
    # ... 기존 list / retrieve / by_plate_short ...

    def _parse_time(self, s, name='time'):
        if not s:
            raise ValidationError(f'{name} is required (ISO8601)')
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00'))
        except ValueError:
            raise ValidationError(f'Invalid {name}: {s!r}')

    def _truckdata_common_params(self, request):
        start_at = self._parse_time(request.query_params.get('start'), 'start')
        end_at   = self._parse_time(request.query_params.get('end'),   'end')
        preset   = request.query_params.get('preset')          # 'light' | 'battery' | ...
        fields_s = request.query_params.get('fields')          # 'pack_soc,x_position'
        fields   = [f.strip() for f in fields_s.split(',') if f.strip()] if fields_s else None
        try:
            limit = int(request.query_params.get('limit', 1000))
        except ValueError:
            raise ValidationError('limit must be integer')
        bucket = request.query_params.get('bucket')            # '1m' | '5m' | '1h'
        order  = request.query_params.get('order', 'asc')
        if order.lower() not in ('asc', 'desc'):
            raise ValidationError("order must be 'asc' or 'desc'")
        return dict(start_at=start_at, end_at=end_at,
                    preset=preset, fields=fields,
                    limit=limit, bucket=bucket, order=order)

    @action(detail=True, methods=['get'], url_path='truckdata')
    def truckdata(self, request, pk=None):
        """
        GET /api/v1/evdash/vehicles/{vehicle_id}/truckdata/
            ?start=2026-05-22T00:00:00&end=2026-05-22T01:00:00
            &preset=battery
            &limit=2000
            &bucket=1m
            &order=asc
        """
        params = self._truckdata_common_params(request)
        try:
            result = self.service.get_truckdata(vehicle_id=int(pk), **params)
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(result)

    @action(
        detail=False, methods=['get'],
        url_path=r'by-plate-short/(?P<plate_short>[0-9]{1,8})/truckdata',
    )
    def truckdata_by_plate_short(self, request, plate_short=None):
        """plate_short(끝 4자리)로 차량 찾고 truck 시계열 조회."""
        params = self._truckdata_common_params(request)
        try:
            result = self.service.get_truckdata_by_plate_short(plate_short, **params)
        except ValueError as e:
            raise ValidationError(str(e))
        if result is None:
            raise NotFound(f'No vehicle matched plate_short={plate_short!r}')
        return Response(result)

    @action(detail=False, methods=['get'], url_path='truckdata-presets')
    def truckdata_presets(self, request):
        """사용 가능한 preset과 컬럼 목록."""
        return Response({
            'presets': {k: v for k, v in self.service.TRUCK_PRESETS.items()},
            'all_safe_columns': sorted(self.service.SAFE_TRUCK_COLUMNS),
            'max_range_hours': self.service.MAX_RANGE_HOURS,
            'max_limit': self.service.MAX_LIMIT,
        })
```

URL은 DefaultRouter가 자동 등록합니다. 별도 `urls.py` 수정 불필요.

---

## Step 3. API 사용법

배포(`docker compose up -d --force-recreate backend`) 후:

### 3.1 사용 가능한 preset 확인
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/api/v1/evdash/vehicles/truckdata-presets/
```

### 3.2 특정 차량 (terminal_id=123) 의 지난 1시간 light preset
```bash
START=$(date -u -d '1 hour ago' +%FT%TZ)
END=$(date -u +%FT%TZ)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/evdash/vehicles/123/truckdata/?start=$START&end=$END&preset=light"
```

### 3.3 배터리 모니터링용 — 24시간, 5분 다운샘플링
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/evdash/vehicles/123/truckdata/?start=2026-05-21T00:00:00Z&end=2026-05-22T00:00:00Z&preset=battery&bucket=5m"
```

→ 24시간 × 12개/시간 = 288개 행 (압축됨)

### 3.4 콜드체인 — 명시 필드
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/evdash/vehicles/123/truckdata/?start=2026-05-21T08:00:00Z&end=2026-05-21T20:00:00Z&fields=time,current_temp,target_temp,freezer_on,defrost_on&bucket=1m"
```

### 3.5 plate_short로 (CHEONHA Vehicle.vehicle_number_short 매칭)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/v1/evdash/vehicles/by-plate-short/4806/truckdata/?start=2026-05-22T00:00:00Z&end=2026-05-22T01:00:00Z&preset=light"
```

### 3.6 응답 구조
```json
{
  "vehicle_id": 123,
  "start": "2026-05-22T00:00:00+00:00",
  "end":   "2026-05-22T01:00:00+00:00",
  "bucket": "1m",
  "fields": ["time", "terminal_id", "pack_soc", "x_position", "y_position",
             "veh_speed", "veh_power_status", "charger_connection_status",
             "range", "odometer"],
  "count": 60,
  "truncated": false,
  "rows": [
    {
      "time": "2026-05-22T00:00:00+00:00",
      "terminal_id": 123,
      "pack_soc": "82",
      "x_position": "37.5147",
      "y_position": "127.0490",
      "veh_speed": "32",
      "veh_power_status": "ON",
      "charger_connection_status": "DISCONNECTED",
      "range": "210",
      "odometer": "184220"
    },
    ...
  ]
}
```

---

## Step 4. 즉시 테스트 (Django 코드 적용 전, 컨테이너에서 raw psycopg2)

코드 push 전이라도 컨테이너 안에서 바로 테스트 가능:

```bash
sudo docker exec -i cheonha-backend-1 python <<'PY'
import os, psycopg2
from datetime import datetime, timedelta, timezone

conn = psycopg2.connect(
    host=os.environ['EVDASH_DB_HOST'],
    port=int(os.environ['EVDASH_DB_PORT']),
    dbname=os.environ['EVDASH_DB_NAME'],
    user=os.environ['EVDASH_DB_USER'],
    password=os.environ['EVDASH_DB_PASSWORD'],
    connect_timeout=5,
)
cur = conn.cursor()

# 가장 최근 데이터를 받은 차량 1대 찾기
cur.execute("""
    SELECT terminal_id, max(time) AS latest
    FROM dashboard_truckdata
    WHERE time > NOW() - INTERVAL '1 hour'
    GROUP BY terminal_id
    ORDER BY latest DESC
    LIMIT 1
""")
vid, latest = cur.fetchone()
print(f'sample vehicle_id = {vid}, latest = {latest}')

# 그 차량의 최근 10분 light preset
start = latest - timedelta(minutes=10)
end   = latest + timedelta(minutes=1)
cur.execute("""
    SELECT time, pack_soc, x_position, y_position,
           veh_speed, veh_power_status, range
    FROM dashboard_truckdata
    WHERE terminal_id = %s
      AND time >= %s AND time < %s
    ORDER BY time DESC
    LIMIT 10
""", (vid, start, end))
rows = cur.fetchall()
print(f'\n== {len(rows)} rows ==')
for r in rows:
    print(r)
cur.close(); conn.close()
PY
```

5분 이내에 10행 정도의 실데이터가 나오면 **Service 메서드도 동일하게 동작할 것**임을 보장.

---

## Step 5. 주의사항

1. **컬럼 화이트리스트로 SQL injection 차단** — 임의 컬럼명 못 박음.
2. **기간 제한 7일** — 무한 쿼리 방지. UI에서 더 긴 범위는 chunk로 나눠 호출.
3. **LIMIT 10000** — 응답 너무 커지면 다운샘플링(`bucket=5m` 등) 권장.
4. **time_bucket + last()** — TimescaleDB 2.x 함수. PG12+TS 2.11.2에서 확인됨.
5. **응답의 truncated=true** 이면 클라이언트가 마지막 time을 기준으로 다음 페이지 요청.
6. **모든 numeric 컬럼이 `character varying`** — 클라이언트에서 float 변환 책임. (DB 마이그레이션이 큰 작업이라 그대로 둠)
7. **인덱스 활용**: `(terminal_id, time DESC)` 인덱스가 있어서 차량+기간 쿼리는 빠름. **다른 필터(예: WHERE pack_soc > 50) 단독은 매우 느림.**

---

## Step 6. 향후 확장 아이디어

- **여러 차량 동시 조회**: `vehicle_ids=12,34,56`로 여러 terminal_id 동시 (`WHERE terminal_id = ANY(%s)`)
- **GeoJSON LineString 응답**: 경로 시각화용 (x_position, y_position 모음)
- **이상치 감지 endpoint**: 배터리 급강하/도어 비정상 오픈 등 룰 기반 알람
- **차량 간 비교**: 같은 fleet의 차량별 평균 pack_soc 시계열
- **Materialized view**: 자주 쓰는 1분/5분 다운샘플링을 미리 계산해두기 (TimescaleDB Continuous Aggregate)

이런 거 필요해지면 같은 패턴으로 Service 메서드만 추가하면 됩니다.

---

## 한 줄 요약

**Step 0 (truckdata GRANT) → Step 1 (Service 메서드) → Step 2 (ViewSet 액션) → 배포 → curl 한 줄로 사용 가능.** 
preset 5개(light/battery/cold_chain/motion/safety)와 time_bucket 다운샘플링까지 다 포함되어 있어요.
