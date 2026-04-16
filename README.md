# 천하운수 정산 관리 시스템

천하운수 정산 데이터를 웹과 모바일에서 함께 조회하고 관리하는 프로젝트입니다.

- 웹: 관리자/조장용 정산 관리
- 모바일 앱: 기사 개인 정산 조회 및 근무 기록

## 저장소 구성

- `backend/`: Django + DRF API
- `frontend/`: Vue 3 웹 프론트엔드
- `cheonha-settlement-app/`: Expo 기반 Android 앱
- `nginx/`: 배포용 Nginx 설정
- `docker-compose.yml`: 운영/개발용 컨테이너 구성

## 모바일 앱 현재 기준

모바일 앱은 현재 아래 흐름을 기준으로 동작합니다.

- 이름 + 조 + 비밀번호 로그인
- 초기 비밀번호 `0000` 로그인 시 비밀번호 변경 강제
- 초기 비밀번호 변경 시 차량번호도 함께 등록
- 로그인 상태는 앱 완전 종료 후에도 유지
- 차량번호는 사용자별로 분리 저장
- 캘린더 날짜 탭으로 정산 문의 팝업 진입
- 정산 문의 댓글 등록 및 날짜별 상태 점 표시
- 관리자 답변/읽음 처리 반영 시 앱에서 상태 점 갱신
- 근무 시작 시 BLE, 기압계, 위치, 카메라 이벤트를 수집
- 근무 종료 시 CSV 공유

## 웹 현재 기준

웹은 현재 아래 흐름을 기준으로 동작합니다.

- 관리자용 `정산 문의` 탭 제공
- 최신순 문의 목록, 팀 필터, 답변 필요 필터 제공
- 문의 상세에서 박스수/지급단가/조정금액 수정
- 댓글형 답변, 읽음 처리 지원

## APK 다운로드

아래 링크는 `main` 브랜치 기준 직접 다운로드 링크입니다.

### 1. 테스트 앱

- 파일: `downloads/mobile/cheonha-test-latest.apk`
- 다운로드: [cheonha-test-latest.apk](https://github.com/Heedo-Kim0624/cheonha/raw/main/downloads/mobile/cheonha-test-latest.apk)
- 용도: 테스트 서버 연결용
- 서버: `http://13.124.120.147`
- 앱 이름: `CLEVER_CH DEV`
- 최신 반영: 문의 완료 배지 즉시 반영, 문의 팝업 최신 대화 하단 표시, 문의 팝업 안정화
- 버전: `1.0.10` / `versionCode 12`
- SHA-256: `60A44B93BC868A643AECC9C74587D21A8A2032C59FDAE36A90352FF669A60F8A`

### 2. 운영 앱

- 파일: `downloads/mobile/clever-ch-production-latest.apk`
- 다운로드: [clever-ch-production-latest.apk](https://github.com/Heedo-Kim0624/cheonha/raw/main/downloads/mobile/clever-ch-production-latest.apk)
- 용도: 운영 서버 연결용
- 앱 이름: `CLEVER_CH`
- SHA-256: `302A964CE15E897A791FCAB091C9DF5B0339F7B667FEF77FCD7C7362FB6B49C2`

해시 검증용 파일:

- [SHA256SUMS.txt](https://github.com/Heedo-Kim0624/cheonha/raw/main/downloads/mobile/SHA256SUMS.txt)

## 로컬 실행

### 백엔드 + 웹

```bash
cp .env.example .env
docker compose up -d db
docker compose up -d
```

### 모바일 앱

```bash
cd cheonha-settlement-app
npm install
npx expo start
```

## Android 로컬 빌드

테스트 앱 예시:

```bash
cd cheonha-settlement-app
set APP_VARIANT=test
set APP_API_BASE_URL=http://13.124.120.147
set EXPO_PUBLIC_API_BASE_URL=http://13.124.120.147
npx expo prebuild --platform android
cd android
gradlew.bat assembleRelease
```

운영 앱은 `APP_VARIANT=production` 과 운영 서버 주소를 사용하면 됩니다.

## 비고

- `cheonha-settlement-app/apk-output/` 는 빌드 산출물 작업용 디렉터리이며 Git 추적 대상이 아닙니다.
- GitHub 다운로드용 APK는 `downloads/mobile/` 에 별도로 보관합니다.

## 라이선스

Private repository.
