#!/bin/bash
# AI-CICD 测试环境管理脚本
# 用于启动、停止和管理测试环境

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

# 测试环境配置文件
TEST_COMPOSE_FILE="docker-compose.test.yml"

# 创建测试环境的 docker-compose 配置
create_test_compose() {
    cat > $TEST_COMPOSE_FILE <<'EOF'
version: '3.8'

services:
  # 测试用 PostgreSQL
  postgres-test:
    image: postgres:15-alpine
    container_name: ai-cicd-test-postgres
    environment:
      - POSTGRES_DB=ai_cicd_test
      - POSTGRES_USER=test_user
      - POSTGRES_PASSWORD=test_password
    ports:
      - "5433:5432"
    volumes:
      - test_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - ai-cicd-test-network

  # 测试用 Redis
  redis-test:
    image: redis:7-alpine
    container_name: ai-cicd-test-redis
    command: redis-server --appendonly yes
    ports:
      - "6380:6379"
    volumes:
      - test_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - ai-cicd-test-network

  # 测试用 RabbitMQ
  rabbitmq-test:
    image: rabbitmq:3.12-management-alpine
    container_name: ai-cicd-test-rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=test_user
      - RABBITMQ_DEFAULT_PASS=test_password
    ports:
      - "5673:5672"
      - "15673:15672"
    volumes:
      - test_rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running", "-q"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - ai-cicd-test-network

networks:
  ai-cicd-test-network:
    driver: bridge

volumes:
  test_postgres_data:
  test_redis_data:
  test_rabbitmq_data:
EOF
    log_success "测试环境配置已创建: $TEST_COMPOSE_FILE"
}

# 启动测试环境
start_test_env() {
    log_info "启动测试环境..."

    if [ ! -f "$TEST_COMPOSE_FILE" ]; then
        create_test_compose
    fi

    docker compose -f $TEST_COMPOSE_FILE up -d

    log_info "等待测试环境启动..."
    sleep 5

    # 检查服务健康状态
    log_info "检查服务状态..."
    docker compose -f $TEST_COMPOSE_FILE ps

    # 设置测试环境变量
    export TEST_DATABASE_URL="postgresql+asyncpg://test_user:test_password@localhost:5433/ai_cicd_test"
    export TEST_REDIS_URL="redis://localhost:6380/0"
    export TEST_RABBITMQ_URL="amqp://test_user:test_password@localhost:5673/"

    log_success "测试环境已启动 ✓"
    echo ""
    echo "测试环境连接信息:"
    echo "  - PostgreSQL: localhost:5433 (数据库: ai_cicd_test)"
    echo "  - Redis: localhost:6380"
    echo "  - RabbitMQ: localhost:5673 (管理界面: http://localhost:15673)"
    echo ""
    echo "环境变量已设置:"
    echo "  export TEST_DATABASE_URL=$TEST_DATABASE_URL"
    echo "  export TEST_REDIS_URL=$TEST_REDIS_URL"
    echo "  export TEST_RABBITMQ_URL=$TEST_RABBITMQ_URL"
}

# 停止测试环境
stop_test_env() {
    log_info "停止测试环境..."
    docker compose -f $TEST_COMPOSE_FILE down
    log_success "测试环境已停止 ✓"
}

# 清理测试环境（包括数据）
clean_test_env() {
    log_warning "清理测试环境和所有数据..."
    read -p "确认删除所有测试数据？[y/N]: " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        docker compose -f $TEST_COMPOSE_FILE down -v
        log_success "测试环境已清理 ✓"
    else
        log_info "取消清理"
    fi
}

# 检查测试环境状态
status_test_env() {
    log_info "测试环境状态:"
    echo ""
    if [ -f "$TEST_COMPOSE_FILE" ]; then
        docker compose -f $TEST_COMPOSE_FILE ps
    else
        log_warning "测试环境未初始化"
    fi
}

# 重置测试数据库
reset_test_db() {
    log_info "重置测试数据库..."
    if docker ps | grep -q ai-cicd-test-postgres; then
        docker exec ai-cicd-test-postgres psql -U test_user -d ai_cicd_test -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        log_success "测试数据库已重置 ✓"
    else
        log_error "测试数据库未运行"
    fi
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start     启动测试环境（PostgreSQL, Redis, RabbitMQ）"
    echo "  stop      停止测试环境"
    echo "  restart   重启测试环境"
    echo "  clean     清理测试环境和所有数据"
    echo "  status    查看测试环境状态"
    echo "  reset-db  重置测试数据库"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start              # 启动测试环境"
    echo "  $0 run-tests          # 启动环境并运行测试"
    echo ""
}

# 主逻辑
case "${1:-help}" in
    start)
        start_test_env
        ;;
    stop)
        stop_test_env
        ;;
    restart)
        stop_test_env
        sleep 2
        start_test_env
        ;;
    clean)
        clean_test_env
        ;;
    status)
        status_test_env
        ;;
    reset-db)
        reset_test_db
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
