# 배포 체크리스트

## 프로덕션 배포 전 확인 사항

### 1. 보안 설정
- [ ] `SECRET_KEY` 변경 (환경 변수에서 읽기)
- [ ] `DEBUG = False` 설정
- [ ] `ALLOWED_HOSTS` 올바르게 설정
- [ ] CORS 출처 제한
- [ ] HTTPS 활성화 (SSL 인증서 설정)
- [ ] 데이터베이스 비밀번호 강력하게 설정
- [ ] API 레이트 제한 설정
- [ ] CSRF 보호 활성화
- [ ] 세션 보안 설정

### 2. 데이터베이스 설정
- [ ] PostgreSQL 설치 및 구성
- [ ] 데이터베이스 생성
- [ ] 사용자 계정 생성
- [ ] 마이그레이션 실행: `python manage.py migrate`
- [ ] 정규 백업 계획 수립
- [ ] 데이터베이스 연결 풀 설정
- [ ] 인덱스 최적화

### 3. 정적/미디어 파일
- [ ] 정적 파일 수집: `python manage.py collectstatic`
- [ ] Nginx에서 정적 파일 서빙 설정
- [ ] 미디어 파일 저장소 설정
- [ ] 파일 업로드 크기 제한 설정
- [ ] 바이러스 스캔 고려

### 4. 로깅 및 모니터링
- [ ] 로그 파일 경로 설정
- [ ] 로그 순환 설정 (logrotate)
- [ ] 에러 모니터링 설정 (예: Sentry)
- [ ] 성능 모니터링 설정 (예: New Relic, DataDog)
- [ ] 보안 모니터링 설정

### 5. 애플리케이션 설정
- [ ] 환경 변수 파일 (.env) 설정
- [ ] 타임존 설정 (Asia/Seoul)
- [ ] 로케일 설정 (한국어)
- [ ] 이메일 설정 (SMTP)
- [ ] 캐시 설정 (Redis, Memcached)

### 6. 웹 서버 설정
- [ ] Gunicorn/uWSGI 설정
- [ ] Nginx 리버스 프록시 설정
- [ ] SSL/TLS 인증서 설정
- [ ] 압축 설정
- [ ] 캐시 헤더 설정
- [ ] 헬스 체크 엔드포인트 설정

### 7. 프로세스 관리
- [ ] Systemd 서비스 설정
- [ ] 자동 재시작 설정
- [ ] 프로세스 모니터링 설정
- [ ] 로그 수집 설정

### 8. 테스트
- [ ] 단위 테스트 실행: `python manage.py test`
- [ ] API 통합 테스트 실행
- [ ] 성능 테스트 실행
- [ ] 보안 테스트 실행
- [ ] 부하 테스트 실행

### 9. 데이터 마이그레이션
- [ ] 기존 데이터 백업
- [ ] 마이그레이션 스크립트 준비
- [ ] 마이그레이션 테스트 (스테이징 환경)
- [ ] 롤백 계획 수립

### 10. 문서화
- [ ] API 문서 최신화
- [ ] 배포 가이드 작성
- [ ] 운영 매뉴얼 작성
- [ ] 장애 대응 절차 문서화
- [ ] 팀 교육 실시

## 배포 단계

### 사전 준비 (배포 전 일주일)
```bash
# 1. 코드 최종 검토
git diff origin/main..HEAD

# 2. 마이그레이션 테스트
python manage.py migrate --plan

# 3. 정적 파일 테스트
python manage.py collectstatic --dry-run

# 4. 성능 테스트
python manage.py runserver --insecure
# 부하 테스트 도구로 테스트 (예: Apache Bench, wrk)
```

### 배포 일자 (배포 당일)
```bash
# 1. 데이터베이스 백업
pg_dump cheonha > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 애플리케이션 코드 배포
git pull origin main

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 마이그레이션 적용
python manage.py migrate

# 5. 정적 파일 수집
python manage.py collectstatic --noinput

# 6. 캐시 초기화
python manage.py clear_cache

# 7. 서비스 재시작
sudo systemctl restart django_app

# 8. 헬스 체크
curl https://your-domain.com/api/v1/health/

# 9. 로그 모니터링
tail -f /var/log/django_app.log

# 10. 모니터링 대시보드 확인
# 에러율, 응답 시간, 활성 사용자 수 등 모니터링
```

### 배포 후 (배포 후 24시간)
- [ ] 시스템 안정성 모니터링
- [ ] 에러 로그 검토
- [ ] 성능 지표 확인
- [ ] 사용자 피드백 수집
- [ ] 필요시 롤백 준비

## 롤백 계획

```bash
# 1. 마이그레이션 되돌리기
python manage.py migrate <previous_migration>

# 2. 코드 되돌리기
git revert <commit_hash>
git push origin main

# 3. 서비스 재시작
sudo systemctl restart django_app

# 4. 데이터베이스 복구 (필요시)
psql cheonha < backup_YYYYMMDD_HHMMSS.sql

# 5. 시스템 안정성 확인
curl https://your-domain.com/api/v1/health/
```

## 모니터링 항목

### 애플리케이션 메트릭
- 요청 처리 시간 (P50, P95, P99)
- 에러율
- 활성 사용자 수
- API 호출 수

### 시스템 메트릭
- CPU 사용률
- 메모리 사용률
- 디스크 사용률
- 네트워크 대역폭

### 데이터베이스 메트릭
- 연결 수
- 쿼리 응답 시간
- 느린 쿼리 로그
- 디스크 사용률

### 보안 메트릭
- 실패한 로그인 시도
- SQL 인젝션 시도
- DDoS 공격 감지

## 응급 대응

### 서버 다운
1. 헬스 체크 확인
2. 로그 확인: `sudo journalctl -u django_app -n 50`
3. 디스크 공간 확인: `df -h`
4. 메모리 확인: `free -h`
5. 프로세스 재시작: `sudo systemctl restart django_app`

### 데이터베이스 문제
1. 연결 수 확인: `SELECT count(*) FROM pg_stat_activity;`
2. 느린 쿼리 확인: `SELECT query, calls, total_time FROM pg_stat_statements;`
3. 인덱스 재구성: `REINDEX DATABASE cheonha;`
4. 진공 작업: `VACUUM ANALYZE;`

### 높은 CPU/메모리 사용률
1. 실행 중인 프로세스 확인: `ps aux`
2. 성능 프로필링: `python -m cProfile manage.py runserver`
3. 데이터베이스 쿼리 최적화
4. 캐싱 전략 검토

### 높은 에러율
1. 에러 로그 확인
2. 최근 배포 변경사항 검토
3. 롤백 고려
4. 관련 서비스 상태 확인

