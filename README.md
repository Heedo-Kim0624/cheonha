# 천하운수 정산관리 시스템

택배 배송 정산을 위한 웹 기반 관리 시스템입니다.

## 주요 기능

- **배차 데이터 업로드**: 엑셀 배차표 업로드 → 자동 파싱 → 팀/배송원 감지
- **팀 단가 관리**: 팀별 수신단가, 지급단가, 특근비용 설정
- **특근 설정**: 배송원별 특근 여부 및 금액 설정
- **정산 처리**: 배차 데이터 기반 자동 정산 생성
- **배송원 관리**: 배송원 등록/수정/삭제, 용차 구분
- **권한 관리**: 관리자(전체 접근) / 팀장(배차+배송원만, 금액 비노출)

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Django 4.2 + DRF + PostgreSQL |
| Frontend | Vue 3 + Pinia + Tailwind CSS |
| 인증 | JWT (SimpleJWT) |
| 배포 | Docker Compose + Nginx |

## 프로젝트 구조

```
cheonha/
├── backend/
│   ├── apps/
│   │   ├── accounts/    # 사용자/팀 관리
│   │   ├── dispatch/    # 배차 업로드/파싱
│   │   ├── crew/        # 배송원 관리
│   │   ├── settlement/  # 정산 처리
│   │   ├── region/      # 권역 관리
│   │   └── dashboard/   # 대시보드
│   ├── config/          # Django 설정
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/       # 페이지 컴포넌트
│   │   ├── stores/      # Pinia 상태관리
│   │   ├── api/         # API 클라이언트
│   │   └── components/  # 공통 컴포넌트
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

## 배포 방법

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 값 설정
```

### 2. Docker Compose 실행

```bash
docker compose up -d db
sleep 5

# 마이그레이션
docker compose run --rm backend sh -c \
  'python manage.py makemigrations accounts partner region dispatch crew settlement && \
   python manage.py migrate --noinput'

# 관리자 계정 생성
docker compose run --rm backend sh -c \
  'DJANGO_SUPERUSER_PASSWORD=admin1234! python manage.py createsuperuser \
   --noinput --username admin --email admin@cheonha.local'

# 전체 서비스 시작
docker compose up -d
```

### 3. 접속

- 사이트: `http://<서버IP>`
- 관리자: admin / admin1234!

## 운영 플로우

1. **관리자**: 팀 관리에서 팀 생성 (H조, A조 등) + 단가 설정
2. **팀장**: 회원가입 → 관리자 승인 → 로그인
3. **배차표 업로드** → 신규 배송원 용차 구분 → 특근 설정 → 정산 생성
4. **관리자**: 정산 처리에서 조별 정산 내역 확인

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| SECRET_KEY | Django 시크릿 키 | (필수) |
| DB_PASSWORD | PostgreSQL 비밀번호 | cheonha_secure_2026 |
| ALLOWED_HOSTS | 허용 호스트 | * |
| DEBUG | 디버그 모드 | False |
| PORT | 서비스 포트 | 80 |

## 라이선스

Private - 천하운수 내부용
