# 천하운수 정산관리 시스템

택배 배송 정산을 위한 통합 관리 시스템입니다. 웹 관리자 대시보드와 기사용 모바일 앱을 포함합니다.

## 주요 기능

### 웹 (관리자/팀장)
- **배차 데이터 업로드**: 엑셀 배차표 → 자동 파싱 → 팀/배송원 감지
- **팀 단가 관리**: 팀별 수신단가 / 특근비용 설정, 기사별 지급단가
- **배송원 관리**: 등록/수정/삭제, 용차 구분, 조별 필터
- **정산 처리**: 배차 데이터 기반 자동 정산 (같은 날짜 합산), 조정비용 수정
- **운영 현황**: 날짜별 배송원/권역/박스 현황, 박스수 추이 차트 (1일/1주/1달/사용자지정)
- **권한 관리**: 관리자(전체) / 팀장(배차+배송원, 금액 비노출)

### 모바일 앱 (기사)
- **로그인**: 이름 + 조 + 비밀번호
- **월별 정산 조회**: 날짜별 박스수·지급액 캘린더 뷰
- **비밀번호 변경**
- **가입 승인 플로우**: 관리자가 웹에서 승인

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Django 4.2 + DRF + PostgreSQL 15 |
| Frontend (Web) | Vue 3 + Pinia + Tailwind CSS |
| Mobile App | React Native + Expo SDK 54 |
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
│   │   ├── mobile/      # 모바일 앱 API
│   │   └── dashboard/   # 대시보드
│   ├── config/          # Django 설정
│   └── Dockerfile
├── frontend/                    # 웹 (Vue 3)
│   ├── src/views/               # 페이지 컴포넌트
│   ├── src/components/          # 공통 컴포넌트 (TeamFilter 등)
│   └── Dockerfile
├── cheonha-settlement-app/      # 모바일 앱 (Expo)
│   ├── src/screens/             # Login, Calendar, Register 등
│   ├── src/services/api.ts      # API 클라이언트
│   ├── plugins/                 # Expo config plugins (cleartext 등)
│   └── app.config.ts
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── seed_data.py                 # 더미 데이터 시딩 스크립트
└── .env.example
```

## 배포 방법 (웹)

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 편집
```

### 2. Docker Compose 실행

```bash
docker compose up -d db
sleep 5

# 마이그레이션
docker compose run --rm backend sh -c \
  'python manage.py makemigrations accounts partner region dispatch crew settlement mobile && \
   python manage.py migrate --noinput'

# 관리자 계정 생성
docker compose run --rm backend sh -c \
  'DJANGO_SUPERUSER_PASSWORD=admin1234! python manage.py createsuperuser \
   --noinput --username admin --email admin@cheonha.local'

# 전체 서비스 시작
docker compose up -d

# (선택) 더미 데이터 시딩
docker compose exec -T backend python manage.py shell < seed_data.py
```

### 3. 접속

- 사이트: `http://<서버IP>`
- 관리자: admin / admin1234!
- 팀장 (시딩 시): teamleader / test1234!

## 모바일 앱 빌드

### 로컬 개발
```bash
cd cheonha-settlement-app
npm install
npx expo start
```

### APK 빌드 (EAS 클라우드)
```bash
npx eas build --platform android --profile preview
```

`app.config.ts`의 `extra.apiBaseUrl` 또는 환경변수 `EXPO_PUBLIC_API_BASE_URL` 로 서버 IP 지정. 기본값은 `appEnv === 'production'` 이면 운영 서버, 그 외엔 테스트 서버.

## 운영 플로우

1. **관리자**: 팀 관리에서 팀 생성 (A조, H조 등) + 단가 설정
2. **팀장**: 회원가입 → 관리자 승인 → 로그인
3. **배차표 업로드** → 신규 배송원 용차 구분/지급단가 설정 → 특근 설정 → 정산 생성
4. **관리자**: 정산 처리에서 조별 정산 내역 확인, 조정비용 수정
5. **기사**: 모바일 앱에서 가입 요청 → 관리자 승인 → 월별 정산 조회

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
