#!/bin/bash
set -e

##############################################
# 천하운수 정산관리 시스템 - EC2 배포 스크립트
#
# 사용법:
#   EC2에 SSH 접속 후 이 스크립트를 실행합니다.
#   bash deploy-ec2.sh
#
# 전제조건:
#   - Ubuntu 22.04 EC2 인스턴스
#   - 인터넷 연결
#   - sudo 권한
##############################################

echo "=========================================="
echo "  천하운수 정산관리 시스템 배포 시작"
echo "=========================================="

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. 시스템 업데이트 및 필수 패키지 설치
log_info "시스템 패키지 업데이트 중..."
sudo apt-get update -qq
sudo apt-get install -y -qq git curl apt-transport-https ca-certificates gnupg lsb-release

# 2. Docker 설치 (이미 설치되어 있으면 스킵)
if ! command -v docker &> /dev/null; then
    log_info "Docker 설치 중..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    log_info "Docker 설치 완료"
else
    log_info "Docker 이미 설치됨: $(docker --version)"
fi

# 3. Docker Compose 설치 (standalone, 이미 있으면 스킵)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_info "Docker Compose 설치 중..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_info "Docker Compose 설치 완료"
else
    log_info "Docker Compose 이미 설치됨"
fi

# 4. GitHub CLI 설치 (이미 설치되어 있으면 스킵)
if ! command -v gh &> /dev/null; then
    log_info "GitHub CLI 설치 중..."
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq gh
    log_info "GitHub CLI 설치 완료"
else
    log_info "GitHub CLI 이미 설치됨: $(gh --version | head -1)"
fi

# 5. 프로젝트 디렉토리 설정
PROJECT_DIR="$HOME/cheonha"
log_info "프로젝트 디렉토리: $PROJECT_DIR"

if [ -d "$PROJECT_DIR" ]; then
    log_warn "기존 프로젝트 디렉토리가 존재합니다. 백업 후 계속합니다."
    mv "$PROJECT_DIR" "${PROJECT_DIR}.bak.$(date +%Y%m%d%H%M%S)"
fi

# 프로젝트 파일이 현재 디렉토리에 있는 경우 복사
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PARENT_DIR/docker-compose.yml" ]; then
    log_info "로컬 프로젝트 파일을 복사합니다..."
    cp -r "$PARENT_DIR" "$PROJECT_DIR"
else
    log_error "프로젝트 파일을 찾을 수 없습니다."
    log_info "프로젝트 파일을 먼저 EC2에 업로드해주세요:"
    log_info "  scp -i cheonha.pem -r ./cheonha ubuntu@54.180.88.180:~/"
    exit 1
fi

cd "$PROJECT_DIR"

# 6. 환경변수 설정
if [ ! -f .env ]; then
    log_info "환경변수 파일 생성 중..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 50 | tr -d '/+=' | head -c 50)
    DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null || openssl rand -base64 24 | tr -d '/+=' | head -c 24)

    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "54.180.88.180")

    cat > .env << EOF
# Django
DEBUG=False
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=${PUBLIC_IP},localhost,127.0.0.1

# Database
DB_PASSWORD=${DB_PASSWORD}

# CORS
CORS_ALLOWED_ORIGINS=http://${PUBLIC_IP},http://localhost

# Frontend API
VITE_API_BASE_URL=/api/v1

# Port
PORT=80
EOF
    log_info ".env 파일 생성 완료"
else
    log_info ".env 파일이 이미 존재합니다."
fi

# 7. Docker 빌드 및 실행
log_info "Docker 컨테이너 빌드 및 실행 중... (약 3~5분 소요)"

# docker compose 또는 docker-compose 사용
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

sudo $COMPOSE_CMD down 2>/dev/null || true
sudo $COMPOSE_CMD up -d --build

# 8. 컨테이너 상태 확인
log_info "컨테이너 상태 확인 중..."
sleep 10
sudo $COMPOSE_CMD ps

# 9. 관리자 계정 생성
log_info "관리자 계정 생성..."
sudo $COMPOSE_CMD exec -T backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@cheonha.com', 'admin1234!', role='ADMIN')
    print('관리자 계정 생성 완료: admin / admin1234!')
else:
    print('관리자 계정이 이미 존재합니다.')
" 2>/dev/null || log_warn "관리자 계정 생성은 컨테이너 시작 후 수동으로 해주세요."

echo ""
echo "=========================================="
echo -e "${GREEN}  배포 완료!${NC}"
echo "=========================================="
echo ""
echo "  웹사이트:    http://${PUBLIC_IP:-54.180.88.180}"
echo "  API 문서:    http://${PUBLIC_IP:-54.180.88.180}/api/schema/swagger/"
echo "  Django Admin: http://${PUBLIC_IP:-54.180.88.180}/admin/"
echo ""
echo "  관리자 계정: admin / admin1234!"
echo "  (첫 로그인 후 반드시 비밀번호를 변경하세요)"
echo ""
echo "=========================================="
