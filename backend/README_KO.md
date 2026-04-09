# 천하운수 정산관리 시스템 - 백엔드 API

## 프로젝트 개요

천하운수 정산관리 시스템의 Django REST Framework 기반 백엔드입니다.

- 배차 데이터 관리 및 검증
- 배송원 정산 자동화
- 권역별 단가 관리
- 실시간 대시보드 및 KPI
- 역할 기반 접근 제어 (RBAC)

## 빠른 시작

### 1. 환경 설정

```bash
# 가상 환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정 (필요시)
```

### 2. 데이터베이스 초기화

```bash
# 마이그레이션 실행
python manage.py makemigrations
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 3. 서버 시작

```bash
python manage.py runserver

# http://localhost:8000/api/v1/docs/ 에서 API 문서 확인
```

## 주요 기능

### 계정 관리 (Accounts)
- JWT 기반 인증
- 사용자 및 팀 관리
- 역할 기반 접근 제어 (ADMIN, TEAM_LEADER, APPROVER, CREW)
- 비밀번호 변경

### 배차 관리 (Dispatch)
- Excel/CSV 파일 업로드
- 자동 데이터 유효성 검증
- 배차 데이터 확정
- 오류 이력 추적

### 권역 및 단가 (Region)
- 배송 권역 생성/관리
- 수신단가(배송사 요금) 관리
- 지급단가(배송원 보수) 관리
- 단가 변경 이력 추적

### 배송원 관리 (Crew)
- 배송원 정보 관리
- 신규 배송원 자동 감지
- 연장근무 설정 및 비용 관리
- 팀별 배송원 관리

### 정산 관리 (Settlement)
- 정산 기간별 처리
- 배송원별 정산 상세 정보
- 자동 이윤 계산
- 정산서 CSV 내보내기
- 정산 확정 및 지급 상태 관리

### 파트너사 관리 (Partner)
- 배송사 정보 관리
- 계약 기간 관리

### 대시보드 (Dashboard)
- KPI 조회 (총 정산, 수익, 이윤)
- 권역별 수익 분석
- 월별 추세 분석
- 배송원 통계

## 기술 스택

- **Framework**: Django 4.2+
- **API**: Django REST Framework 3.14+
- **인증**: djangorestframework-simplejwt
- **데이터베이스**: PostgreSQL / SQLite
- **문서**: drf-spectacular (Swagger UI)
- **배포**: Gunicorn + Nginx

## 프로젝트 구조

```
backend/
├── config/                  # Django 설정
├── apps/                    # 비즈니스 로직
│   ├── accounts/           # 사용자 관리
│   ├── dispatch/           # 배차 관리
│   ├── region/             # 권역 및 단가
│   ├── settlement/         # 정산 관리
│   ├── crew/               # 배송원 관리
│   ├── partner/            # 파트너사 관리
│   ├── dashboard/          # 대시보드
│   └── common/             # 공유 유틸리티
├── manage.py               # Django 관리 명령어
├── requirements.txt        # 패키지 의존성
└── SETUP.md               # 상세 설정 가이드
```

## API 엔드포인트

### 인증
- `POST /api/v1/accounts/token/` - 로그인 (JWT 발급)
- `POST /api/v1/accounts/token/refresh/` - 토큰 갱신

### 사용자
- `GET /api/v1/accounts/users/` - 사용자 목록
- `POST /api/v1/accounts/users/` - 사용자 생성 (관리자)
- `GET /api/v1/accounts/users/me/` - 현재 사용자 정보
- `POST /api/v1/accounts/users/change_password/` - 비밀번호 변경

### 배차
- `GET /api/v1/dispatch/uploads/` - 업로드 목록
- `POST /api/v1/dispatch/uploads/` - 파일 업로드
- `POST /api/v1/dispatch/uploads/{id}/validate/` - 데이터 검증
- `POST /api/v1/dispatch/uploads/{id}/confirm/` - 데이터 확정

### 권역
- `GET /api/v1/region/regions/` - 권역 목록
- `GET /api/v1/region/prices/` - 단가 목록
- `POST /api/v1/region/prices/` - 단가 생성
- `PUT /api/v1/region/prices/{id}/` - 단가 수정
- `GET /api/v1/region/prices/{id}/price_history/` - 변경 이력

### 배송원
- `GET /api/v1/crew/members/` - 배송원 목록
- `GET /api/v1/crew/members/new_members/` - 신규 배송원
- `GET /api/v1/crew/overtime/` - 연장근무 설정

### 정산
- `GET /api/v1/settlement/settlements/` - 정산 목록
- `POST /api/v1/settlement/settlements/` - 정산 생성
- `POST /api/v1/settlement/settlements/{id}/confirm/` - 정산 확정
- `POST /api/v1/settlement/settlements/{id}/mark_paid/` - 지급 완료
- `GET /api/v1/settlement/settlements/{id}/export/` - CSV 내보내기

### 대시보드
- `GET /api/v1/dashboard/dashboard/kpi/` - KPI 조회
- `GET /api/v1/dashboard/dashboard/revenue_by_region/` - 권역별 수익
- `GET /api/v1/dashboard/dashboard/settlement_summary/` - 정산 요약
- `GET /api/v1/dashboard/dashboard/monthly_trend/` - 월별 추세
- `GET /api/v1/dashboard/dashboard/crew_statistics/` - 배송원 통계

## 역할 및 권한

| 역할 | 권한 | 설명 |
|------|------|------|
| ADMIN | 전체 권한 | 모든 데이터 조회/수정 가능 |
| TEAM_LEADER | 팀 권한 | 자신의 팀 데이터만 조회/수정 가능 |
| APPROVER | 승인 권한 | 정산 확정 권한 |
| CREW | 조회 권한 | 자신의 정보만 조회 가능 |

## 데이터 모델

### User (사용자)
```python
{
    "id": 1,
    "username": "user123",
    "email": "user@example.com",
    "first_name": "김",
    "last_name": "배송",
    "role": "CREW",
    "team": 1,
    "phone": "010-1234-5678",
    "is_active": true
}
```

### Settlement (정산)
```python
{
    "id": 1,
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "team": 1,
    "status": "CONFIRMED",
    "total_receive": 1000000,
    "total_pay": 800000,
    "total_overtime": 50000,
    "total_profit": 150000
}
```

### DispatchUpload (배차 업로드)
```python
{
    "id": 1,
    "team": 1,
    "upload_date": "2024-01-15T10:30:00Z",
    "total_rows": 100,
    "success_rows": 98,
    "error_rows": 2,
    "status": "VALIDATED"
}
```

## 테스트

```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트
python manage.py test apps.accounts

# 커버리지 확인
coverage run --source='.' manage.py test
coverage report
coverage html  # HTML 리포트 생성
```

## 프로덕션 배포

### 1. 환경 설정
```bash
# .env 파일 수정
DEBUG=False
SECRET_KEY=your-secure-random-key
DB_ENGINE=postgresql
ALLOWED_HOSTS=your-domain.com
```

### 2. 정적 파일 수집
```bash
python manage.py collectstatic --noinput
```

### 3. Gunicorn 실행
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 4. Nginx 설정
[SETUP.md](SETUP.md)의 Nginx 설정 섹션 참조

## 문제 해결

### 마이그레이션 오류
```bash
python manage.py showmigrations
python manage.py migrate [app] [migration_name]
```

### 포트 충돌
```bash
python manage.py runserver 8001
```

### 데이터베이스 초기화
```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

## 주요 설정 파일

- **settings.py**: Django 설정 (DB, 앱, 미들웨어)
- **urls.py**: URL 라우팅
- **requirements.txt**: Python 의존성
- **.env**: 환경 변수 (개발용)
- **SETUP.md**: 상세 설정 가이드
- **PROJECT_STRUCTURE.md**: 프로젝트 구조 설명
- **DEPLOYMENT_CHECKLIST.md**: 배포 체크리스트

## 추가 문서

- [SETUP.md](SETUP.md) - 환경 설정 상세 가이드
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 프로젝트 구조 설명
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - 배포 체크리스트

## 지원

문제 발생 시 다음을 확인하세요:
1. 로그 파일 확인: `tail -f logs/django.log`
2. Django 관리자 페이지: `http://localhost:8000/admin/`
3. API 문서: `http://localhost:8000/api/v1/docs/`
4. 설정 가이드: [SETUP.md](SETUP.md)

## 라이선스

Copyright (c) 2024 천하운수. All rights reserved.

