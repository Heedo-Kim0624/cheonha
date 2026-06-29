# CLEVER 현장관리자 앱

현장관리자(유한/천하/개인 소속)가 구독 요청·반납·A/S 요청을 등록하는 React Native(Expo) 앱.

## 화면
| ID | 화면 | 비고 |
|---|---|---|
| APP-01 | 로그인 | 회사 + 조 + 전화번호 + PIN(공통 2580) |
| APP-02 | 메인 | 구독 관리 / A/S |
| APP-03 | 구독 관리 메뉴 | 요청 / 반납 (변경 메뉴 제거) |
| APP-04 | 구독 요청 | 날짜 + 대수 (반납 불가일 미적용) |
| APP-05 | 구독 반납 | 차량번호 + 사유 + 날짜 + 시간(10:00~16:00) |
| APP-06 | A/S 요청 | 차량번호 + 사유 |

## 빌드
```
npm install
npx expo start
# Android APK
npx eas build -p android --profile preview
```

빌드 결과물은 `downloads/field-manager/clever-fm-{version}.apk`에 배치 (운영 정책).

## 환경변수
- `EXPO_PUBLIC_API_BASE_URL` (기본: `http://43.201.160.163/api/v1`)

## 백엔드 연동
- `POST /api/v1/field-manager/login/`           — PIN 2580 검증 + JWT 발급
- `POST /api/v1/field-manager/subscription-requests/`
- `POST /api/v1/field-manager/return-requests/`  — 반납 불가일 검증 + 시간 10~16
- `POST /api/v1/field-manager/as-requests/`
- `GET  /api/v1/field-manager/blocked-dates/?company_code=...`
