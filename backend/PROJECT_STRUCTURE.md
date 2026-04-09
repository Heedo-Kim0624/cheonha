# 프로젝트 구조

## 디렉토리 레이아웃

```
backend/
├── config/                          # Django 프로젝트 설정
│   ├── __init__.py
│   ├── settings.py                  # Django 설정 (DB, 앱, 미들웨어, 기본 설정)
│   ├── urls.py                      # 프로젝트 URL 라우팅
│   ├── wsgi.py                      # WSGI 애플리케이션
│   ├── asgi.py                      # ASGI 애플리케이션 (비동기)
│   └── middleware.py                # Feature flag 미들웨어
│
├── apps/                            # Django 앱들 (비즈니스 로직)
│   ├── accounts/                    # 사용자 인증 및 역할 관리
│   │   ├── __init__.py
│   │   ├── models.py                # User, Team 모델
│   │   ├── serializers.py           # User, Team 직렬화
│   │   ├── views.py                 # 인증, 사용자, 팀 뷰
│   │   ├── urls.py                  # URL 라우팅
│   │   ├── admin.py                 # Django 관리자 등록
│   │   ├── apps.py                  # 앱 설정
│   │   └── tests.py                 # 단위 테스트
│   │
│   ├── common/                      # 공유 유틸리티
│   │   ├── __init__.py
│   │   ├── models.py                # AuditMixin 기본 모델
│   │   ├── serializers.py           # 공유 Serializer
│   │   ├── views.py                 # BaseViewSet 기본 뷰
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   ├── dispatch/                    # 배차 데이터 관리
│   │   ├── __init__.py
│   │   ├── models.py                # DispatchUpload, DispatchRecord 모델
│   │   ├── serializers.py           # 배차 직렬화
│   │   ├── views.py                 # 배차 업로드, 검증, 확정 뷰
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   ├── region/                      # 권역 및 단가 관리
│   │   ├── __init__.py
│   │   ├── models.py                # Region, RegionPrice, PriceHistory 모델
│   │   ├── serializers.py           # 권역 직렬화
│   │   ├── views.py                 # 권역, 단가, 이력 뷰
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   ├── settlement/                  # 정산 관리
│   │   ├── __init__.py
│   │   ├── models.py                # Settlement, SettlementDetail 모델
│   │   ├── serializers.py           # 정산 직렬화
│   │   ├── views.py                 # 정산 생성, 확정, 지급, 내보내기 뷰
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   ├── crew/                        # 배송원 관리
│   │   ├── __init__.py
│   │   ├── models.py                # CrewMember, OvertimeSetting 모델
│   │   ├── serializers.py           # 배송원 직렬화
│   │   ├── views.py                 # 배송원, 연장근무 뷰
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   ├── partner/                     # 파트너사 관리
│   │   ├── __init__.py
│   │   ├── models.py                # Partner 모델
│   │   ├── serializers.py           # 파트너사 직렬화
│   │   ├── views.py                 # 파트너사 뷰
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   └── tests.py
│   │
│   └── dashboard/                   # 대시보드 및 KPI
│       ├── __init__.py
│       ├── models.py                # 모델 없음 (데이터 집계)
│       ├── serializers.py           # KPI, 수익 직렬화
│       ├── views.py                 # KPI, 월별 추세, 배송원 통계 뷰
│       ├── urls.py
│       ├── admin.py
│       ├── apps.py
│       └── tests.py
│
├── logs/                            # 로그 파일 (자동 생성)
│   └── django.log
│
├── media/                           # 업로드 파일 저장소 (자동 생성)
│   └── dispatch/
│       └── {year}/{month}/{day}/
│           └── {파일명}
│
├── static/                          # 정적 파일 (CSS, JS 등)
│   └── (프론트엔드 정적 파일)
│
├── staticfiles/                     # 수집된 정적 파일 (프로덕션)
│   └── (collectstatic으로 생성)
│
├── templates/                       # Django 템플릿
│   └── (필요시 추가)
│
├── manage.py                        # Django 관리 명령어
├── requirements.txt                 # Python 패키지 의존성
├── .env.example                     # 환경 변수 템플릿
├── .gitignore                       # Git 무시 파일
├── SETUP.md                         # 설정 가이드
├── PROJECT_STRUCTURE.md             # 이 파일
└── db.sqlite3                       # SQLite 데이터베이스 (개발)

```

## 각 앱의 역할

### accounts (계정 관리)
- **목적**: 사용자 인증, 역할 관리, 팀 관리
- **주요 모델**: User, Team
- **주요 기능**:
  - JWT 토큰 발급
  - 사용자 생성/조회/수정
  - 비밀번호 변경
  - 팀 관리

### common (공유 유틸리티)
- **목적**: 모든 앱에서 공유하는 기본 기능 제공
- **주요 기능**:
  - AuditMixin: 생성자/수정자 자동 기록
  - BaseViewSet: 권한 검증 및 팀 필터링

### dispatch (배차 관리)
- **목적**: 배차 파일 업로드, 검증, 확정
- **주요 모델**: DispatchUpload, DispatchRecord
- **주요 기능**:
  - Excel/CSV 파일 업로드
  - 데이터 유효성 검증
  - 배차 데이터 확정
  - 오류 메시지 기록

### region (권역 관리)
- **목적**: 배송 권역과 단가 관리
- **주요 모델**: Region, RegionPrice, PriceHistory
- **주요 기능**:
  - 권역 생성/조회/수정
  - 수신단가/지급단가 관리
  - 단가 변경 이력 추적
  - 팀별 권역 관리

### settlement (정산 관리)
- **목적**: 정산 처리 및 정산서 생성
- **주요 모델**: Settlement, SettlementDetail
- **주요 기능**:
  - 정산 기간 정의
  - 배송원별 정산 상세 정보
  - 이윤 계산 자동화
  - 정산 확정 및 지급 상태 관리
  - CSV 내보내기

### crew (배송원 관리)
- **목적**: 배송원 정보 및 연장근무 관리
- **주요 모델**: CrewMember, OvertimeSetting
- **주요 기능**:
  - 배송원 생성/조회/수정
  - 신규 배송원 자동 감지
  - 연장근무 설정 및 비용 관리

### partner (파트너사 관리)
- **목적**: 배송사 정보 관리
- **주요 모델**: Partner
- **주요 기능**:
  - 파트너사 생성/조회/수정
  - 계약 기간 관리

### dashboard (대시보드)
- **목적**: 경영 지표 및 통계 제공
- **주요 기능**:
  - KPI 조회 (총 정산, 수익, 이윤)
  - 권역별 수익 분석
  - 월별 추세 분석
  - 배송원 통계

## 모델 관계도

```
User ──┬─→ Team ──→ Region ──→ RegionPrice ──→ PriceHistory
       │           ↓
       │        CrewMember ──→ OvertimeSetting
       │           ↓
       ├─→ DispatchUpload ──→ DispatchRecord
       │
       ├─→ Settlement ──→ SettlementDetail
       │
       └─→ (기타 감시 정보)

Partner ──→ CrewMember
```

## API 엔드포인트 구조

```
/api/v1/
├── accounts/
│   ├── token/               (로그인)
│   ├── token/refresh/       (토큰 갱신)
│   ├── users/               (사용자 CRUD)
│   │   └── {id}/
│   │       ├── change_password/
│   │       └── me/
│   └── teams/               (팀 CRUD)
│
├── dispatch/
│   ├── uploads/             (배차 업로드 CRUD)
│   │   └── {id}/
│   │       ├── validate/
│   │       └── confirm/
│   └── records/             (배차 레코드 조회)
│
├── region/
│   ├── regions/             (권역 CRUD)
│   ├── prices/              (권역 단가 CRUD)
│   │   └── {id}/
│   │       └── price_history/
│   └── price-history/       (단가 이력 조회)
│
├── settlement/
│   ├── settlements/         (정산 CRUD)
│   │   └── {id}/
│   │       ├── confirm/
│   │       ├── mark_paid/
│   │       └── export/
│   └── details/             (정산 상세 CRUD)
│
├── crew/
│   ├── members/             (배송원 CRUD)
│   │   ├── new_members/
│   │   └── {id}/
│   │       └── mark_registered/
│   └── overtime/            (연장근무 설정 CRUD)
│
├── partner/
│   └── partners/            (파트너사 CRUD)
│
└── dashboard/
    └── dashboard/
        ├── kpi/
        ├── revenue_by_region/
        ├── settlement_summary/
        ├── monthly_trend/
        └── crew_statistics/
```

## 인증 및 권한

### 인증 방식
- JWT (JSON Web Token)
- 헤더: `Authorization: Bearer {access_token}`

### 역할별 접근 제어
```
ADMIN          → 모든 데이터 조회/수정 가능
TEAM_LEADER    → 자신의 팀 데이터만 조회/수정 가능
APPROVER       → 정산 확정 권한
CREW           → 자신의 정보만 조회 가능
```

## 개발 가이드

### 새 앱 추가하기

1. `apps/{app_name}/` 디렉토리 생성
2. 필수 파일 생성:
   - `__init__.py`
   - `models.py`
   - `serializers.py`
   - `views.py`
   - `urls.py`
   - `admin.py`
   - `apps.py`
   - `tests.py`
3. `config/settings.py`의 `INSTALLED_APPS`에 앱 추가
4. `config/urls.py`에 URL 라우팅 추가

### 새 모델 추가하기

1. `models.py`에 모델 클래스 정의
2. `serializers.py`에 Serializer 정의
3. `views.py`에 ViewSet 정의
4. `urls.py`에 라우터 등록
5. `admin.py`에 관리자 등록
6. 마이그레이션 생성: `python manage.py makemigrations`
7. 마이그레이션 적용: `python manage.py migrate`

### 테스트 작성

```python
# {app}/tests.py
from django.test import TestCase
from rest_framework.test import APITestCase

class MyModelTests(TestCase):
    def setUp(self):
        # 테스트 데이터 설정
        pass

    def test_model_creation(self):
        # 모델 테스트
        pass

class MyAPITests(APITestCase):
    def test_endpoint(self):
        # API 테스트
        pass
```

## 배포 고려사항

- DEBUG=False 설정
- SECRET_KEY 변경
- ALLOWED_HOSTS 설정
- PostgreSQL 사용 권장
- 정적 파일 수집 (collectstatic)
- Gunicorn + Nginx 구성
- SSL/HTTPS 설정
- 로그 모니터링
- 정기적인 백업

