# 集成测试架构设计

**设计日期**: 2026-03-10
**测试范围**: AI-CICD核心功能集成测试
**测试框架**: pytest + asyncio + pytest-asyncio

---

## 📋 测试范围

### 1. 测试调度器集成测试
**目标**: 验证TestScheduler与数据库、Celery的集成

**测试场景**:
- ✅ 提交测试任务到Celery
- ✅ 更新测试状态到数据库
- ✅ 查询测试状态
- ✅ 取消测试任务
- ✅ 批量提交测试
- ✅ 获取测试统计信息

**依赖**:
- 数据库 (PostgreSQL测试实例)
- Celery (测试worker)

---

### 2. WebSocket实时通信集成测试
**目标**: 验证WebSocket日志流和实时更新

**测试场景**:
- ✅ WebSocket连接和断开
- ✅ 主题订阅和取消订阅
- ✅ 构建日志实时推送
- ✅ 测试结果实时推送
- ✅ 状态更新广播
- ✅ 进度更新推送
- ✅ 多客户端并发

**依赖**:
- WebSocket服务器
- 测试客户端

---

### 3. 构建→测试完整流程集成测试
**目标**: 验证从构建到测试的完整CI/CD流程

**测试场景**:
- ✅ 提交构建任务
- ✅ 构建完成后自动触发测试
- ✅ 测试执行并收集结果
- ✅ 状态更新和日志流
- ✅ 失败场景处理
- ✅ 缓存功能验证

**依赖**:
- BuildScheduler + TestScheduler
- Celery workers
- WebSocket
- 数据库

---

### 4. 智能测试选择集成测试
**目标**: 验证测试选择服务的端到端功能

**测试场景**:
- ✅ Git变更分析
- ✅ 依赖关系图构建
- ✅ 影响域分析
- ✅ 测试选择决策
- ✅ 反馈学习

**依赖**:
- Git仓库 (测试仓库)
- 测试发现服务
- 依赖关系分析

---

### 5. 失败分类和修复集成测试
**目标**: 验证失败诊断和自动修复流程

**测试场景**:
- ✅ 失败分类准确率
- ✅ 根因分析
- ✅ 修复建议生成
- ✅ 自动修复执行
- ✅ MR自动化

**依赖**:
- 失败分类器
- 根因分析器
- 修复生成器
- GitLab API (mock)

---

## 🏗️ 测试架构

### 目录结构

```
tests/integration/
├── conftest.py                 # pytest配置和fixtures
├── test_scheduler_integration.py    # 测试调度器集成测试
├── test_websocket_integration.py    # WebSocket集成测试
├── test_build_test_pipeline.py      # 构建→测试流程测试
├── test_smart_selection.py          # 智能测试选择测试
├── test_pipeline_maintenance.py     # 失败诊断测试
└── fixtures/                   # 测试数据和fixtures
    ├── test_projects/         # 测试项目
    ├── logs/                  # 模拟日志
    └── git_repos/             # 测试Git仓库
```

### 测试配置

**pytest.ini**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    integration: 集成测试
    slow: 慢速测试（需要数据库/Celery）
    requires_celery: 需要Celery worker
    requires_db: 需要数据库
```

---

## 🔧 Fixtures和工具

### 共享Fixtures

**数据库**:
- `db_session` - 测试数据库会话
- `clean_db` - 清空数据库的fixture

**Celery**:
- `celery_app` - Celery应用实例
- `celery_worker` - 启动的测试worker

**项目数据**:
- `test_project` - 创建测试项目
- `test_pipeline` - 创建测试流水线
- `test_job` - 创建测试作业

**WebSocket**:
- `websocket_client` - WebSocket测试客户端
- `ws_manager` - WebSocket管理器

---

## 📝 测试执行策略

### 本地开发测试

**快速测试** (无外部依赖):
```bash
pytest tests/integration/ -m "not slow" -v
```

**完整集成测试** (需要数据库和Celery):
```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行测试
pytest tests/integration/ -v

# 清理
docker-compose -f docker-compose.test.yml down
```

### CI/CD管道测试

**阶段1: 单元测试**
```bash
pytest tests/unit/ -v --cov=src
```

**阶段2: 集成测试**
```bash
pytest tests/integration/ -v -m "not slow"
```

**阶段3: 端到端测试**
```bash
pytest tests/e2e/ -v
```

---

## 🎯 成功标准

### 覆盖率目标

| 模块 | 单元测试覆盖率 | 集成测试覆盖率 |
|------|---------------|---------------|
| TestScheduler | 90%+ | 80%+ |
| WebSocket | 85%+ | 75%+ |
| Build→Test流程 | 70%+ | 70%+ |
| 智能测试选择 | 80%+ | 60%+ |
| 失败诊断 | 85%+ | 65%+ |

### 质量目标

- ✅ 所有集成测试通过
- ✅ 无Flaky测试（不稳定的测试）
- ✅ 测试执行时间 < 5分钟
- ✅ 0个已知的bug

---

## 📊 测试报告

### 自动生成

**HTML报告**:
```bash
pytest tests/integration/ --html=reports/integration_report.html
```

**覆盖率报告**:
```bash
pytest tests/integration/ --cov=src --cov-report=html --cov-report=term
```

**JUnit XML** (CI集成):
```bash
pytest tests/integration/ --junitxml=reports/junit.xml
```

---

## 🐛 已知问题和限制

### 当前限制

1. **Celery测试**:
   - 需要真实Redis和RabbitMQ
   - 测试时间较长
   - 可能需要mock外部服务

2. **WebSocket测试**:
   - 并发测试可能不稳定
   - 需要清理连接状态

3. **Git操作**:
   - 测试仓库需要隔离
   - 需要清理临时文件

### 缓解措施

- 使用pytest-xdist并行运行测试
- 使用mock减少外部依赖
- 实现测试数据清理机制

---

## 🚀 实施计划

### 阶段1: 基础设施 (1天)
- [x] 创建测试目录结构
- [ ] 实现conftest.py和fixtures
- [ ] 配置pytest

### 阶段2: 测试调度器集成测试 (1天)
- [ ] test_scheduler_integration.py
- [ ] 数据库集成验证
- [ ] Celery任务验证

### 阶段3: WebSocket集成测试 (1天)
- [ ] test_websocket_integration.py
- [ ] 日志流验证
- [ ] 多客户端测试

### 阶段4: 流程集成测试 (2天)
- [ ] test_build_test_pipeline.py
- [ ] test_smart_selection.py
- [ ] test_pipeline_maintenance.py

### 阶段5: 执行和优化 (1天)
- [ ] 运行所有测试
- [ ] 修复Flaky测试
- [ ] 性能优化
- [ ] 生成测试报告

**总计**: 6天

---

**创建时间**: 2026-03-10
**维护者**: AI-CICD Team
