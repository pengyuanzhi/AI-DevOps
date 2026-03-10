#!/bin/bash
# E2E测试快速启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}AI-CICD E2E 测试快速启动${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"

# 检查Qt6
if ! pkg-config --exists Qt6Core 2>/dev/null; then
    echo -e "${RED}❌ 未找到Qt6${NC}"
    echo "请安装Qt6: sudo apt-get install qt6-base-dev qt6-tools-dev"
    exit 1
fi
echo -e "${GREEN}✅ Qt6 已安装${NC}"

# 检查CMake
if ! command -v cmake &> /dev/null; then
    echo -e "${RED}❌ 未找到CMake${NC}"
    echo "请安装CMake: sudo apt-get install cmake"
    exit 1
fi
echo -e "${GREEN}✅ CMake 已安装$(cmake --version | head -1)${NC}"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到Python3${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 已安装$(python3 --version)${NC}"

# 检查编译器
if ! command -v g++ &> /dev/null; then
    echo -e "${RED}❌ 未找到g++编译器${NC}"
    echo "请安装build-essential: sudo apt-get install build-essential"
    exit 1
fi
echo -e "${GREEN}✅ g++ 编译器已安装${NC}"

echo ""

# 进入测试目录
cd "$(dirname "$0")"

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(realpath ../..)"

# 运行测试
echo -e "${YELLOW}运行E2E测试...${NC}"
echo ""

python3 run_e2e_tests.py "$@"

exit $?
