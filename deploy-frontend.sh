#!/bin/bash
#
# AI-CICD 前端部署脚本
# 用于构建和部署前端Docker容器
#

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "========================================"
echo "  AI-CICD 前端部署脚本"
echo "========================================"
echo ""

log_info "项目目录: $PROJECT_ROOT"
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    log_error "Docker未运行，请先启动Docker"
    exit 1
fi

# 检查端口80是否被占用
if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口80已被占用"
    echo ""
    read -p "是否继续部署? (y/N): " continue_deploy
    if [[ ! $continue_deploy =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 0
    fi
fi

# 停止并删除旧容器
log_info "停止旧容器..."
docker-compose stop frontend 2>/dev/null || true
docker-compose rm -f frontend 2>/dev/null || true

# 构建前端镜像
log_info "构建前端Docker镜像..."
docker-compose build frontend

if [ $? -eq 0 ]; then
    log_success "前端镜像构建成功"
else
    log_error "前端镜像构建失败"
    exit 1
fi

# 启动前端容器
log_info "启动前端容器..."
docker-compose up -d frontend

if [ $? -eq 0 ]; then
    log_success "前端容器启动成功"
else
    log_error "前端容器启动失败"
    exit 1
fi

# 等待容器健康检查
log_info "等待容器启动..."
sleep 5

# 检查容器状态
log_info "检查容器状态..."
docker-compose ps frontend

# 查看日志
echo ""
log_info "前端容器日志（最近20行）:"
docker-compose logs --tail=20 frontend

# 显示访问地址
echo ""
log_success "========================================="
log_success "前端部署完成！"
log_success "========================================="
echo ""
echo -e "${GREEN}前端地址:${NC}  http://localhost"
echo -e "${GREEN}API文档:${NC}   http://localhost:8000/docs"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f frontend"
echo "  停止服务: docker-compose stop frontend"
echo "  重启服务: docker-compose restart frontend"
echo "  查看状态: docker-compose ps"
echo ""

# 健康检查
log_info "执行健康检查..."
sleep 2
if curl -f -s http://localhost/health > /dev/null 2>&1; then
    log_success "前端服务健康检查通过 ✓"
else
    log_warning "前端服务健康检查失败，请检查日志"
fi

echo ""
