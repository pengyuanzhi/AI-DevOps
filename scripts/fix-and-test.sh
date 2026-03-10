#!/bin/bash
# Docker 权限修复和测试脚本

echo "=================================="
echo "  Docker 权限修复"
echo "=================================="
echo ""
echo "当前用户: $(whoami)"
echo "当前用户组: $(groups)"
echo ""

# 检查是否已经在 docker 组
if groups | grep -q docker; then
    echo "✓ 用户已在 docker 组中"
    echo ""
    echo "现在可以运行测试了："
    echo "  cd /home/kerfs/AI-CICD-new"
    echo "  ./scripts/test-docker-build.sh"
    exit 0
fi

echo "✗ 用户不在 docker 组中"
echo ""
echo "需要运行以下命令（需要输入 sudo 密码）："
echo ""
echo "  sudo usermod -aG docker \$USER"
echo "  newgrp docker"
echo ""
echo "或者重新登录系统"
echo ""
echo "然后运行测试："
echo "  ./scripts/test-docker-build.sh"
