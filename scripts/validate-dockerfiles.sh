#!/bin/bash
# Dockerfile 语法和配置验证脚本（不需要 Docker daemon）

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

PROJECT_ROOT="/home/kerfs/AI-CICD-new"
cd "$PROJECT_ROOT"

echo ""
echo "======================================"
echo "  Dockerfile 配置验证"
echo "======================================"
echo ""

ERRORS=0
WARNINGS=0

# 1. 检查文件存在性
log_info "检查文件存在性..."

check_file() {
    local file=$1
    local required=$2

    if [ -f "$file" ]; then
        log_success "✓ $file"
        return 0
    else
        if [ "$required" = "required" ]; then
            log_error "✗ $file (必需)"
            ((ERRORS++))
        else
            log_warning "✗ $file (可选)"
            ((WARNINGS++))
        fi
        return 1
    fi
}

check_file "Dockerfile" "required"
check_file "Dockerfile.dev" "optional"
check_file ".dockerignore" "required"
check_file "requirements.txt" "required"
check_file "frontend/Dockerfile" "required"
check_file "frontend/.dockerignore" "optional"
check_file "frontend/nginx.conf" "required"
check_file "frontend/package.json" "required"
check_file "docker-compose.yml" "required"
check_file "docker-compose.prod.yml" "optional"

echo ""

# 2. 检查 Dockerfile 语法
log_info "检查 Dockerfile 语法..."

check_dockerfile_syntax() {
    local file=$1
    local errors=0

    if [ ! -f "$file" ]; then
        return 1
    fi

    # 检查基本指令
    if ! grep -q "^FROM" "$file"; then
        log_error "$file: 缺少 FROM 指令"
        ((errors++))
    fi

    if ! grep -q "^WORKDIR" "$file"; then
        log_warning "$file: 缺少 WORKDIR 指令"
        ((errors++))
    fi

    if ! grep -q "^EXPOSE" "$file"; then
        log_warning "$file: 缺少 EXPOSE 指令"
        ((errors++))
    fi

    if ! grep -q "^HEALTHCHECK" "$file"; then
        log_warning "$file: 缺少 HEALTHCHECK 指令（推荐）"
    fi

    # 检查多阶段构建
    if grep -q "^FROM.*AS" "$file"; then
        log_success "$file: 使用多阶段构建 ✓"
    fi

    # 检查非 root 用户
    if grep -q "^USER" "$file"; then
        log_success "$file: 使用非 root 用户 ✓"
    fi

    if [ $errors -eq 0 ]; then
        log_success "$file: 语法检查通过 ✓"
        return 0
    else
        return 1
    fi
}

check_dockerfile_syntax "Dockerfile"
check_dockerfile_syntax "Dockerfile.dev"
check_dockerfile_syntax "frontend/Dockerfile"

echo ""

# 3. 检查 .dockerignore
log_info "检查 .dockerignore 配置..."

check_dockerignore() {
    local file=$1

    if [ ! -f "$file" ]; then
        log_warning "$file: 不存在"
        return 1
    fi

    local should_ignore=("node_modules" ".git" "*.pyc" "__pycache__" "*.md" ".env")

    for item in "${should_ignore[@]}"; do
        if grep -q "$item" "$file"; then
            log_success "$file: 忽略 $item ✓"
        else
            log_warning "$file: 应该忽略 $item"
        fi
    done
}

check_dockerignore ".dockerignore"
check_dockerignore "frontend/.dockerignore"

echo ""

# 4. 检查依赖文件
log_info "检查依赖文件..."

if [ -f "requirements.txt" ]; then
    log_success "requirements.txt 存在 ✓"

    # 检查关键依赖
    REQUIRED_PACKAGES=("fastapi" "uvicorn" "pydantic" "sqlalchemy" "redis" "celery")

    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if grep -qi "$pkg" requirements.txt; then
            log_success "  ✓ $pkg"
        else
            log_error "  ✗ 缺少 $pkg"
            ((ERRORS++))
        fi
    done
fi

if [ -f "frontend/package.json" ]; then
    log_success "frontend/package.json 存在 ✓"

    # 检查是否有 build 脚本
    if grep -q '"build"' frontend/package.json; then
        log_success "  ✓ 有 build 脚本"
    else
        log_error "  ✗ 缺少 build 脚本"
        ((ERRORS++))
    fi
fi

echo ""

# 5. 检查 nginx 配置
log_info "检查 nginx 配置..."

if [ -f "frontend/nginx.conf" ]; then
    log_success "frontend/nginx.conf 存在 ✓"

    # 检查关键配置
    if grep -q "proxy_pass" frontend/nginx.conf; then
        log_success "  ✓ 配置了反向代理"
    else
        log_warning "  ⚠ 可能缺少反向代理配置"
    fi

    if grep -q "gzip" frontend/nginx.conf; then
        log_success "  ✓ 启用了 gzip 压缩"
    fi

    if grep -q "try_files.*index.html" frontend/nginx.conf; then
        log_success "  ✓ 配置了 SPA 路由支持"
    fi
fi

echo ""

# 6. 检查 docker-compose 配置
log_info "检查 docker-compose 配置..."

if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    if [ -f "docker-compose.yml" ]; then
        if docker compose config > /dev/null 2>&1; then
            log_success "docker-compose.yml 语法正确 ✓"
        else
            log_error "docker-compose.yml 语法错误"
            docker compose config
            ((ERRORS++))
        fi
    fi

    if [ -f "docker-compose.prod.yml" ]; then
        if docker compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
            log_success "docker-compose.prod.yml 语法正确 ✓"
        else
            log_error "docker-compose.prod.yml 语法错误"
            docker compose -f docker-compose.prod.yml config
            ((ERRORS++))
        fi
    fi
else
    log_warning "Docker Compose 未安装，跳过语法检查"
fi

echo ""

# 7. 检查文件大小和性能
log_info "检查文件大小..."

check_file_size() {
    local file=$1
    local max_size=$2

    if [ -f "$file" ]; then
        local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)

        if [ $size -gt $max_size ]; then
            log_warning "$file: 文件较大 ($((size/1024))KB)"
        else
            log_success "$file: 大小正常 ($((size/1024))KB)"
        fi
    fi
}

check_file_size "Dockerfile" 10240  # 10KB
check_file_size "frontend/Dockerfile" 10240
check_file_size "docker-compose.yml" 51200  # 50KB
check_file_size "docker-compose.prod.yml" 51200

echo ""

# 8. 生成报告
echo "======================================"
if [ $ERRORS -eq 0 ]; then
    log_success "所有检查通过！"
else
    log_error "发现 $ERRORS 个错误"
fi

if [ $WARNINGS -gt 0 ]; then
    log_warning "发现 $WARNINGS 个警告"
fi
echo "======================================"
echo ""

# 9. 下一步建议
if [ $ERRORS -eq 0 ]; then
    log_info "下一步操作："
    echo ""
    echo "  1. 修复 Docker 权限（如果需要）："
    echo "     ./scripts/fix-docker-permissions.sh"
    echo ""
    echo "  2. 测试构建："
    echo "     ./scripts/test-docker-build.sh"
    echo ""
    echo "  3. 部署："
    echo "     ./scripts/deploy.sh"
    echo ""
fi

exit $ERRORS
