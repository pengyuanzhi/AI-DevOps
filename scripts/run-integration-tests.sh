#!/bin/bash
# 集成测试运行脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}AI-CICD 集成测试执行${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 进入项目根目录
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# 创建报告目录
REPORT_DIR="$PROJECT_ROOT/tests/reports"
mkdir -p "$REPORT_DIR"

echo -e "${YELLOW}项目根目录: ${PROJECT_ROOT}${NC}"
echo -e "${YELLOW}报告目录: ${REPORT_DIR}${NC}"
echo ""

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}❌ pytest未安装${NC}"
    echo -e "${YELLOW}请安装: pip install pytest pytest-asyncio pytest-cov${NC}"
    exit 1
fi
echo -e "${GREEN}✅ pytest已安装${NC}"
echo ""

# 解析命令行参数
TEST_TYPE="${1:-quick}"
RUN_SLOW="${RUN_SLOW:-false}"

# 显示菜单
if [ "$TEST_TYPE" = "--help" ] || [ "$TEST_TYPE" = "-h" ]; then
    echo "用法: $0 [test_type]"
    echo ""
    echo "测试类型:"
    echo "  quick      - 快速测试（无外部依赖，默认）"
    echo "  integration - 完整集成测试（需要数据库）"
    echo "  all        - 运行所有测试"
    echo "  coverage   - 运行测试并生成覆盖率报告"
    echo "  unit       - 只运行单元测试"
    echo "  e2e        - 只运行E2E测试"
    echo ""
    echo "环境变量:"
    echo "  RUN_SLOW=true  - 包含慢速测试"
    echo ""
    exit 0
fi

# 执行测试
case $TEST_TYPE in
    quick)
        echo -e "${BLUE}运行快速集成测试...${NC}"
        echo ""
        pytest tests/integration/ \
            -m "not slow" \
            -v \
            --tb=short \
            --html="$REPORT_DIR/integration_quick_report.html" \
            --self-contained-html
        ;;

    integration)
        echo -e "${BLUE}运行完整集成测试...${NC}"
        echo ""
        pytest tests/integration/ \
            -v \
            --tb=short \
            --html="$REPORT_DIR/integration_full_report.html" \
            --self-contained-html
        ;;

    all)
        echo -e "${BLUE}运行所有测试...${NC}"
        echo ""
        pytest tests/ \
            -v \
            --tb=short \
            --html="$REPORT_DIR/all_tests_report.html" \
            --self-contained-html
        ;;

    coverage)
        echo -e "${BLUE}运行测试并生成覆盖率报告...${NC}"
        echo ""
        pytest tests/integration/ \
            -m "not slow" \
            --cov=src \
            --cov-report=html:"$REPORT_DIR/coverage_html" \
            --cov-report=term \
            --cov-report=html \
            -v
        echo ""
        echo -e "${GREEN}✅ 覆盖率报告已生成: ${REPORT_DIR}/coverage_html/index.html${NC}"
        ;;

    unit)
        echo -e "${BLUE}运行单元测试...${NC}"
        echo ""
        pytest tests/unit/ \
            -v \
            --tb=short \
            --html="$REPORT_DIR/unit_tests_report.html" \
            --self-contained-html
        ;;

    e2e)
        echo -e "${BLUE}运行E2E测试...${NC}"
        echo ""
        python tests/e2e/demo_e2e.py
        ;;

    *)
        echo -e "${RED}❌ 未知的测试类型: $TEST_TYPE${NC}"
        echo ""
        echo "运行 '$0 --help' 查看帮助"
        exit 1
        ;;
esac

# 检查测试结果
TEST_RESULT=$?
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}✅ 测试通过！${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "${BLUE}报告位置:${NC}"
    echo -e "  ${REPORT_DIR}/"
    echo ""
else
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}❌ 测试失败！${NC}"
    echo -e "${RED}============================================${NC}"
    echo ""
    echo -e "${YELLOW}请检查上方输出查看详细错误信息${NC}"
    echo ""
fi

exit $TEST_RESULT
