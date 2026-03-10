#!/bin/bash
# 后端开发服务器启动脚本
# 用于调试FastAPI后端

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}AI-CICD 后端开发服务器${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 进入项目根目录
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo -e "${YELLOW}项目根目录: ${PROJECT_ROOT}${NC}"
echo ""

# 检查Python
echo -e "${YELLOW}检查依赖...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到Python3${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3: $(python3 --version)${NC}"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  未找到虚拟环境，正在创建...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✅ 虚拟环境创建完成${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 安装依赖
echo -e "${YELLOW}检查并安装Python依赖...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✅ Python依赖已安装${NC}"

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到.env文件，创建默认配置...${NC}"
    cat > .env << 'EOF'
# 数据库配置
DATABASE_URL=postgresql+asyncpg://ai_cicd:ai_cicd_password@localhost:5432/ai_cicd

# Redis配置
REDIS_URL=redis://localhost:6379/0

# GitLab配置
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_gitlab_token_here
GITLAB_WEBHOOK_SECRET=your_webhook_secret_here

# LLM配置
ZHIPU_API_KEY=your_zhipu_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# 应用配置
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FORMAT=json
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# 缓存配置
CACHE_TTL=3600
MAX_CACHE_SIZE=1000
EOF
    echo -e "${GREEN}✅ .env文件已创建${NC}"
    echo -e "${YELLOW}⚠️  请编辑.env文件配置必要的环境变量${NC}"
fi

# 检查数据库
echo -e "${YELLOW}检查数据库连接...${NC}"
if ! pg_isready -h localhost -p 5432 &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL未运行${NC}"
    echo -e "${YELLOW}启动PostgreSQL: ${GREEN}sudo systemctl start postgresql${NC}"
    echo -e "${YELLOW}或使用Docker: ${GREEN}docker-compose up -d db${NC}"
else
    echo -e "${GREEN}✅ PostgreSQL运行中${NC}"
fi

# 检查Redis
echo -e "${YELLOW}检查Redis连接...${NC}"
if ! redis-cli ping &> /dev/null; then
    echo -e "${RED}❌ Redis未运行${NC}"
    echo -e "${YELLOW}启动Redis: ${GREEN}sudo systemctl start redis${NC}"
    echo -e "${YELLOW}或使用Docker: ${GREEN}docker-compose up -d redis${NC}"
else
    echo -e "${GREEN}✅ Redis运行中${NC}"
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}启动后端开发服务器${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 启动选项
RELOAD="--reload"
HOST="0.0.0.0"
PORT="8000"
LOG_LEVEL="info"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-reload)
            RELOAD=""
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --debug)
            LOG_LEVEL="debug"
            shift
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "用法: $0 [--no-reload] [--port PORT] [--host HOST] [--debug]"
            exit 1
            ;;
    esac
done

# 显示启动信息
echo -e "${GREEN}后端服务器配置:${NC}"
echo -e "  主机: ${BLUE}http://${HOST}:${PORT}${NC}"
echo -e "  API文档: ${BLUE}http://${HOST}:${PORT}/docs${NC}"
echo -e "  重载: ${BLUE}$( [ -n "$RELOAD" ] && echo "开启" || echo "关闭")${NC}"
echo -e "  日志级别: ${BLUE}${LOG_LEVEL}${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
echo ""

# 启动FastAPI服务器
exec uvicorn src.main:app \
    --host $HOST \
    --port $PORT \
    $RELOAD \
    --log-level $LOG_LEVEL \
    --log-config config/logging.conf 2>/dev/null || \
uvicorn src.main:app \
    --host $HOST \
    --port $PORT \
    $RELOAD \
    --log-level $LOG_LEVEL
