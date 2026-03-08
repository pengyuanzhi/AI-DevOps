# 集成测试指南

## 📋 概述

本目录包含 AI-CICD 项目的集成测试和手动测试脚本。

## 🧪 自动化集成测试

### 运行所有集成测试

```bash
# 从项目根目录运行
python -m pytest tests/integration/ -v

# 运行特定测试类
python -m pytest tests/integration/test_gitlab_integration.py::TestGitLabClientIntegration -v

# 运行单个测试
python -m pytest tests/integration/test_gitlab_integration.py::TestGitLabClientIntegration::test_full_mr_workflow -v -s
```

### 集成测试覆盖

✅ **GitLab 客户端集成**
- 完整的 MR 工作流测试
- 获取 MR 详情、diff、文件内容

✅ **MR 操作集成**
- Python 文件过滤
- 发布审查评论

✅ **文件操作集成**
- 批量获取文件

✅ **Webhook 集成**
- Webhook 事件处理
- 签名验证

✅ **端到端工作流**
- 完整的 MR 处理流程

### 测试结果

```
tests/integration/test_gitlab_integration.py::TestGitLabClientIntegration::test_full_mr_workflow PASSED
tests/integration/test_gitlab_integration.py::TestMROperationsIntegration::test_get_python_files_from_mr PASSED
tests/integration/test_gitlab_integration.py::TestMROperationsIntegration::test_post_review_comment PASSED
tests/integration/test_gitlab_integration.py::TestFileOperationsIntegration::test_batch_get_multiple_files PASSED
tests/integration/test_gitlab_integration.py::TestWebhookIntegration::test_webhook_mr_event PASSED
tests/integration/test_gitlab_integration.py::TestEndToEndWorkflow::test_full_mr_processing_workflow PASSED

========================= 6 passed, 2 skipped =========================
```

---

## 🖥️ 手动测试

### 方式 1: 使用自动化测试脚本

我们提供了一个自动化测试脚本，可以启动服务器并测试所有端点：

```bash
# 运行手动测试脚本
cd /home/kerfs/AI-CICD-new
python tests/manual_test_webhook.py
```

这个脚本会：
1. 启动测试服务器（端口 8765）
2. 测试健康检查端点
3. 测试 Webhook 端点（各种签名场景）
4. 测试 Dashboard API
5. 保持服务器运行以便手动测试

### 方式 2: 手动启动服务器

```bash
# 1. 启动服务器
cd /home/kerfs/AI-CICD-new
python -m src.main

# 服务器将在 http://localhost:8000 启动
```

#### 测试健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy",
    "gitlab": "healthy",
    "llm": "healthy"
  },
  "timestamp": "2026-03-08T10:00:00.000Z"
}
```

#### 测试 Webhook 端点

```bash
# 发送测试 Webhook 事件
curl -X POST http://localhost:8000/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: test_webhook_secret_12345" \
  -d '{
    "object_kind": "merge_request",
    "event_type": "merge_request",
    "user": {
      "id": 1,
      "name": "Test User",
      "username": "testuser"
    },
    "project": {
      "id": 456,
      "name": "test-project",
      "path_with_namespace": "group/test-project"
    },
    "object_attributes": {
      "action": "open",
      "iid": 1,
      "title": "Test MR",
      "source_branch": "feature",
      "target_branch": "main"
    }
  }'
```

预期响应：
```json
{
  "status": "queued",
  "message": "MR 'Test MR' 已加入处理队列（0 个 Python 文件）",
  "event_type": "merge_request"
}
```

#### 测试 Dashboard

访问 Dashboard 页面：
```
http://localhost:8000/static/index.html
```

测试 Dashboard API：
```bash
# 获取统计数据
curl http://localhost:8000/api/dashboard/stats

# 获取趋势数据
curl http://localhost:8000/api/dashboard/trends?hours=24
```

---

## 🔧 真实 GitLab 连接测试

如果您有真实的 GitLab token，可以运行真实连接测试：

### 1. 配置环境变量

编辑 `.env` 文件：
```bash
GITLAB_URL=https://gitlab.com  # 或您的 GitLab 实例 URL
GITLAB_TOKEN=your_real_token_here
GITLAB_WEBHOOK_SECRET=your_webhook_secret
```

### 2. 运行真实连接测试

```bash
# 只运行集成标记的测试
python -m pytest tests/integration/test_gitlab_integration.py::TestRealGitLabConnection -v -s
```

⚠️ **注意**：
- 这些测试默认被跳过
- 需要真实的 GitLab token
- 需要真实的项目 ID（在代码中配置）

---

## 📊 测试覆盖率

当前测试覆盖率：

- **单元测试**: 10/10 通过 ✅
- **集成测试**: 6/6 通过 ✅

### 未覆盖的测试

以下功能需要真实 GitLab 环境才能测试：

- 真实 GitLab API 调用
- 真实 MR 评论发布
- 真实文件创建/更新

---

## 🐛 调试测试

### 查看详细日志

测试运行时查看详细输出：
```bash
python -m pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

### 查看服务器日志

手动测试时，服务器会输出详细日志到控制台：
```
2026-03-08 10:00:00 [info] webhook_event_received object_kind=merge_request
2026-03-08 10:00:00 [info] fetching_mr_details project_id=456 mr_iid=1
```

---

## 📝 测试最佳实践

1. **使用 Mock 数据**: 集成测试默认使用 Mock，不需要真实 GitLab
2. **测试隔离**: 每个测试独立运行，不依赖其他测试
3. **快速反馈**: 集成测试应该在几秒内完成
4. **清晰输出**: 使用 `-s` 参数查看 print 输出

---

## 🚀 下一步

测试通过后，可以：

1. **继续 Phase 3**: 开始实施测试生成功能
2. **真实集成**: 配置真实 GitLab token 进行端到端测试
3. **CI/CD 集成**: 将测试集成到 CI/CD 流程

---

## 💡 常见问题

### Q: 测试失败怎么办？

A:
1. 检查依赖是否安装完整：`pip install -r requirements.txt`
2. 检查 `.env` 文件配置
3. 查看详细日志：`pytest -v -s`

### Q: 如何添加新的集成测试？

A:
1. 在 `tests/integration/` 目录创建测试文件
2. 使用 `@pytest.mark.asyncio` 标记异步测试
3. 使用 Mock 模拟外部依赖

### Q: 真实 GitLab 测试会修改数据吗？

A:
- 不会。真实连接测试默认被跳过
- 即使运行，也只是读取数据（GET 请求）
- 不会创建 MR、评论或修改文件
