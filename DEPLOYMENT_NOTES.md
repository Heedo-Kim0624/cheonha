# 차량관리 + 현장관리자 앱 추가 개발 — 배포 노트

## 변경 요약

### 신규 백엔드 Django apps
| 앱 | 스키마 | 책임 |
|---|---|---|
| `apps.vehicle_management` | `vehicle_mgmt` | 회사·차량·피트·캘린더·구독·반납·A/S |
| `apps.field_manager` | `field_mgr` | 현장관리자 로그인 세션 (PIN 2580) |

### 신규 API 엔드포인트
- `/api/v1/vehicle/` — 차량관리 (관리자 JWT 필수)
- `/api/v1/field-manager/` — 현장관리자 앱 (자체 fm-token, PIN 2580)

### 신규 Frontend
- 라우트 5개: `/portal/vehicle/{status,pit,calendar,subscription,as}`
- `CleverPortalAdminView.vue` 사이드바에 "차량관리" 4번째 탭 + 컴포넌트 5개
- `frontend/src/components/portal/VehicleManagementPanel.vue` 등 6개 컴포넌트

### 신규 Mobile App
- `field-manager-app/` Expo TypeScript 신규 프로젝트
- 6 화면 (APP-01 ~ APP-06)
- Android APK 빌드 후 `downloads/field-manager/`에 배치

---

## 로컬 검증 절차

### 1. 백엔드 (Docker)
```bash
cd cheonha
docker-compose down
docker-compose build backend
docker-compose up -d db backend
docker-compose logs -f backend  # 마이그레이션 진행 확인
```

마이그레이션 자동 실행됨 (`docker-compose.yml`의 `command`에 `migrate --fake-initial` 포함).
신규 스키마는 `0001_create_schema.py`에서 `CREATE SCHEMA IF NOT EXISTS` 실행.

### 2. 시드 데이터 (회사 3개)
```bash
docker-compose exec backend python manage.py shell
```
```python
from apps.vehicle_management.models import Company
Company.objects.bulk_create([
    Company(code='YUHAN',    name='유한',  sort_order=1),
    Company(code='CHEONHA',  name='천하',  sort_order=2),
    Company(code='PERSONAL', name='개인',  sort_order=3),
], ignore_conflicts=True)
```

### 3. 프론트엔드
```bash
cd frontend
npm install
npm run dev
```
포털 로그인 후 `/portal/vehicle/status` 진입 확인.

### 4. 현장관리자 앱
```bash
cd field-manager-app
npm install
npx expo start
```
PIN `2580`으로 로그인 가능. 실기기에서 백엔드 호스트 변경: `app.config.ts`의 `apiBaseUrl`.

### 5. APK 빌드 (Android)
```bash
cd field-manager-app
npm install -g eas-cli
eas login
eas build -p android --profile preview
# 산출 APK 다운로드 → downloads/field-manager/clever-fm-1.0.0.apk
```

---

## 프로덕션 배포 (43.201.160.163)

### 사전 점검
- [ ] `.pem` 키 파일 권한: `chmod 400 "CHEONHA (1).pem"` (WSL/Linux 환경)
- [ ] EC2 인스턴스 보안그룹: 인바운드 22(SSH), 80(HTTP) 열려있어야 함
- [ ] 현재 운영 중인 컨테이너 목록 확인: `docker-compose ps`
- [ ] DB 백업: `docker-compose exec db pg_dump -U cheonha cheonha > backup_$(date +%F).sql`

### 배포 명령 (Bash 또는 PowerShell)
```bash
# 1. 코드 업로드 (rsync)
rsync -avz -e "ssh -i 'CHEONHA (1).pem'" \
  --exclude node_modules --exclude __pycache__ --exclude '*.pyc' \
  --exclude .git --exclude _screenshots --exclude '*.pen' \
  ./ ubuntu@43.201.160.163:/home/ubuntu/cheonha/

# 2. SSH 접속
ssh -i "CHEONHA (1).pem" ubuntu@43.201.160.163

# 3. 서버에서:
cd /home/ubuntu/cheonha

# (a) 백업
docker-compose exec -T db pg_dump -U cheonha cheonha > backup_$(date +%F_%H%M).sql

# (b) 재빌드
docker-compose build backend frontend

# (c) 마이그레이션 + 재시작 (무중단 wish — 짧은 다운타임 발생)
docker-compose up -d --no-deps backend
docker-compose exec backend python manage.py migrate --noinput
docker-compose up -d --no-deps frontend nginx

# (d) 헬스 체크
curl -s http://localhost/api/v1/schema/ | head
docker-compose logs --tail 50 backend
```

### 시드 (회사 마스터)
```bash
docker-compose exec -T backend python manage.py shell <<'PY'
from apps.vehicle_management.models import Company
Company.objects.bulk_create([
    Company(code='YUHAN',    name='유한',  sort_order=1),
    Company(code='CHEONHA',  name='천하',  sort_order=2),
    Company(code='PERSONAL', name='개인',  sort_order=3),
], ignore_conflicts=True)
print(list(Company.objects.values_list('code', 'name')))
PY
```

### 롤백
```bash
git checkout <previous-commit>
docker-compose build backend frontend
docker-compose up -d --no-deps backend frontend nginx
# DB 복원 (필요 시)
cat backup_YYYY-MM-DD_HHMM.sql | docker-compose exec -T db psql -U cheonha cheonha
```

---

## 검증 체크리스트

- [ ] `docker-compose ps` — 모든 컨테이너 `Up`
- [ ] `curl http://43.201.160.163/api/v1/vehicle/companies/` — 3개 회사 반환
- [ ] 포털 `/portal/vehicle/status` — 차량 목록 화면 표시
- [ ] 포털 `/portal/vehicle/pit` — 인라인 편집 가능
- [ ] 포털 `/portal/vehicle/calendar` — 통합 일정 + 반납 불가일 등록
- [ ] 현장관리자 앱 PIN `2580`으로 로그인 → 구독 요청 등록 → 포털에 표시 확인
- [ ] 현장관리자 앱 반납 요청 시 캘린더 등록 불가일 disabled 동작 확인

---

## 알려진 미완 / 다음 작업

- `WEB-05` 구독 요청 차량 선택 모달 UI는 백엔드 `/subscriptions/{id}/assign/` 호출만 구현. 차량 그리드 선택 UI는 후속 작업.
- `WEB-06` 반납 가능/조정 분기 UI도 동일 (백엔드 `confirm`/`adjust` 동작).
- 차량현황 Excel 일괄 업로드 (`POST /vehicles/bulk-upload/`)는 미구현 — 다음 단계.
- 피트 `Excel 가져오기` 동일.
- A/S 처리 완료시 캘린더 자동 등록은 백엔드 `complete()` 액션에 추가 필요.
