# 현장관리자 앱 엄격 진단 및 직접배포 기록

## 적용일

- 2026-05-22

## 적용 범위

- 현장관리자 로그인 허용목록 추가
- 현장관리자 토큰 신원 기준 요청 저장
- 반납 사진 MIME/확장자/장당 10MB 제한
- 반납 요청 저장 transaction 처리
- 회사별 불가일 + 전사 공통 불가일 반영
- 현장관리자 앱 `1.0.9`, `versionCode 10` release APK 빌드

## 운영 반영 결과

- DB 백업: `/home/ubuntu/cheonha/backups/pre_field_manager_strict_20260522_152011.sql`
- 적용 마이그레이션: `field_manager.0003_field_manager_account`
- 허용목록 seed:
  - dry-run 후보 6개
  - apply 생성 6개
  - 재실행 dry-run 결과 `to_create=0`

## APK 산출물

- 최신 APK: `downloads/field-manager/clever-field-manager-latest.apk`
- 버전 보관본: `field-manager-app/apk-output/clever-field-manager-v1.0.9-vc10-20260522-151655.apk`
- SHA256: `7c9f7586156db4b5a2bdaad168d01dcf948f0e943070c2ad42ccf7d55d4205f9`
- package: `com.clever.fieldmanager`
- versionName: `1.0.9`
- versionCode: `10`
- signing SHA1: `5E:8F:16:06:2E:A3:CD:2C:4A:0D:54:78:76:BA:A6:F3:8C:AB:F6:25`
- signing SHA256: `FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:6F:89:9B:83:32:66:75:91:03:3B:9C`

## 검증

- `python manage.py check`: 통과
- `npx tsc --noEmit`: 통과
- Android `assembleRelease`: 통과
- 현장관리자 운영 로그인 smoke: 통과
- 현장관리자 미등록 로그인 차단 smoke: 통과
- 현장관리자 불가일 조회 smoke: 통과
- 현장관리자 요청 이력 조회 smoke: 통과
- ERP 운영 smoke: 통과
- backend/nginx 로그: 배포 후 새 5xx/traceback 없음

## 확인된 제약

- 로컬 Django 테스트는 SQLite가 `vehicle_mgmt`, `field_mgr` PostgreSQL schema 구조를 재현하지 못해 실행 불가.
- 운영 PostgreSQL test DB 테스트는 기존 `crew` 마이그레이션의 fresh DB 재생 문제로 중단됨.
- 실제 기기 UI scenario gate는 현재 `adb devices`에 연결 기기가 없어 미실행.

## 다음 조치

- 기존 `crew` 마이그레이션 fresh DB 재생 문제를 별도 회귀 테스트 정비 작업으로 분리한다.
- 실제 Android 기기를 연결한 뒤 로그인, 메인, 구독 요청, 반납, A/S, 이력 화면을 APK 실행 기준으로 캡처한다.
- 신규 현장관리자가 생기면 운영자가 `FieldManagerAccount`에 먼저 등록한 뒤 로그인하도록 운영 절차를 고정한다.
