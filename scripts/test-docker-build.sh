#!/bin/bash
# AI-CICD Docker 构建测试脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 项目根目录
PROJECT_ROOT="/home/kerfs/AI-CICD-new"
cd "$PROJECT_ROOT"

echo ""
echo "======================================"
echo "  AI-CICD Docker 构建测试"
echo "======================================"
echo ""

# 1. 检查 Docker 权限
log_info "检查 Docker 权限..."
if ! docker ps &> /dev/null; then
    log_error "Docker 权限不足"
    log_info "当前用户: $(whoami)"
    log_info "当前用户组: $(groups)"
    echo ""
    log_warning "解决方案："
    echo "  方案1（推荐）：将当前用户添加到 docker 组"
    echo "    sudo usermod -aG docker \$USER"
    echo "    newgrp docker"
    echo "    # 或者重新登录"
    echo ""
    echo "  方案2：使用 sudo 运行此脚本"
    echo "    sudo $0"
    echo ""
    exit 1
fi

log_success "Docker 权限正常 ✓"

# 2. 检查必要文件
log_info "检查必要文件..."

REQUIRED_FILES=(
    "Dockerfile"
    "Dockerfile.dev"
    ".dockerignore"
    "requirements.txt"
    "frontend/Dockerfile"
    "frontend/nginx.conf"
    "frontend/package.json"
)

MISSING_FILES=()
for FILE in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$FILE" ]; then
        MISSING_FILES+=("$FILE")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    log_error "缺少必要文件:"
    for FILE in "${MISSING_FILES[@]}"; do
        echo "  - $FILE"
    done
    exit 1
fi

log_success "所有必要文件存在 ✓"

# 3. 检查 Docker Compose
log_info "检查 Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "未安装 Docker Compose"
    exit 1
fi

log_success "Docker Compose 已安装 ✓"

# 4. 构建测试
echo ""
log_info "开始构建测试..."
echo ""

# 测试1：构建后端生产镜像
log_info "测试1：构建后端生产镜像..."
echo "命令：docker build -t ai-cicd-backend:test -f Dockerfile ."
echo ""

if docker build -t ai-cicd-backend:test -f Dockerfile .; then
    log_success "后端镜像构建成功 ✓"
    BACKEND_SIZE=$(docker images ai-cicd-backend:test --format "{{.Size}}")
    log_info "镜像大小: $BACKEND_SIZE"
else
    log_error "后端镜像构建失败"
    exit 1
fi

echo ""

# 测试2：构建后端开发镜像
log_info "测试2：构建后端开发镜像..."
echo "命令：docker build -t ai-cicd-backend:dev -f Dockerfile.dev ."
echo ""

if docker build -t ai-cicd-backend:dev -f Dockerfile.dev .; then
    log_success "开发镜像构建成功 ✓"
    DEV_SIZE=$(docker images ai-cicd-backend:dev --format "{{.Size}}")
    log_info "镜像大小: $DEV_SIZE"
else
    log_error "开发镜像构建失败"
    exit 1
fi

echo ""

# 测试3：构建前端镜像
log_info "测试3：构建前端镜像..."
echo "命令：docker build -t ai-cicd-frontend:test ./frontend/"
echo ""

if docker build -t ai-cicd-frontend:test ./frontend/; then
    log_success "前端镜像构建成功 ✓"
    FRONTEND_SIZE=$(docker images ai-cicd-frontend:test --format "{{.Size}}")
    log_info "镜像大小: $FRONTEND_SIZE"
else
    log_error "前端镜像构建失败"
    exit 1
fi

# 5. 镜像大小对比
echo ""
log_info "镜像大小汇总:"
echo ""
docker images | grep "ai-cicd-" | grep -E "test|dev"

# 6. 清理测试镜像
echo ""
read -p "是否清理测试镜像？[Y/n]: " cleanup
if [[ ! $cleanup =~ ^[Nn]$ ]]; then
    log_info "清理测试镜像..."
    docker rmi ai-cicd-backend:test ai-cicd-backend:dev ai-cicd-frontend:test 2>/dev/null || true
    log_success "测试镜像已清理 ✓"
fi

# 7. 测试 docker-compose 配置
echo ""
log_info "测试 docker-compose 配置语法..."
if docker compose config > /dev/null 2>&1; then
    log_success "docker-compose.yml 语法正确 ✓"
else
    log_error "docker-compose.yml 语法错误"
    docker compose config
fi

if docker compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
    log_success "docker-compose.prod.yml 语法正确 ✓"
else
    log_error "docker-compose.prod.yml 语法错误"
    docker compose -f docker-compose.prod.yml config
fi

# 8. 总结
echo ""
echo "======================================"
log_success "所有构建测试通过！"
echo "======================================"
echo ""
echo "镜像已准备好，可以部署："
echo ""
echo "  开发环境："
echo "    docker compose up -d"
echo ""
echo "  生产环境："
echo "    ./scripts/deploy.sh"
echo ""
