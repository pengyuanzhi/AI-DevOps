#!/bin/bash
# AI-CICD Platform 快速启动脚本

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

echo ""
echo "======================================"
echo "  AI-CICD Platform 快速启动"
echo "======================================"
echo ""

# 检查.env文件
if [ ! -f .env ]; then
    log_info "创建.env文件..."
    cp .env.example .env
    log_warning "请编辑.env文件配置API密钥"
    ${EDITOR:-vi} .env
fi

# 创建目录
log_info "创建必要的目录..."
mkdir -p data/cache data/generated/tests logs

# 启动服务
log_info "启动Docker服务..."
docker compose up -d --build

# 等待服务健康
log_info "等待服务启动..."
sleep 10

# 执行数据库迁移
log_info "执行数据库迁移..."
docker compose exec -T ai-cicd alembic upgrade head || log_warning "数据库迁移跳过（可能已执行）"

# 显示状态
echo ""
log_info "服务状态："
docker compose ps
echo ""
log_success "启动完成！"
echo ""
echo "访问地址："
echo "  - API文档:    http://localhost:8000/docs"
echo "  - RabbitMQ:   http://localhost:15672"
echo ""
