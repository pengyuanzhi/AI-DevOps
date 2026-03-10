#!/bin/bash
# 前端开发服务器启动脚本
# 用于调试Vue 3前端界面

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}AI-CICD 前端开发服务器${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 进入项目根目录
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo -e "${YELLOW}项目根目录: ${PROJECT_ROOT}${NC}"
echo ""

# 检查Node.js
echo -e "${YELLOW}检查依赖...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 未找到Node.js${NC}"
    echo -e "${YELLOW}请安装Node.js: https://nodejs.org/${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js: $(node --version)${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 未找到npm${NC}"
    exit 1
fi
echo -e "${GREEN}✅ npm: $(npm --version)${NC}"

# 进入前端目录
cd frontend
FRONTEND_DIR=$(pwd)
echo -e "${YELLOW}前端目录: ${FRONTEND_DIR}${NC}"
echo ""

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠️  未找到node_modules，正在安装依赖...${NC}"
    npm install
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    # 检查package.json是否更新
    if [ "package.json" -nt "node_modules" ]; then
        echo -e "${YELLOW}⚠️  检测到package.json更新，重新安装依赖...${NC}"
        npm install
        echo -e "${GREEN}✅ 依赖更新完成${NC}"
    else
        echo -e "${GREEN}✅ 依赖已安装${NC}"
    fi
fi

# 检查Vite配置
if [ ! -f "vite.config.ts" ]; then
    echo -e "${RED}❌ 未找到vite.config.ts${NC}"
    exit 1
fi

# 检查环境变量配置
ENV_FILE=".env.development"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠️  未找到${ENV_FILE}，创建默认配置...${NC}"
    cat > $ENV_FILE << 'ENVEOF'
# 开发环境配置
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_ENABLE_MOCK=false
VITE_LOG_LEVEL=debug
ENVEOF
    echo -e "${GREEN}✅ ${ENV_FILE}已创建${NC}"
fi

# 检查后端是否运行
echo -e "${YELLOW}检查后端服务...${NC}"
BACKEND_URL=$(grep "VITE_API_BASE_URL" $ENV_FILE | cut -d '=' -f2)
BACKEND_HOST=$(echo $BACKEND_URL | sed -E 's|https?://([^/:]+).*|\1|')
BACKEND_PORT=$(echo $BACKEND_URL | sed -E 's|.*:([0-9]+)$|\1|')

if curl -s "http://${BACKEND_HOST}:${BACKEND_PORT}/health" > /dev/null 2>&1 || \
   curl -s "http://${BACKEND_HOST}:${BACKEND_PORT}/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 后端服务运行中 (${BACKEND_URL})${NC}"
else
    echo -e "${YELLOW}⚠️  后端服务未运行或无法访问${NC}"
    echo -e "${YELLOW}请先启动后端: ${GREEN}../scripts/start-backend.sh${NC}"
    echo -e "${YELLOW}或在另一个终端运行: ${GREEN}cd .. && ./scripts/start-backend.sh${NC}"
fi

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}启动前端开发服务器${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 启动选项
PORT="5173"
HOST_ARGS="--host 0.0.0.0"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --local-only)
            HOST_ARGS=""
            shift
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "用法: $0 [--port PORT] [--local-only]"
            exit 1
            ;;
    esac
done

# 显示启动信息
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}前端服务器配置:${NC}"
echo -e "  本地地址: ${BLUE}http://localhost:${PORT}${NC}"
if [ -n "$LOCAL_IP" ]; then
    echo -e "  网络地址: ${BLUE}http://${LOCAL_IP}:${PORT}${NC}"
fi
echo -e "  后端API: ${BLUE}${BACKEND_URL}${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务器${NC}"
echo ""

# 启动Vite开发服务器
exec npm run dev -- --port $PORT $HOST_ARGS
