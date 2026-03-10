#!/bin/bash
#
# AI-CICD Project 清理脚本
# 清理临时文件、缓存、构建产物等不必要的文件
#

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

echo ""
echo "======================================"
echo "  AI-CICD Project 清理脚本"
echo "======================================"
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

log_info "项目目录: $PROJECT_ROOT"
echo ""

# 1. 清理Python缓存
log_info "清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
log_success "Python缓存已清理"

# 2. 清理pytest缓存
log_info "清理pytest缓存..."
rm -rf .pytest_cache
rm -rf frontend/.pytest_cache
log_success "pytest缓存已清理"

# 3. 清理构建产物
log_info "清理构建产物..."
rm -rf frontend/dist
log_success "构建产物已清理"

# 4. 清理运行时数据
log_info "清理运行时数据..."
rm -rf data/cache/*
rm -rf data/generated/*
rm -rf data/*.db
rm -rf data/*.db-journal
rm -rf logs/*.log
log_success "运行时数据已清理"

# 5. 清理临时文件
log_info "清理临时文件..."
find . -type f -name "*.tmp" -delete 2>/dev/null || true
find . -type f -name "*.bak" -delete 2>/dev/null || true
find . -type f -name "*.swp" -delete 2>/dev/null || true
find . -type f -name "*~" -delete 2>/dev/null || true
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
log_success "临时文件已清理"

# 6. 询问是否清理node_modules（根目录）
log_warning "发现根目录node_modules (170MB)"
log_info "根目录的package.json只包含前端依赖，这些依赖应该在frontend/node_modules中"
echo ""
read -p "是否删除根目录的node_modules? [y/N]: " clean_root_node

if [[ $clean_root_node =~ ^[Yy]$ ]]; then
    log_info "删除根目录node_modules..."
    rm -rf node_modules
    rm -f package-lock.json
    log_success "根目录node_modules已删除"
else
    log_info "跳过根目录node_modules清理"
fi

# 7. 询问是否清理文档
log_info "检查项目文档..."
echo ""
log_warning "发现多个会话总结文档，建议整合为一个主文档"
echo "  - SESSION_SUMMARY.md"
echo "  - SESSION_SUMMARY_2026_03_09_PART2.md"
echo "  - SESSION_UPDATE_2026_03_09.md"
echo "  - PROGRESS_REPORT.md"
echo "  - INTEGRATION_TEST_SUMMARY.md"
echo ""
read -p "是否整合会话文档? [y/N]: " clean_docs

if [[ $clean_docs =~ ^[Yy]$ ]]; then
    log_info "整合文档..."
    # 保留最新和最重要的文档
    mkdir -p docs/archive

    # 移动旧文档到archive
    mv SESSION_SUMMARY_2026_03_09_PART2.md docs/archive/ 2>/dev/null || true
    mv SESSION_UPDATE_2026_03_09.md docs/archive/ 2>/dev/null || true
    mv PROGRESS_REPORT.md docs/archive/ 2>/dev/null || true
    mv INTEGRATION_TEST_SUMMARY.md docs/archive/ 2>/dev/null || true
    mv DOCKER_FIX.md docs/archive/ 2>/dev/null || true

    # 保留重要文档在根目录
    log_success "旧文档已移动到 docs/archive/"
    log_info "保留的文档："
    echo "  - API_ENDPOINT_COMPLETION_REPORT.md"
    echo "  - CURRENT_STATUS_ASSESSMENT.md"
    echo "  - DOCKER_STARTUP_GUIDE.md"
    echo "  - FEATURES.md"
    echo "  - README.md"
    echo "  - SESSION_SUMMARY.md (最新)"
else
    log_info "跳过文档整合"
fi

# 8. 清理Docker资源（可选）
echo ""
read -p "是否清理Docker构建缓存? [y/N]: " clean_docker

if [[ $clean_docker =~ ^[Yy]$ ]]; then
    log_info "清理Docker资源..."
    docker system prune -f
    log_success "Docker资源已清理"
else
    log_info "跳过Docker资源清理"
fi

# 统计清理结果
echo ""
log_info "清理结果统计："
echo ""
echo "文件系统使用情况："
df -h . | tail -1
echo ""

# 计算节省的空间
if [ -d ".git" ]; then
    log_info "Git仓库大小："
    du -sh .git 2>/dev/null
fi

if [ -d "frontend/node_modules" ]; then
    log_info "frontend/node_modules 大小："
    du -sh frontend/node_modules 2>/dev/null
fi

echo ""
log_success "清理完成！"
echo ""
echo "建议后续操作："
echo "  1. 检查.gitignore是否配置正确"
echo "  2. 提交更改前查看: git status"
echo "  3. 运行测试确保清理未破坏功能: pytest"
echo ""

  现在项目使用统一的前端技术栈：
  - 前端: Vue 3 + TypeScript + Element Plus + ECharts
  - 后端: FastAPI + PostgreSQL + Redis + RabbitMQ
  - 部署: Docker + Kubernetes (计划中)

  遗留代码已完全清理，项目结构更加清晰！