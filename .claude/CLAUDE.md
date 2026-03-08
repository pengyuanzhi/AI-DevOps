# Claude AI 项目指南

## 项目概述

**项目名称**: AI驱动CI/CD平台
**目标用户**: 中型团队（20-200人）
**核心领域**: C/C++和Qt项目的自托管AI驱动CI/CD平台
**当前版本**: v2.9 (模块化单体) → v3.5+ (服务网格演进)

### 核心价值

- **CI/CD自动化**: 支持C/C++自动化构建、自动化测试、自动化部署
- **智能化**: AI驱动的自主决策与维护
- **质量保障**: 静态代码审查 + 内存安全检测
- **效率提升**: 智能测试选择，缩短80%以上测试反馈时间
- **资源优化**: Kubernetes智能调度与自动扩缩容
- **易用性**: 自然语言生成CI/CD配置

---

## 技术栈

### 后端
- **框架**: FastAPI 0.115+, Uvicorn 0.32+
- **ORM**: SQLAlchemy 2.0+
- **数据验证**: Pydantic 2.10+
- **任务队列**: Celery 5.3+ + RabbitMQ 3.12+
- **数据库**: PostgreSQL 15+, Redis 7.0+
- **日志**: Structlog 24.4+

### 前端
- **框架**: Vue 3.4+
- **语言**: TypeScript 5.3+
- **构建工具**: Vite 5.0+
- **UI组件**: Element Plus 2.5+
- **图表**: ECharts 5.5+

### DevOps
- **容器编排**: Kubernetes 1.24+
- **监控**: Prometheus + Grafana
- **追踪**: OpenTelemetry + Jaeger

### C/C++工具
- **构建**: CMake, QMake, Make, Ninja
- **静态分析**: Clang-Tidy, Cppcheck
- **内存检测**: Valgrind
- **测试**: Qt Test

---

## 项目结构

```
AI-CICD-new/
├── src/                          # 源代码目录
│   ├── main.py                   # FastAPI应用入口
│   ├── api/                      # API层
│   │   ├── routes/               # 路由（webhooks, dashboard, cicd）
│   │   └── middleware/           # 中间件（auth）
│   ├── core/                     # 核心业务逻辑
│   │   ├── llm/                  # LLM客户端（Claude, 智谱AI, OpenAI）
│   │   ├── analyzers/            # 代码分析器
│   │   │   └── cpp/              # C++分析器
│   │   ├── quality/              # 质量检查
│   │   │   └── cpp/              # C++静态分析（Clang-Tidy, Cppcheck）
│   │   └── config/               # 配置生成器
│   ├── integrations/             # 第三方集成
│   │   └── gitlab/               # GitLab集成（client, mr_operations）
│   ├── models/                   # 数据模型
│   ├── services/                 # 服务层
│   └── utils/                    # 工具类
│       ├── config.py             # 配置管理
│       └── logger.py             # 日志配置
├── frontend/                     # Vue 3前端（待创建）
├── tests/                        # 测试目录
│   ├── unit/                     # 单元测试
│   └── integration/              # 集成测试
├── docs/                         # 文档目录
│   ├── REQUIREMENTS.md           # 需求文档 (v2.9)
│   ├── ARCHITECTURE.md           # 技术架构设计 (v1.0)
│   └── IMPLEMENTATION_PLAN.md    # 实施计划与里程碑 (v1.0)
├── configs/                      # 配置文件目录
├── data/                         # 数据存储目录
├── static/                       # 静态资源（CSS、JS）
├── docker-compose.yml            # Docker Compose配置
├── Dockerfile                    # Docker镜像
├── requirements.txt              # Python依赖
└── .env.example                  # 环境变量模板
```

---

## 关键文档位置

### 核心文档（必读）
1. **需求文档**: `/home/kerfs/AI-CICD-new/docs/REQUIREMENTS.md`
   - 6大AI核心功能详细需求
   - 7个Dashboard模块设计
   - 性能要求和验收标准

2. **架构设计**: `/home/kerfs/AI-CICD-new/docs/ARCHITECTURE.md`
   - 系统分层架构
   - 技术栈选型理由
   - 微服务演进策略
   - 数据库设计
   - API设计
   - 安全设计
   - 可观测性设计

3. **实施计划**: `/home/kerfs/AI-CICD-new/docs/IMPLEMENTATION_PLAN.md`
   - 6个阶段的详细任务分解
   - 里程碑时间线（T-2周 → T+34周）
   - 技术债务管理策略
   - 风险管控矩阵
   - 质量保障计划

### 关键实现文件
- `/home/kerfs/AI-CICD-new/src/main.py` - 应用入口
- `/home/kerfs/AI-CICD-new/src/utils/config.py` - 配置管理
- `/home/kerfs/AI-CICD-new/src/core/llm/factory.py` - LLM客户端工厂
- `/home/kerfs/AI-CICD-new/src/integrations/gitlab/mr_operations.py` - GitLab MR操作

---

## 6大AI核心功能

### 1. 智能测试选择
- **目标**: 典型PR的测试时间减少≥80%
- **核心算法**: Git diff解析 + 依赖图构建 + 影响域分析（BFS遍历）
- **性能要求**: 依赖图构建时间<30秒，测试选择决策时间<10秒

### 2. AI增强静态代码审查
- **工具集成**: Clang-Tidy + Cppcheck
- **AI价值**: 误报过滤、上下文理解、质量评分（5维度）
- **性能要求**: 误报率≤10%，审查时间<2分钟（1000行代码）

### 3. 自然语言配置
- **功能**: 自然语言 → GitLab CI YAML
- **性能要求**: 80%常见场景可生成正确配置，配置时间减少≥80%

### 4. 自主流水线维护
- **功能**: 失败检测 → AI根因分析 → 自动修复
- **性能要求**: 自动修复率≥90%，误报减少≥70%

### 5. 智能资源优化
- **功能**: Kubernetes智能Pod调度 + HPA/VPA自动扩缩容
- **性能要求**: 资源利用率提升≥20%，Pod调度延迟<5秒

### 6. 内存安全检测
- **工具**: Valgrind Memcheck
- **AI价值**: 误报过滤、根因分析、智能修复建议
- **性能要求**: 检测率≥90%，误报率≤15%

---

## 开发规范

### 代码风格
- **Python**: 遵循PEP 8，使用Black格式化，isort排序导入
- **TypeScript**: 遵循ESLint配置，使用Prettier格式化
- **C++**: 遵循Google C++ Style Guide

### Git提交规范
```
<type>(<scope>): <subject>

<body>

<footer>
```

**type类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

### 分支策略
- `main`: 主分支，生产环境代码
- `develop`: 开发分支
- `feature/*`: 功能分支
- `bugfix/*`: Bug修复分支
- `hotfix/*`: 紧急修复分支

---

## 常用命令

### 开发环境启动
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 启动开发服务器
python -m src.main

# 或使用Docker Compose
docker-compose up -d
```

### 测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 代码质量检查
```bash
# 代码格式化
black src/
isort src/

# 类型检查
mypy src/

# Lint检查
flake8 src/
pylint src/
```

### Docker操作
```bash
# 构建镜像
docker build -t ai-cicd:latest .

# 运行容器
docker run -d \
  --name ai-cicd \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  ai-cicd:latest

# 查看日志
docker logs -f ai-cicd
```

---

## 环境变量配置

### 必需配置
```bash
# LLM API（至少配置一个）
ANTHROPIC_API_KEY=your_claude_api_key
ZHIPU_API_KEY=your_zhipu_api_key
OPENAI_API_KEY=your_openai_api_key

# GitLab
GITLAB_TOKEN=your_gitlab_token
GITLAB_WEBHOOK_SECRET=your_webhook_secret

# 数据库（生产环境）
DATABASE_URL=postgresql://user:password@localhost:5432/ai_cicd
REDIS_URL=redis://localhost:6379/0

# 消息队列
RABBITMQ_URL=amqp://user:password@localhost:5672/
```

### 可选配置
```bash
# C++分析工具
ENABLE_CPP_REVIEW=true
CLANG_TIDY_CHECKS=-*
CLANG_TIDY_CHECKS+=modernize*
CPPCHECK_ENABLE=all

# 性能优化
ENABLE_CCACHE=true
CCACHE_DIR=/path/to/ccache

# 日志级别
LOG_LEVEL=INFO
```

---

## 重要注意事项

### 1. 数据隐私
- 支持完全离线模式（本地LLM）
- 用户自备API密钥
- 数据存储在用户控制的Kubernetes集群

### 2. 技术债务
当前需要偿还的高优先级技术债务：
- SQLite → PostgreSQL迁移（阶段0）
- 同步调用 → 异步任务队列（阶段0）
- 正则表达式C++解析器 → Tree-sitter（阶段3）

### 3. 性能目标
- 测试时间减少：≥80%
- 构建时间减少：≥15%
- 资源利用率提升：≥20%
- 系统可用性：≥99.5%

### 4. 架构演进
- **v2.9**: 模块化单体（当前）
- **v3.1**: 微服务拆分
- **v3.5+**: 服务网格

### 5. 依赖关系
**关键路径**:
- 构建执行引擎 → 测试执行 → 智能测试选择
- 前端框架 → 各Dashboard模块

### 6. 风险缓解
- **AI效果不达预期**: 准备降级方案（回退到纯静态分析）
- **构建环境复杂度高**: 先支持标准C++项目，再扩展到Qt项目
- **前端开发进度滞后**: 优先实现核心Dashboard

---

## 测试策略

### 单元测试
- 目标覆盖率：≥80%（核心模块≥90%）
- 工具：pytest + pytest-cov
- 重点：LLM客户端、GitLab集成、代码分析器

### 集成测试
- 目标覆盖率：≥70%
- 工具：pytest + pytest-asyncio
- 重点：Webhook处理、CI/CD流水线、Dashboard API

### E2E测试
- 目标覆盖率：≥50%（关键用户路径）
- 工具：Playwright（前端）
- 重点：MR创建 → 测试生成 → 代码审查 → 反馈

---

## 监控和日志

### 结构化日志
使用Structlog，所有日志包含：
- `timestamp`: 时间戳
- `level`: 日志级别
- `logger`: 日志来源
- `message`: 日志消息
- `trace_id`: 追踪ID（分布式追踪）
- `context`: 上下文信息

### 关键指标
- Pipeline计数和耗时
- AI请求计数和延迟
- 资源使用率（CPU、内存）
- 构建和测试成功率

### 告警规则
- API响应时间：P95 > 500ms
- 数据库查询：P95 > 100ms
- 构建失败率：>10%
- AI请求失败率：>5%

---

## 常见问题

### Q: 如何添加新的LLM提供商？
A: 在`src/core/llm/`目录下创建新的客户端类，继承`BaseLLMClient`，然后在`factory.py`中注册。

### Q: 如何添加新的静态分析工具？
A: 在`src/core/quality/cpp/`目录下创建新的检查器类，继承`BaseChecker`，然后在统一结果模型中集成。

### Q: 如何扩展Dashboard？
A: 在`frontend/src/views/`目录下添加新组件，在`src/api/routes/dashboard.py`中添加对应的API端点。

### Q: 如何配置Kubernetes部署？
A: 参考`docs/ARCHITECTURE.md`第10章，在`k8s/`目录下创建Deployment、Service、Ingress等资源清单。

---

## 联系方式

- **项目Owner**: [待填写]
- **技术负责人**: [待填写]
- **问题反馈**: [GitLab Issues链接]

---

**最后更新**: 2026-03-08
**维护者**: Claude AI
**版本**: v1.0
