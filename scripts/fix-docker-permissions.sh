#!/bin/bash
# Docker 权限修复脚本

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

echo ""
echo "======================================"
echo "  Docker 权限修复"
echo "======================================"
echo ""

# 检查当前用户
CURRENT_USER=$(whoami)
log_info "当前用户: $CURRENT_USER"

# 检查 docker 组
if groups | grep -q docker; then
    log_success "用户已在 docker 组中"
    log_info "但可能需要重新登录或运行: newgrp docker"
    echo ""
    log_info "尝试运行: newgrp docker"
    echo "  或者重新登录系统"
    exit 0
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

# 检查 docker.sock 是否存在
if [ ! -S /var/run/docker.sock ]; then
    log_error "Docker daemon 未运行"
    log_info "启动方法:"
    echo "  WSL2: 启动 Docker Desktop"
    echo "  Linux: sudo systemctl start docker"
    exit 1
fi

# 添加用户到 docker 组
log_warning "用户不在 docker 组中"
echo ""
log_info "将用户添加到 docker 组需要 sudo 权限"
echo ""

read -p "是否继续？[y/N]: " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    log_info "取消操作"
    exit 0
fi

# 添加用户到 docker 组
log_info "添加用户 $CURRENT_USER 到 docker 组..."
if sudo usermod -aG docker "$CURRENT_USER"; then
    log_success "用户已添加到 docker 组 ✓"
    echo ""
    log_warning "重要：需要执行以下操作之一使更改生效："
    echo ""
    echo "  方式1（临时生效）："
    echo "    newgrp docker"
    echo ""
    echo "  方式2（永久生效）："
    echo "    重新登录系统或重启"
    echo ""
    echo "然后运行："
    echo "    ./scripts/test-docker-build.sh"
    echo ""
else
    log_error "添加用户到 docker 组失败"
    exit 1
fi
