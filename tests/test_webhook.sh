#!/bin/bash
#
# Webhook 端点测试脚本
#
# 使用方法：
#   1. 先启动服务器: python -m src.main
#   2. 然后在另一个终端运行此脚本
#

echo "========================================"
echo "   AI-CICD Webhook 集成测试"
echo "========================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 基础 URL
BASE_URL="http://localhost:8000"
WEBHOOK_SECRET="test_webhook_secret_12345"

# 测试 1: 健康检查
echo -e "${YELLOW}测试 1: 健康检查${NC}"
echo "GET $BASE_URL/health"
echo ""
curl -s "$BASE_URL/health" | python -m json.tool
echo ""
echo ""

# 测试 2: Webhook - MR 打开事件（正确签名）
echo -e "${YELLOW}测试 2: Webhook MR 事件（正确签名）${NC}"
echo "POST $BASE_URL/webhook/gitlab"
echo ""
curl -s -X POST "$BASE_URL/webhook/gitlab" \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -d '{
    "object_kind": "merge_request",
    "event_type": "merge_request",
    "user": {
      "id": 1,
      "name": "Test User",
      "username": "testuser",
      "email": "test@example.com"
    },
    "project": {
      "id": 456,
      "name": "test-project",
      "path_with_namespace": "group/test-project",
      "default_branch": "main",
      "url": "https://gitlab.example.com/group/test-project.git",
      "web_url": "https://gitlab.example.com/group/test-project"
    },
    "object_attributes": {
      "id": 123,
      "iid": 1,
      "title": "Feature: Add user authentication",
      "description": "This MR adds OAuth2 authentication",
      "state": "opened",
      "created_at": "2026-03-08T10:00:00.000Z",
      "updated_at": "2026-03-08T11:00:00.000Z",
      "action": "open",
      "source_branch": "feature/auth",
      "target_branch": "main"
    },
    "changes": {},
    "labels": [],
    "assignees": [],
    "reviewers": []
  }' | python -m json.tool
echo ""
echo ""

# 测试 3: Webhook - Pipeline 事件
echo -e "${YELLOW}测试 3: Webhook Pipeline 事件${NC}"
echo "POST $BASE_URL/webhook/gitlab"
echo ""
curl -s -X POST "$BASE_URL/webhook/gitlab" \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -d '{
    "object_kind": "pipeline",
    "event_type": "pipeline",
    "user": {
      "id": 1,
      "name": "Test User",
      "username": "testuser"
    },
    "project": {
      "id": 456,
      "name": "test-project"
    },
    "object_attributes": {
      "id": 789,
      "name": "pipeline #1234",
      "ref": "main",
      "tag": false,
      "status": "success",
      "source": "merge_request_event",
      "created_at": "2026-03-08T10:00:00.000Z"
    }
  }' | python -m json.tool
echo ""
echo ""

# 测试 4: Webhook - Push 事件
echo -e "${YELLOW}测试 4: Webhook Push 事件${NC}"
echo "POST $BASE_URL/webhook/gitlab"
echo ""
curl -s -X POST "$BASE_URL/webhook/gitlab" \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -d '{
    "object_kind": "push",
    "event_type": "push",
    "user": {
      "id": 1,
      "name": "Test User",
      "username": "testuser"
    },
    "project": {
      "id": 456,
      "name": "test-project"
    },
    "ref": "refs/heads/main",
    "before": "0000000000000000000000000000000000000000",
    "after": "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
    "checkout_sha": "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t",
    "commits": []
  }' | python -m json.tool
echo ""
echo ""

# 测试 5: Webhook - 错误的签名（应该返回 401 或错误）
echo -e "${YELLOW}测试 5: Webhook 错误签名（应失败）${NC}"
echo "POST $BASE_URL/webhook/gitlab"
echo ""
response=$(curl -s -X POST "$BASE_URL/webhook/gitlab" \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: wrong_secret" \
  -d '{"object_kind": "merge_request"}')

echo "$response" | python -m json.tool
echo ""

# 检查是否正确拒绝了错误签名
if echo "$response" | grep -q "error\|Error\|401\|403"; then
    echo -e "${GREEN}✅ 正确拒绝了错误签名${NC}"
else
    echo -e "${RED}❌ 未能正确验证签名${NC}"
fi
echo ""

# 测试 6: Dashboard 统计 API
echo -e "${YELLOW}测试 6: Dashboard 统计 API${NC}"
echo "GET $BASE_URL/api/dashboard/stats"
echo ""
curl -s "$BASE_URL/api/dashboard/stats" | python -m json.tool
echo ""
echo ""

echo "========================================"
echo -e "${GREEN}测试完成！${NC}"
echo "========================================"
echo ""
echo "💡 提示："
echo "   - 如果看到连接错误，请确保服务器正在运行："
echo "     python -m src.main"
echo ""
echo "   - 访问 Dashboard："
echo "     http://localhost:8000/static/index.html"
echo ""
