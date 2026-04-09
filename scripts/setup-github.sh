#!/bin/bash
set -e

##############################################
# 천하운수 - GitHub 레포지토리 생성 및 푸시
#
# 사용법:
#   EC2에서 deploy-ec2.sh 실행 후:
#   bash setup-github.sh
#
# 전제조건:
#   - gh CLI 설치됨 (deploy-ec2.sh에서 자동 설치)
#   - GitHub 로그인 필요 (스크립트가 안내합니다)
##############################################

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

GITHUB_USER="Heedo-Kim0624"
REPO_NAME="cheonha"
PROJECT_DIR="$HOME/cheonha"

echo "=========================================="
echo "  GitHub 레포지토리 설정"
echo "=========================================="

# 1. GitHub CLI 로그인 확인
if ! gh auth status &> /dev/null; then
    log_info "GitHub 로그인이 필요합니다."
    log_info "아래 명령어로 로그인해주세요:"
    echo ""
    echo "  gh auth login"
    echo ""
    log_info "로그인 방법: HTTPS > 브라우저 인증 또는 토큰 입력"
    echo ""
    read -p "로그인 완료 후 Enter를 눌러주세요..."

    if ! gh auth status &> /dev/null; then
        log_warn "GitHub 로그인이 되지 않았습니다. 먼저 로그인해주세요."
        exit 1
    fi
fi

log_info "GitHub 로그인 확인: $(gh auth status 2>&1 | grep 'Logged in')"

# 2. 레포지토리 생성 (이미 존재하면 스킵)
if gh repo view "${GITHUB_USER}/${REPO_NAME}" &> /dev/null; then
    log_info "레포지토리가 이미 존재합니다: ${GITHUB_USER}/${REPO_NAME}"
else
    log_info "레포지토리 생성 중: ${GITHUB_USER}/${REPO_NAME}"
    gh repo create "${REPO_NAME}" \
        --private \
        --description "천하운수 정산관리 시스템 - 배송 파트너사 정산 자동화 웹 시스템" \
        --homepage "http://54.180.88.180" \
        || {
            log_warn "레포지토리 생성 실패. 수동으로 생성해주세요:"
            echo "  https://github.com/new"
            exit 1
        }
    log_info "레포지토리 생성 완료"
fi

# 3. Git 설정
cd "$PROJECT_DIR"

# .git이 없으면 초기화
if [ ! -d ".git" ]; then
    git init
    log_info "Git 저장소 초기화 완료"
fi

# Git 사용자 설정
git config user.name "Heedo Kim"
git config user.email "hdgim1240@gmail.com"

# 4. Remote 설정
REMOTE_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
if git remote get-url origin &> /dev/null; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi
log_info "Remote 설정: $REMOTE_URL"

# 5. 커밋 및 푸시
git add -A
git commit -m "feat: 천하운수 정산관리 시스템 초기 구축

- Django 4.2 + DRF 백엔드 (MSA 아키텍처, 8개 독립 앱)
- Vue 3 + Vite + Pinia + Tailwind CSS 프론트엔드
- Docker + Nginx + PostgreSQL 인프라
- JWT 인증, Feature Flags, 역할 기반 접근 제어
- 배차 데이터 업로드/검증, 조별 운영 (A/X/R조)
- 수신/지급 단가 관리, 특근 비용 관리
- 자동 정산 (수익 = 수신 - 지급 - 특근)
- 배송원 관리 (전화번호/차량번호, 미등록 자동 감지)" 2>/dev/null || log_info "변경사항 없음 (이미 커밋됨)"

git branch -M main
git push -u origin main --force

echo ""
echo "=========================================="
echo -e "${GREEN}  GitHub 푸시 완료!${NC}"
echo "=========================================="
echo ""
echo "  레포지토리: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "=========================================="
