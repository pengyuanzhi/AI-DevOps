# AI驱动CI/CD平台

> 面向中型团队（20-200人）的自托管AI驱动CI/CD平台，专注于C/C++和Qt项目

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)

## 📋 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [快速开始](#快速开始)
- [功能介绍](#功能介绍)
- [技术栈](#技术栈)
- [文档](#文档)
- [开发指南](#开发指南)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目概述

AI-CICD是一个自托管的AI驱动CI/CD平台，旨在解决C/C++和Qt项目在持续集成和交付过程中的痛点。通过集成6大AI核心功能，显著提升开发效率、代码质量和资源利用率。

### 目标用户

- **团队规模**: 20-200人的技术团队
- **技术栈**: C/C++ (C11-C20), Qt 5/6
- **部署方式**: 自托管，基于Kubernetes

### 核心价值

- **CI/CD自动化**: 全流程自动化能力，支持CMake/QMake/Make/Ninja构建
- **智能化**: AI驱动的自主决策与维护，从被动执行到主动优化
- **质量保障**: 静态代码审查 + 内存安全检测，全方位保障代码质量
- **效率提升**: 智能测试选择，缩短80%以上测试反馈时间
- **资源优化**: Kubernetes智能调度与自动扩缩容，最大化集群资源利用率
- **易用性**: 自然语言生成CI/CD配置，降低YAML配置门槛

---

## 核心特性

### 🤖 6大AI核心功能

#### 1. 智能测试选择
- 基于影响域分析，精准选择受变更影响的测试
- **性能提升**: 典型PR的测试时间减少≥80%
- **技术**: Git diff解析 + 依赖图构建 + BFS遍历算法

#### 2. AI增强静态代码审查
- 集成Clang-Tidy、Cppcheck，AI统一分析结果
- **误报过滤**: 智能理解代码上下文，误报率≤10%
- **质量评分**: 5维度评分（内存安全、性能、现代C++、线程安全、代码风格）

#### 3. 自然语言配置生成
- 使用自然语言描述期望的流水线行为
- **配置时间减少**: ≥80%
- **支持**: GitLab CI YAML自动生成

#### 4. 自主流水线维护
- AI自动检测失败、诊断根因、尝试修复
- **自动修复率**: ≥90%（常见构建问题）
- **误报减少**: ≥70%

#### 5. 智能资源优化
- Kubernetes智能Pod调度、HPA/VPA自动扩缩容
- **资源利用率提升**: ≥20%
- **成本节省**: ≥15%

#### 6. 内存安全检测
- 集成Valgrind Memcheck，AI智能分析
- **检测率**: ≥90%（严重内存安全漏洞）
- **自动修复**: ≥40%的问题支持自动修复

---

## 快速开始

### 环境要求

- **Python**: 3.13+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **PostgreSQL**: 15+ (生产环境)
- **Redis**: 7.0+ (生产环境)
- **RabbitMQ**: 3.12+ (生产环境)

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/pengyuanzhi/AI-DevOps.git
cd AI-DevOps
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的配置：

```bash
# LLM API（至少配置一个）
ANTHROPIC_API_KEY=your_api_key_here
ZHIPU_API_KEY=your_zhipu_api_key

# GitLab
GITLAB_TOKEN=your_gitlab_token
GITLAB_WEBHOOK_SECRET=your_webhook_secret

# 数据库（开发环境可使用默认SQLite）
DATABASE_URL=sqlite:///./data/ai_cicd.db
```

#### 4. 启动服务

**开发模式**：
```bash
python -m src.main
```

**生产模式（Docker）**：
```bash
docker-compose up -d
```

#### 5. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 查看Dashboard
open http://localhost:8000/
```

### Docker快速启动

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
```

---

## 功能介绍

### 标准CI/CD功能

#### 代码仓库集成
- ✅ GitLab Webhook接收（Push, MR, Tag事件）
- ✅ 代码拉取和克隆优化
- ✅ 子模块和依赖处理

#### 构建系统
- ✅ CMake/QMake/Make/Ninja支持
- ✅ 增量构建（ccache集成）
- ✅ 构建产物管理和缓存

#### 自动化测试
- ✅ Qt Test集成
- ✅ 代码覆盖率分析（gcov/lcov）
- ✅ 测试报告生成和可视化

#### 部署与发布
- ✅ 多环境管理（Dev, Test, Staging, Prod）
- ✅ 版本管理（语义化版本）
- ✅ Git tag自动发布

#### 可观测性
- ✅ 实时日志流
- ✅ 性能指标Dashboard
- ✅ 资源监控（CPU、内存、磁盘、网络）
- ✅ 告警规则

### Dashboard界面

- **项目概览Dashboard**: 关键指标、趋势图表、快速入口
- **测试和质量概览**: 测试结果可视化、覆盖率报告、智能测试选择展示
- **代码质量报告**: 质量仪表盘、问题列表、增量审查视图
- **CI/CD流水线视图**: Pipeline列表、实时日志、性能分析
- **AI分析结果展示**: MR页面集成、AI决策解释
- **用户设置和配置**: 项目配置、AI模型选择、告警阈值
- **内存安全报告**: 内存安全评分、问题列表、趋势分析

---

## 技术栈

### 后端
- **Web框架**: FastAPI 0.115+, Uvicorn 0.32+
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

## 文档

### 核心文档

- **[需求文档 (v2.9)](docs/REQUIREMENTS.md)**: 完整的功能需求和技术规格
- **[技术架构设计 (v1.0)](docs/ARCHITECTURE.md)**: 系统架构设计和技术选型
- **[实施计划 (v1.0)](docs/IMPLEMENTATION_PLAN.md)**: 详细的开发计划和里程碑

### API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 开发指南

### 项目结构

```
AI-CICD-new/
├── src/                      # 源代码目录
│   ├── main.py               # FastAPI应用入口
│   ├── api/                  # API层
│   ├── core/                 # 核心业务逻辑
│   ├── integrations/         # 第三方集成
│   ├── models/               # 数据模型
│   ├── services/             # 服务层
│   └── utils/                # 工具类
├── frontend/                 # Vue 3前端（待创建）
├── tests/                    # 测试目录
├── docs/                     # 文档目录
├── configs/                  # 配置文件目录
├── data/                     # 数据存储目录
├── docker-compose.yml        # Docker Compose配置
├── Dockerfile                # Docker镜像
├── requirements.txt          # Python依赖
└── .env.example              # 环境变量模板
```

### 开发规范

#### 代码风格
- **Python**: 遵循PEP 8，使用Black格式化
- **TypeScript**: 遵循ESLint配置
- **C++**: 遵循Google C++ Style Guide

#### Git提交规范
```
feat: 新功能
fix: Bug修复
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

### 运行测试

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
```

---

## 路线图

### ✅ Phase 1: 基础设施（已完成）
- [x] FastAPI Web框架
- [x] GitLab Webhook集成
- [x] LLM客户端（Claude、智谱AI、OpenAI）
- [x] C++代码分析器
- [x] 静态代码审查集成
- [x] Docker部署

### 🚧 Phase 2: 核心功能（进行中）
- [ ] Vue 3前端Dashboard
- [ ] 构建系统执行引擎
- [ ] 自动化测试执行（Qt Test）
- [ ] 智能测试选择
- [ ] 自主流水线维护
- [ ] 智能资源优化
- [ ] 内存安全检测

### 📋 Phase 3: 生产优化（计划中）
- [ ] 性能优化（多级缓存、数据库优化）
- [ ] 可观测性完善（Prometheus + Grafana）
- [ ] Kubernetes部署
- [ ] 微服务拆分

---

## 配置GitLab Webhook

1. 进入GitLab项目设置 → Webhooks
2. 添加新的Webhook：
   - **URL**: `http://your-server:8000/webhook/gitlab`
   - **Secret token**: 与`.env`中的`GITLAB_WEBHOOK_SECRET`一致
   - **触发事件**: 勾选`Merge request events`
3. 保存并测试

---

## 常见问题

### Q: 如何添加新的LLM提供商？
A: 在`src/core/llm/`目录下创建新的客户端类，继承`BaseLLMClient`，然后在`factory.py`中注册。

### Q: 如何添加新的静态分析工具？
A: 在`src/core/quality/cpp/`目录下创建新的检查器类，继承`BaseChecker`。

### Q: 支持哪些C++构建系统？
A: 当前支持CMake、QMake、Make、Ninja。计划支持更多构建系统。

### Q: 如何配置Kubernetes部署？
A: 参考`docs/ARCHITECTURE.md`第10章，在`k8s/`目录下创建K8s资源清单。

---

## 性能目标

- **测试时间减少**: ≥80%（通过智能测试选择）
- **构建时间减少**: ≥15%（通过资源优化）
- **资源利用率提升**: ≥20%
- **系统可用性**: ≥99.5%

---

## 贡献指南

我们欢迎各种形式的贡献！

### 贡献方式

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发规范

- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档
- 确保所有测试通过

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 联系方式

- **项目Owner**: pengyuanzhi
- **GitHub**: https://github.com/pengyuanzhi/AI-DevOps
- **Issues**: https://github.com/pengyuanzhi/AI-DevOps/issues

---

## 致谢

感谢所有为这个项目做出贡献的开发者！

特别感谢：
- Anthropic - Claude API
- 智谱AI - GLM模型
- FastAPI团队 - 优秀的Web框架
- GitLab - 强大的DevOps平台

---

**注意**: 本项目目前处于v2.9开发阶段，正在积极开发中。欢迎关注我们的进展！

⭐ 如果这个项目对您有帮助，请给我们一个Star！
