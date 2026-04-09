# 천하운수 정산관리 시스템 - 백엔드 설정 가이드

## 프로젝트 개요

Django REST Framework 기반의 천하운수 정산관리 시스템 백엔드입니다.

### 주요 기능
- 사용자 관리 및 인증 (JWT)
- 배차 데이터 업로드 및 검증
- 권역 관리 및 단가 설정
- 배송원 관리
- 정산 처리 및 정산서 생성
- 파트너사 관리
- 대시보드 및 KPI 조회

## 환경 설정

### 1. Python 가상 환경 설정

```bash
# 가상 환경 생성
python3 -m venv venv

# 가상 환경 활성화
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일에서 필요한 설정 수정
```

### 4. 데이터베이스 설정

#### SQLite (개발 환경)
기본적으로 SQLite를 사용합니다. 추가 설정이 필요 없습니다.

#### PostgreSQL (프로덕션)
```bash
# .env 파일에서 다음과 같이 설정
DB_ENGINE=postgresql
DB_NAME=cheonha
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. 데이터베이스 마이그레이션

```bash
# 마이그레이션 파일 생성
python manage.py makemigrations

# 마이그레이션 적용
python manage.py migrate
```

### 6. 슈퍼유저 생성

```bash
python manage.py createsuperuser
```

### 7. 서버 시작

```bash
python manage.py runserver
```

접속 URL: http://localhost:8000

## API 문서

- Swagger UI: http://localhost:8000/api/v1/docs/
- Schema: http://localhost:8000/api/v1/schema/

## 사용 가능한 API 엔드포인트

### 계정 관리 (Accounts)
- `POST /api/v1/accounts/token/` - JWT 토큰 발급 (로그인)
- `POST /api/v1/accounts/token/refresh/` - 토큰 갱신
- `GET /api/v1/accounts/users/` - 사용자 목록 조회
- `POST /api/v1/accounts/users/` - 사용자 생성 (관리자 권한)
- `GET /api/v1/accounts/users/me/` - 현재 사용자 정보
- `POST /api/v1/accounts/users/change_password/` - 비밀번호 변경
- `GET /api/v1/accounts/teams/` - 팀 목록 조회

### 배차 관리 (Dispatch)
- `GET /api/v1/dispatch/uploads/` - 배차 업로드 목록 조회
- `POST /api/v1/dispatch/uploads/` - 배차 파일 업로드
- `POST /api/v1/dispatch/uploads/{id}/validate/` - 배차 데이터 검증
- `POST /api/v1/dispatch/uploads/{id}/confirm/` - 배차 데이터 확정
- `GET /api/v1/dispatch/records/` - 배차 레코드 조회

### 권역 관리 (Region)
- `GET /api/v1/region/regions/` - 권역 목록 조회
- `GET /api/v1/region/prices/` - 권역별 단가 조회
- `POST /api/v1/region/prices/` - 권역 단가 생성
- `PUT /api/v1/region/prices/{id}/` - 권역 단가 수정
- `GET /api/v1/region/prices/{id}/price_history/` - 단가 변경 이력 조회

### 배송원 관리 (Crew)
- `GET /api/v1/crew/members/` - 배송원 목록 조회
- `GET /api/v1/crew/members/new_members/` - 신규 배송원 조회
- `POST /api/v1/crew/members/{id}/mark_registered/` - 신규 배송원 등록 완료
- `GET /api/v1/crew/overtime/` - 연장근무 설정 조회
- `POST /api/v1/crew/overtime/` - 연장근무 설정 생성

### 파트너사 관리 (Partner)
- `GET /api/v1/partner/partners/` - 파트너사 목록 조회
- `POST /api/v1/partner/partners/` - 파트너사 생성

### 정산 관리 (Settlement)
- `GET /api/v1/settlement/settlements/` - 정산 목록 조회
- `POST /api/v1/settlement/settlements/` - 정산 생성
- `POST /api/v1/settlement/settlements/{id}/confirm/` - 정산 확정
- `POST /api/v1/settlement/settlements/{id}/mark_paid/` - 정산 지급 완료
- `GET /api/v1/settlement/settlements/{id}/export/` - 정산서 내보내기 (CSV)
- `GET /api/v1/settlement/details/` - 정산 상세 조회
- `POST /api/v1/settlement/details/` - 정산 상세 생성

### 대시보드 (Dashboard)
- `GET /api/v1/dashboard/dashboard/kpi/` - KPI 조회
- `GET /api/v1/dashboard/dashboard/revenue_by_region/` - 권역별 수익 조회
- `GET /api/v1/dashboard/dashboard/settlement_summary/` - 정산 요약 조회
- `GET /api/v1/dashboard/dashboard/monthly_trend/` - 월별 추세 조회
- `GET /api/v1/dashboard/dashboard/crew_statistics/` - 배송원 통계 조회

## 권한 관리

### 역할 (Roles)
- `ADMIN` - 관리자 (모든 데이터 조회/수정 가능)
- `TEAM_LEADER` - 팀장 (자신의 팀 데이터만 조회/수정 가능)
- `APPROVER` - 승인자 (정산 확정 권한)
- `CREW` - 배송원 (자신의 정보만 조회 가능)

### 팀 (Teams)
- A팀
- X팀
- R팀

## 테스트 실행

```bash
# 전체 테스트 실행
python manage.py test

# 특정 앱 테스트 실행
python manage.py test apps.accounts

# 특정 테스트 클래스 실행
python manage.py test apps.accounts.tests.UserModelTests

# 커버리지 확인
coverage run --source='.' manage.py test
coverage report
```

## 관리자 페이지

http://localhost:8000/admin/

## 프로덕션 배포

### 1. 설정 변경

```bash
# .env 파일에서 DEBUG=False 설정
DEBUG=False
SECRET_KEY=your-secure-random-key-here
ALLOWED_HOSTS=your-domain.com
```

### 2. 정적 파일 수집

```bash
python manage.py collectstatic
```

### 3. Gunicorn으로 실행

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 4. Nginx 설정

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location /static/ {
        alias /path/to/backend/staticfiles/;
    }

    location /media/ {
        alias /path/to/backend/media/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 문제 해결

### 마이그레이션 오류
```bash
# 마이그레이션 상태 확인
python manage.py showmigrations

# 특정 마이그레이션 롤백
python manage.py migrate [app] [migration_name]
```

### 포트 이미 사용 중
```bash
# 다른 포트로 실행
python manage.py runserver 8001
```

### 데이터베이스 초기화
```bash
# 주의: 모든 데이터가 삭제됩니다
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

## 주요 기술 스택

- Django 4.2+
- Django REST Framework
- PostgreSQL / SQLite
- JWT Authentication
- drf-spectacular (API 문서)
- Python-decouple (환경 변수)
