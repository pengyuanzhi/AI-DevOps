#!/bin/bash
# AI-CICD 生产环境一键部署脚本

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

# 配置
VERSION=${VERSION:-$(git rev-parse --short HEAD 2>/dev/null || echo "latest")}
DEPLOY_ENV=${DEPLOY_ENV:-production}
COMPOSE_FILE="docker-compose.prod.yml"

echo ""
echo "======================================"
echo "  AI-CICD 生产环境部署"
echo "======================================"
echo ""
log_info "版本: $VERSION"
log_info "环境: $DEPLOY_ENV"
echo ""

# 1. 检查环境变量
log_info "检查环境变量..."
if [ ! -f ".env" ]; then
    log_error ".env 文件不存在！"
    log_info "请先创建 .env 文件:"
    echo "  cp .env.example .env"
    echo "  nano .env  # 配置必需的环境变量"
    exit 1
fi

# 检查必需的环境变量
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "RABBITMQ_PASSWORD"
    "ANTHROPIC_API_KEY"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${VAR}=" .env || grep -q "^${VAR}=your_" .env; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_error "缺少或未配置必需的环境变量:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    log_info "请编辑 .env 文件并配置这些变量"
    exit 1
fi

log_success "环境变量检查通过 ✓"

# 2. 检查 Docker
log_info "检查 Docker..."
if ! command -v docker &> /dev/null; then
    log_error "未安装 Docker"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker 服务未运行"
    exit 1
fi

log_success "Docker 检查通过 ✓"

# 3. 构建镜像
log_info "构建 Docker 镜像..."
echo ""

# 构建后端
log_info "构建后端镜像..."
docker compose -f $COMPOSE_FILE build backend

# 构建前端
log_info "构建前端镜像..."
docker compose -f $COMPOSE_FILE build frontend

log_success "镜像构建完成 ✓"

# 4. 停止旧服务
log_info "停止旧服务..."
docker compose -f $COMPOSE_FILE down --remove-orphans

# 5. 启动新服务
log_info "启动新服务..."
docker compose -f $COMPOSE_FILE up -d

# 6. 等待服务就绪
log_info "等待服务启动..."
sleep 10

# 7. 执行数据库迁移
log_info "执行数据库迁移..."
docker compose -f $COMPOSE_FILE exec -T backend alembic upgrade head || \
    log_warning "数据库迁移跳过（可能已执行）"

# 8. 健康检查
log_info "执行健康检查..."
echo ""

# 检查后端
if curl -f http://localhost:8000/health &> /dev/null; then
    log_success "后端服务健康 ✓"
else
    log_warning "后端健康检查失败（可能还在启动中）"
fi

# 检查前端
if curl -f http://localhost/ &> /dev/null; then
    log_success "前端服务健康 ✓"
else
    log_warning "前端健康检查失败（可能还在启动中）"
fi

# 9. 显示服务状态
echo ""
log_info "服务状态:"
docker compose -f $COMPOSE_FILE ps

# 10. 显示访问地址
echo ""
log_success "部署完成！"
echo ""
echo "访问地址:"
echo "  - 前端界面:     http://localhost"
echo "  - API 文档:     http://localhost:8000/docs"
echo "  - RabbitMQ:     http://localhost:15672"
echo ""
echo "查看日志:"
echo "  docker compose -f $COMPOSE_FILE logs -f"
echo ""
echo "停止服务:"
echo "  docker compose -f $COMPOSE_FILE down"
echo ""

# 11. 可选：启用监控
if [ "$ENABLE_MONITORING" = "true" ]; then
    log_info "启动监控服务..."
    docker compose -f $COMPOSE_FILE --profile monitoring up -d
    log_success "监控服务已启动"
    echo ""
    echo "监控地址:"
    echo "  - Prometheus:   http://localhost:9090"
    echo "  - Grafana:      http://localhost:3000 (admin/admin)"
fi
