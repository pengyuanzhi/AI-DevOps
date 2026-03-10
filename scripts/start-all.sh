#!/bin/bash
# 同时启动前后端开发服务器
# 用于完整的前后端调试

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}AI-CICD 前后端开发服务器${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 进入项目根目录
cd "$(dirname "$0")/.."

# 检查tmux
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}❌ 未找到tmux${NC}"
    echo -e "${YELLOW}请安装tmux: ${GREEN}sudo apt-get install tmux${NC}"
    echo ""
    echo -e "${YELLOW}或者手动在两个终端中分别运行:${NC}"
    echo -e "  终端1: ${GREEN}./scripts/start-backend.sh${NC}"
    echo -e "  终端2: ${GREEN}./scripts/start-frontend.sh${NC}"
    exit 1
fi

SESSION_NAME="ai-cicd-dev"

# 检查会话是否已存在
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo -e "${YELLOW}⚠️  开发会话已存在${NC}"
    echo -e "${YELLOW}附加到会话: ${GREEN}tmux attach -t $SESSION_NAME${NC}"
    echo -e "${YELLOW}或关闭会话: ${GREEN}tmux kill-session -t $SESSION_NAME${NC}"
    exec tmux attach-session -t $SESSION_NAME
fi

echo -e "${GREEN}创建tmux开发会话: ${SESSION_NAME}${NC}"
echo ""

# 创建新会话并启动后端
tmux new-session -d -s $SESSION_NAME -n "Backend"

# 在后端窗口中启动后端服务
tmux send-keys -t $SESSION_NAME:0 "cd $(pwd)" C-m
tmux send-keys -t $SESSION_NAME:0 "./scripts/start-backend.sh" C-m

# 等待后端启动
echo -e "${YELLOW}等待后端服务启动...${NC}"
sleep 3

# 创建前端窗口并启动前端
tmux new-window -t $SESSION_NAME -n "Frontend"
tmux send-keys -t $SESSION_NAME:1 "cd $(pwd)" C-m
tmux send-keys -t $SESSION_NAME:1 "./scripts/start-frontend.sh" C-m

# 选择后端窗口
tmux select-window -t $SESSION_NAME:0

echo ""
echo -e "${GREEN}✅ 开发会话已创建！${NC}"
echo ""
echo -e "${BLUE}tmux 会话操作:${NC}"
echo -e "  ${GREEN}Ctrl+B c${NC} - 创建新窗口"
echo -e "  ${GREEN}Ctrl+B n${NC} - 切换到下一个窗口"
echo -e "  ${GREEN}Ctrl+B p${NC} - 切换到上一个窗口"
echo -e "  ${GREEN}Ctrl+B 0${NC} - 切换到后端窗口"
echo -e "  ${GREEN}Ctrl+B 1${NC} - 切换到前端窗口"
echo -e "  ${GREEN}Ctrl+B d${NC} - 分离会话（服务器继续运行）"
echo ""
echo -e "${YELLOW}重新附加到会话:${NC} ${GREEN}tmux attach -t $SESSION_NAME${NC}"
echo -e "${YELLOW}关闭会话:${NC} ${GREEN}tmux kill-session -t $SESSION_NAME${NC}"
echo ""

# 附加到会话
exec tmux attach-session -t $SESSION_NAME
