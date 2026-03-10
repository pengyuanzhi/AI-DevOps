# AI-CICD 自主流水线维护系统
## 安装与使用手册

**版本**: 1.0
**更新日期**: 2026-03-09
**适用人群**: 运维工程师、开发人员、CI/CD管理员

---

## 📋 目录

1. [系统概述](#系统概述)
2. [环境要求](#环境要求)
3. [安装步骤](#安装步骤)
4. [配置说明](#配置说明)
5. [使用指南](#使用指南)
6. [API使用示例](#api使用示例)
7. [GitLab集成](#gitlab集成)
8. [故障排查](#故障排查)
9. [最佳实践](#最佳实践)
10. [性能优化](#性能优化)

---

## 1. 系统概述

### 1.1 功能简介

AI-CICD自主流水线维护系统是一个基于人工智能的CI/CD流水线自动化维护平台，主要功能包括：

- **智能失败分类**: 自动识别15种构建和测试失败类型
- **根因分析**: 使用AI分析失败的根本原因
- **修复建议生成**: 自动生成针对性的修复建议
- **自动修复执行**: 在安全的情况下自动应用修复
- **MR自动化**: 自动创建GitLab合并请求
- **持续学习**: 从反馈中学习，不断优化

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    CI/CD 流水线                           │
│  (GitLab CI, Jenkins, GitHub Actions, etc.)              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ↓ 失败
        ┌──────────────────────┐
        │  失败日志收集          │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   失败分类器          │
        │  - 识别失败类型        │
        │  - 评估严重程度        │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   根因分析器          │
        │  - AI驱动分析         │
        │  - 变更关联分析        │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   修复生成器          │
        │  - 生成修复建议        │
        │  - 评估风险和复杂度     │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   修复执行器          │
        │  - 自动应用修复        │
        │  - 备份和回滚          │
        └──────────┬───────────┘
                   ↓
        ┌──────────────────────┐
        │   MR自动化            │
        │  - 创建合并请求        │
        │  - 添加标签和评论       │
        └──────────────────────┘
                   ↓
        ┌──────────────────────┐
        │   反馈学习器          │
        │  - 收集反馈           │
        │  - 持续优化           │
        └──────────────────────┘
```

### 1.3 核心特性

- ✅ **15种失败类型识别**: 编译错误、链接错误、测试失败、内存问题等
- ✅ **AI增强分析**: 使用LLM进行智能根因分析
- ✅ **多种修复策略**: 保守、平衡、激进、快速失败
- ✅ **安全执行**: 自动备份、失败回滚、dry-run模式
- ✅ **GitLab集成**: 自动创建和管理MR
- ✅ **持续学习**: 从历史数据中学习优化

---

## 2. 环境要求

### 2.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4核 | 8核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB | 100GB+ SSD |
| 网络 | 100Mbps | 1Gbps |

### 2.2 软件要求

#### 必需软件

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- **Python**: 3.9+
- **Git**: 2.20+
- **Docker**: 20.10+
- **Docker Compose**: 1.29+

#### Python依赖

```
fastapi>=0.68.0
uvicorn>=0.15.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.5
celery>=5.2.0
redis>=4.5.0
alembic>=1.8.0
psycopg2-binary>=2.9.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-dotenv>=0.19.0
httpx>=0.23.0
aiofiles>=0.7.0
websockets>=10.0
```

#### LLM服务（可选）

系统支持多种LLM提供商：
- **智谱AI** (GLM-4): 推荐，国内访问快
- **OpenAI** (GPT-4): 需要代理
- **Claude** (Anthropic): 需要代理

### 2.3 外部服务

- **PostgreSQL**: 12+ (用于数据持久化)
- **Redis**: 6+ (用于Celery任务队列)
- **GitLab**: 13+ (用于MR自动化)
- **消息队列**: RabbitMQ或Redis

---

## 3. 安装步骤

### 3.1 快速安装（Docker Compose）

#### 步骤1: 克隆代码仓库

```bash
git clone https://github.com/your-org/ai-cicd.git
cd ai-cicd
```

#### 步骤2: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必要的配置：

```bash
# 基础配置
PROJECT_NAME=ai-cicd
ENVIRONMENT=development

# 数据库配置
POSTGRES_USER=ai_cicd
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=ai_cicd
DATABASE_URL=postgresql://ai_cicd:your_secure_password@postgres:5432/ai_cicd

# Redis配置
REDIS_URL=redis://redis:6379/0

# GitLab配置
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_gitlab_token
GITLAB_WEBHOOK_SECRET=your_webhook_secret

# LLM配置
LLM_PROVIDER=zhipu  # 或 openai, claude
ZHIPU_API_KEY=your_zhipu_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# 应用配置
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=http://localhost:3000
```

#### 步骤3: 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f api
```

#### 步骤4: 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec api alembic upgrade head

# 创建初始数据（可选）
docker-compose exec api python scripts/init_data.py
```

#### 步骤5: 验证安装

```bash
# 健康检查
curl http://localhost:8000/health

# API文档
curl http://localhost:8000/docs
```

### 3.2 手动安装

#### 步骤1: 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3.9 \
    python3.9-venv \
    python3-pip \
    git \
    postgresql-client \
    redis-tools \
    build-essential \
    cmake

# CentOS/RHEL
sudo yum install -y \
    python39 \
    python39-pip \
    git \
    postgresql \
    redis \
    gcc-c++ \
    make \
    cmake
```

#### 步骤2: 创建Python虚拟环境

```bash
# 创建虚拟环境
python3.9 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
# venv\Scripts\activate  # Windows
```

#### 步骤3: 安装Python依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

#### 步骤4: 配置数据库

```bash
# 创建PostgreSQL数据库
sudo -u postgres psql

CREATE DATABASE ai_cicd;
CREATE USER ai_cicd WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ai_cicd TO ai_cicd;
\q
```

#### 步骤5: 运行迁移

```bash
# 设置环境变量
export DATABASE_URL="postgresql://ai_cicd:your_password@localhost:5432/ai_cicd"

# 运行迁移
alembic upgrade head
```

#### 步骤6: 启动服务

```bash
# 启动API服务
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 启动Celery Worker（另一个终端）
celery -A src.tasks.celery_app worker --loglevel=info

# 启动Celery Beat（用于定时任务，可选）
celery -A src.tasks.celery_app beat --loglevel=info
```

### 3.3 验证安装

#### 检查API服务

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm": "available"
  }
}
```

#### 检查API文档

访问浏览器打开：`http://localhost:8000/docs`

应该看到完整的API文档界面。

---

## 4. 配置说明

### 4.1 环境变量配置

#### 必需配置

```bash
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# 密钥
SECRET_KEY=your-secret-key-min-32-characters-long

# GitLab（如果使用MR自动化）
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_personal_access_token
```

#### 可选配置

```bash
# LLM提供商
LLM_PROVIDER=zhipu  # zhipu, openai, claude
ZHIPU_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# 应用设置
DEBUG=false
LOG_LEVEL=INFO
MAX_WORKERS=4
ALLOWED_HOSTS=*

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### 4.2 GitLab集成配置

#### 创建GitLab Personal Access Token

1. 登录GitLab
2. 点击头像 → Settings → Access Tokens
3. 创建新token，选择以下权限：
   - `api`
   - `read_repository`
   - `write_repository`
4. 保存token（只显示一次）

#### 配置Webhook

在GitLab项目中配置webhook：

1. 进入项目 → Settings → Webhooks
2. 添加URL: `https://your-domain.com/api/v1/webhooks/gitlab`
3. Secret: 与`GITLAB_WEBHOOK_SECRET`相同
4. 选择触发事件：
   - ✅ Pipeline events
   - ✅ Push events
   - ✅ Merge request events

### 4.3 LLM服务配置

#### 智谱AI（推荐）

```bash
# 注册账号: https://open.bigmodel.cn/
# 获取API Key

LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_api_key
ZHIPU_MODEL=glm-4
```

#### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4
OPENAI_API_BASE=https://api.openai.com/v1
```

#### Claude

```bash
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

---

## 5. 使用指南

### 5.1 快速开始

#### 场景1: 分析失败的构建

```bash
curl -X POST "http://localhost:8000/api/v1/pipeline-maintenance/v2/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "log_content": "error: main.cpp:42: undefined reference to `foo'",
    "is_build": true
  }'
```

响应：
```json
{
  "failure_type": "link_error",
  "severity": "high",
  "confidence": 0.9,
  "error_location": "main.cpp:42",
  "error_message": "undefined reference to `foo'",
  "suggested_actions": [
    "链接缺失的库文件",
    "检查函数声明和定义是否匹配"
  ],
  "auto_fix_available": false
}
```

#### 场景2: 完整的自动修复流程

```bash
# 1. 分类失败
CLASSIFY_RESULT=$(curl -s -X POST "http://localhost:8000/api/v1/pipeline-maintenance/v2/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "log_content": "...",
    "is_build": true
  }')

# 2. 分析根因
ROOT_CAUSE=$(curl -s -X POST "http://localhost:8000/api/v1/pipeline-maintenance/v2/analyze-root-cause" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": 1,
    \"pipeline_id\": \"pipeline_123\",
    \"job_id\": \"job_456\",
    \"log_content\": \"...\",
    \"failure_type\": \"link_error\",
    \"changed_files\": [\"src/foo.cpp\"],
    \"use_ai\": true
  }")

# 3. 生成修复建议
FIX_SUGGESTION=$(curl -s -X POST "http://localhost:8000/api/v1/pipeline-maintenance/v2/generate-fix" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": 1,
    \"pipeline_id\": \"pipeline_123\",
    \"job_id\": \"job_456\",
    \"root_cause_type\": \"dependency_issue\",
    \"title\": \"缺少库依赖\",
    \"description\": \"链接时找不到foo函数\",
    \"confidence\": 0.85,
    \"use_ai\": true
  }")

# 4. 执行修复（dry-run模式）
curl -X POST "http://localhost:8000/api/v1/pipeline-maintenance/v2/execute-fix" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": 1,
    \"pipeline_id\": \"pipeline_123\",
    \"job_id\": \"job_456\",
    \"suggestion_id\": \"fix_123\",
    \"fix_type\": \"code_change\",
    \"complexity\": \"simple\",
    \"title\": \"修复链接错误\",
    \"description\": \"添加foo.cpp到CMakeLists.txt\",
    \"code_changes\": [...],
    \"commands\": [\"cmake ..\", \"make\"],
    \"project_path\": \"/path/to/project\",
    \"dry_run\": true
  }"
```

### 5.2 Python SDK使用

#### 安装SDK

```bash
pip install ai-cicd-client
```

#### 基本使用

```python
from ai_cicd import PipelineMaintenanceClient

# 初始化客户端
client = PipelineMaintenanceClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# 分析失败
classification = client.classify_failure(
    project_id=1,
    pipeline_id="pipeline_123",
    job_id="job_456",
    log_content="error: undefined reference",
    is_build=True
)

print(f"失败类型: {classification.failure_type}")
print(f"严重程度: {classification.severity}")

# 获取根因分析
root_cause = client.analyze_root_cause(
    project_id=1,
    pipeline_id="pipeline_123",
    job_id="job_456",
    log_content="...",
    failure_type=classification.failure_type,
    use_ai=True
)

print(f"根因: {root_cause.title}")
print(f"置信度: {root_cause.confidence}")

# 生成修复建议
suggestions = client.generate_fix(
    root_cause_type=root_cause.root_cause_type,
    title=root_cause.title,
    description=root_cause.description,
    confidence=root_cause.confidence
)

for suggestion in suggestions:
    print(f"建议: {suggestion.title}")
    print(f"复杂度: {suggestion.complexity}")
    print(f"风险: {suggestion.risk_level}")

# 执行修复
result = client.execute_fix(
    suggestion=suggestions[0],
    project_path="/path/to/project",
    dry_run=True  # 先用dry-run测试
)

if result.success:
    print("修复成功！")
else:
    print(f"修复失败: {result.error_message}")
```

### 5.3 GitLab CI集成

#### .gitlab-ci.yml配置

```yaml
stages:
  - build
  - test
  - auto-fix

variables:
  PIPELINE_MAINTENANCE_URL: http://your-server:8000

build:
  stage: build
  script:
    - mkdir build && cd build
    - cmake .. && make
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

test:
  stage: test
  script:
    - cd build
    - ctest --output-on-failure
  dependencies:
    - build

# 失败分析（仅在失败时运行）
analyze_failure:
  stage: auto-fix
  script:
    - |
      # 获取失败日志
      LOG_CONTENT=$(cat build/error.log)

      # 调用分析API
      curl -X POST "$PIPELINE_MAINTENANCE_URL/api/v1/pipeline-maintenance/v2/classify" \
        -H "Content-Type: application/json" \
        -d "{
          \"project_id\": $CI_PROJECT_ID,
          \"pipeline_id\": $CI_PIPELINE_ID,
          \"job_id\": $CI_JOB_ID,
          \"log_content\": $(echo "$LOG_CONTENT" | jq -Rs .),
          \"is_build\": true
        }" > analysis_result.json

      # 显示分析结果
      cat analysis_result.json | jq '.'
  when:
    - on_failure
  dependencies:
    - build
  allow_failure: true

# 自动修复（仅限简单问题）
auto_fix:
  stage: auto-fix
  script:
    - |
      # 从分析结果中获取失败类型
      FAILURE_TYPE=$(cat analysis_result.json | jq -r '.failure_type')

      # 只有简单的配置问题才自动修复
      if [[ "$FAILURE_TYPE" == "configuration_error" ]] || \
         [[ "$FAILURE_TYPE" == "missing_dependency" ]]; then

        echo "尝试自动修复..."

        # 生成并执行修复
        curl -X POST "$PIPELINE_MAINTENANCE_URL/api/v1/pipeline-maintenance/v2/execute-fix" \
          -H "Content-Type: application/json" \
          -d @fix_request.json

        echo "修复已应用，重新运行流水线"
      else
        echo "失败类型 $FAILURE_TYPE 不适合自动修复"
        exit 1
      fi
  when:
    - on_failure
  dependencies:
    - analyze_failure
  allow_failure: true
```

---

## 6. API使用示例

### 6.1 失败分类API

**端点**: `POST /api/v1/pipeline-maintenance/v2/classify`

**Python示例**:
```python
import requests

url = "http://localhost:8000/api/v1/pipeline-maintenance/v2/classify"
payload = {
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "log_content": """
    /usr/bin/ld: /tmp/main.o: in function `main':
    main.cpp:(.text+0x42): undefined reference to `calculate'
    collect2: error: ld returned 1 exit status
    """,
    "is_build": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"失败类型: {result['failure_type']}")
print(f"严重程度: {result['severity']}")
print(f"置信度: {result['confidence']}")
print(f"建议操作: {result['suggested_actions']}")
```

### 6.2 根因分析API

**端点**: `POST /api/v1/pipeline-maintenance/v2/analyze-root-cause`

```python
url = "http://localhost:8000/api/v1/pipeline-maintenance/v2/analyze-root-cause"
payload = {
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "log_content": "...",
    "failure_type": "link_error",
    "changed_files": ["src/calculator.cpp", "CMakeLists.txt"],
    "error_location": "main.cpp:42",
    "use_ai": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"根因类型: {result['root_cause_type']}")
print(f"描述: {result['description']}")
print(f"负责文件: {result['responsible_files']}")
print(f"修复建议: {result['suggested_fixes']}")
```

### 6.3 修复生成API

**端点**: `POST /api/v1/pipeline-maintenance/v2/generate-fix`

```python
url = "http://localhost:8000/api/v1/pipeline-maintenance/v2/generate-fix"
payload = {
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "root_cause_type": "dependency_issue",
    "title": "缺少库依赖",
    "description": "链接时找不到calculate函数",
    "confidence": 0.85,
    "responsible_files": ["src/calculator.cpp"],
    "use_ai": True
}

response = requests.post(url, json=payload)
result = response.json()

print(f"生成了 {len(result['suggestions'])} 个修复建议")

for i, suggestion in enumerate(result['suggestions'], 1):
    print(f"\n建议 {i}:")
    print(f"  标题: {suggestion['title']}")
    print(f"  复杂度: {suggestion['complexity']}")
    print(f"  风险: {suggestion['risk_level']}")
    print(f"  预估时间: {suggestion['estimated_time']}")
    print(f"  可自动应用: {suggestion['auto_applicable']}")
```

### 6.4 修复执行API

**端点**: `POST /api/v1/pipeline-maintenance/v2/execute-fix`

```python
url = "http://localhost:8000/api/v1/pipeline-maintenance/v2/execute-fix"
payload = {
    "project_id": 1,
    "pipeline_id": "pipeline_123",
    "job_id": "job_456",
    "suggestion_id": "fix_20260309_123456",
    "fix_type": "code_change",
    "complexity": "simple",
    "title": "更新CMakeLists.txt",
    "description": "添加calculator.cpp到编译列表",
    "code_changes": [
        {
            "file_path": "CMakeLists.txt",
            "old_code": "add_executable(demo main.cpp)",
            "new_code": "add_executable(demo main.cpp calculator.cpp)",
            "description": "添加calculator.cpp"
        }
    ],
    "commands": ["cmake ..", "make"],
    "verification_steps": ["运行测试", "检查输出"],
    "project_path": "/path/to/project",
    "dry_run": False  # 设置为True进行模拟运行
}

response = requests.post(url, json=payload)
result = response.json()

print(f"执行状态: {result['status']}")
print(f"成功: {result['success']}")
print(f"修改文件: {result['modified_files']}")
print(f"备份位置: {result['backup_location']}")
print(f"验证通过: {result['verification_passed']}")

if result['rollback_attempted']:
    print(f"已回滚: {result['rollback_succeeded']}")
```

### 6.5 反馈提交API

**端点**: `POST /api/v1/pipeline-maintenance/v2/feedback`

```python
url = "http://localhost:8000/api/v1/pipeline-maintenance/v2/feedback"
payload = {
    "suggestion_id": "fix_20260309_123456",
    "feedback_type": "fix_success",  # 或 fix_failure, false_positive
    "execution_status": "succeeded",
    "execution_time": 45.2,
    "user_rating": 5,
    "user_comments": "修复成功，测试通过"
}

response = requests.post(url, json=payload)
result = response.json()

print(f"反馈已记录: {result['recorded']}")
print(f"记录ID: {result['record_id']}")
```

---

## 7. GitLab集成

### 7.1 自动创建修复MR

```python
import requests
import json

# 配置
GITLAB_URL = "https://gitlab.example.com"
GITLAB_TOKEN = "your_access_token"
PROJECT_ID = "your_project_id"

# 触发自动修复
def trigger_auto_fix(pipeline_id, job_id, log_content, project_path):
    # 1. 分类失败
    classify_result = requests.post(
        f"http://localhost:8000/api/v1/pipeline-maintenance/v2/classify",
        json={
            "project_id": PROJECT_ID,
            "pipeline_id": pipeline_id,
            "job_id": job_id,
            "log_content": log_content,
            "is_build": True
        }
    ).json()

    # 2. 如果是简单问题，尝试自动修复
    if classify_result['confidence'] > 0.8:
        fix_result = requests.post(
            f"http://localhost:8000/api/v1/pipeline-maintenance/v2/execute-fix",
            json={
                **generate_fix_request(classify_result),
                "project_path": project_path,
                "dry_run": False
            }
        ).json()

        # 3. 如果修复成功，创建MR
        if fix_result['success']:
            create_fix_mr(
                pipeline_id,
                job_id,
                fix_result,
                classify_result
            )

def create_fix_mr(pipeline_id, job_id, fix_result, classify_result):
    """创建修复MR"""
    import subprocess

    # 推送修改到新分支
    branch_name = f"auto-fix/{pipeline_id}/{job_id}"
    subprocess.run([
        "git", "checkout", "-b", branch_name
    ])
    subprocess.run(["git", "add", "."])
    subprocess.run([
        "git", "commit", "-m",
        f"Auto-fix for pipeline {pipeline_id}, job {job_id}\n\n"
        f"Failure type: {classify_result['failure_type']}\n"
        f"Fix applied: {fix_result['modified_files']}"
    ])
    subprocess.run(["git", "push", "origin", branch_name])

    # 通过GitLab API创建MR
    mr_request = {
        "source_branch": branch_name,
        "target_branch": "main",
        "title": f"[AI修复] {classify_result['suggested_actions'][0]}",
        "description": generate_mr_description(fix_result, classify_result),
        "labels": ["AI修复", "auto-created", classify_result['severity']],
        "remove_source_branch": True
    }

    response = requests.post(
        f"{GITLAB_URL}/api/v4/projects/{PROJECT_ID}/merge_requests",
        headers={"PRIVATE-TOKEN": GITLAB_TOKEN},
        json=mr_request
    )

    if response.status_code == 201:
        mr = response.json()
        print(f"MR已创建: {mr['web_url']}")
    else:
        print(f"MR创建失败: {response.text}")

def generate_mr_description(fix_result, classify_result):
    """生成MR描述"""
    return f"""
## 自动修复

此MR由AI-CICD系统自动创建。

### 失败信息
- **失败类型**: {classify_result['failure_type']}
- **严重程度**: {classify_result['severity']}
- **置信度**: {classify_result['confidence']:.2%}

### 修复详情
- **状态**: {fix_result['status']}
- **修改文件**: {', '.join(fix_result['modified_files'])}
- **执行时间**: {fix_result['duration_seconds']:.2f}秒

### 验证
- **验证通过**: {fix_result['verification_passed']}
- **回滚**: {'是' if fix_result['rollback_attempted'] else '否'}

### 审查建议
1. 检查修改的文件
2. 运行相关测试
3. 确认没有副作用
4. 通过后合并此MR

---
自动创建于: {datetime.now().isoformat()}
"""
```

### 7.2 Webhook配置

在GitLab项目中添加webhook：

**URL**: `https://your-domain.com/api/v1/webhooks/gitlab`

**Secret**: 从环境变量`GITLAB_WEBHOOK_SECRET`获取

**事件**:
- ✅ Pipeline events
- ✅ Push events
- ✅ Merge request events

---

## 8. 故障排查

### 8.1 常见问题

#### 问题1: API服务无法启动

**症状**:
```
Error: Unable to connect to database
```

**解决方案**:
```bash
# 检查数据库是否运行
docker-compose ps postgres

# 检查数据库连接
docker-compose exec api python -c "
from src.db.session import get_db_session
db = get_db_session()
print('Database connected:', db is not None)
"

# 重启数据库
docker-compose restart postgres

# 重新运行迁移
docker-compose exec api alembic upgrade head
```

#### 问题2: LLM服务连接失败

**症状**:
```
Error: LLM service not available
```

**解决方案**:
```bash
# 检查API密钥配置
echo $ZHIPU_API_KEY
echo $OPENAI_API_KEY

# 测试LLM连接
curl -X POST "http://localhost:8000/api/v1/llm/test" \
  -H "Content-Type: application/json" \
  -d '{"provider": "zhipu", "message": "test"}'

# 检查日志
docker-compose logs -f api | grep -i llm

# 更换LLM提供商
export LLM_PROVIDER=zhipu  # 或 openai, claude
docker-compose restart api
```

#### 问题3: 自动修复失败

**症状**:
```
Error: Fix execution failed: permission denied
```

**解决方案**:
```bash
# 检查项目目录权限
ls -la /path/to/project

# 确保正确的文件权限
chmod -R u+rw /path/to/project

# 使用dry-run模式先测试
"dry_run": true

# 检查备份目录
ls -la /tmp/ai-cicd-fix-backups/
```

#### 问题4: GitLab MR创建失败

**症状**:
```
Error: Failed to create MR: 401 Unauthorized
```

**解决方案**:
```bash
# 验证GitLab Token
curl -H "PRIVATE-TOKEN: your_token" \
  "https://gitlab.example.com/api/v4/user"

# 检查token权限
# 需要: api, read_repository, write_repository

# 更新token
export GITLAB_TOKEN=new_token
docker-compose restart api
```

### 8.2 日志查看

#### 查看API日志

```bash
# Docker环境
docker-compose logs -f api

# 手动安装
tail -f /var/log/ai-cicd/api.log
```

#### 查看Celery日志

```bash
# Docker环境
docker-compose logs -f celery-worker

# 手动安装
tail -f /var/log/ai-cicd/celery.log
```

#### 启用调试日志

```bash
# 在.env文件中设置
DEBUG=true
LOG_LEVEL=DEBUG

# 重启服务
docker-compose restart api
```

### 8.3 性能问题

#### 问题: API响应慢

**诊断**:
```bash
# 检查系统资源
htop

# 检查数据库连接
docker-compose exec api python -c "
import time
start = time.time()
from src.db.session import get_db_session
db = get_db_session()
end = time.time()
print(f'DB connection time: {end-start:.3f}s')
"

# 检查LLM响应时间
grep "llm_response_time" /var/log/ai-cicd/api.log | tail -10
```

**优化方案**:
```bash
# 1. 增加worker数量
export MAX_WORKERS=8

# 2. 启用缓存
export ENABLE_CACHE=true
export CACHE_TTL=3600

# 3. 使用更快的LLM
export LLM_PROVIDER=zhipu  # 比OpenAI快

# 4. 数据库连接池
export DB_POOL_SIZE=20
```

---

## 9. 最佳实践

### 9.1 部署建议

#### 开发环境

```yaml
services:
  api:
    image: ai-cicd:latest
    ports:
      - "8000:8000"
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - ./src:/app/src
      - ./data:/app/data
```

#### 生产环境

```yaml
services:
  api:
    image: ai-cicd:latest
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - MAX_WORKERS=8
    deploy:
      replicas: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 9.2 安全建议

#### 1. 使用环境变量管理密钥

```bash
# 不要在代码中硬编码密钥
# 使用.env文件（不提交到git）
echo ".env" >> .gitignore
```

#### 2. 启用HTTPS

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    location / {
        proxy_pass http://localhost:8000;
    }
}
```

#### 3. 限制API访问

```python
# 在API中添加认证
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(
    token: str = Depends(HTTPBearer())
):
    # 验证token
    if not validate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )
    return user
```

### 9.3 监控和告警

#### 健康检查

```bash
# 设置定期健康检查
*/5 * * * * curl -f http://localhost:8000/health || \
  echo "API服务异常" | mail -s "Alert" admin@example.com
```

#### 日志监控

```python
# 使用Prometheus监控
from prometheus_client import Counter, Histogram

# 指标定义
failure_classification_total = Counter(
    'failure_classification_total',
    'Total number of failure classifications',
    ['failure_type', 'severity']
)

fix_execution_duration = Histogram(
    'fix_execution_duration_seconds',
    'Time taken to execute fixes',
    buckets=[1, 5, 10, 30, 60, 300]
)
```

---

## 10. 性能优化

### 10.1 数据库优化

#### 使用连接池

```python
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### 添加索引

```sql
-- 失败分类索引
CREATE INDEX idx_failure_type ON pipeline_failures(failure_type);
CREATE INDEX idx_severity ON pipeline_failures(severity);
CREATE INDEX idx_timestamp ON pipeline_failures(created_at);

-- 修复建议索引
CREATE INDEX idx_suggestion_id ON fix_suggestions(suggestion_id);
CREATE INDEX idx_fix_type ON fix_suggestions(fix_type);
```

### 10.2 缓存策略

#### Redis缓存

```python
import redis
import json
from typing import Optional

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_get(key: str) -> Optional[dict]:
    """从缓存获取"""
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None

def cache_set(key: str, value: dict, ttl: int = 3600):
    """设置缓存"""
    redis_client.setex(
        key,
        ttl,
        json.dumps(value)
    )

# 使用示例
def classify_with_cache(log_content: str) -> dict:
    cache_key = f"classify:{hash(log_content)}"

    # 尝试从缓存获取
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 执行分类
    result = failure_classifier.classify(log_content, {})

    # 存入缓存
    cache_set(cache_key, result, ttl=3600)

    return result
```

### 10.3 异步处理

#### 使用Celery异步任务

```python
from celery import Celery

celery_app = Celery(
    'ai_cicd',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

@celery_app.task
def async_classify_failure(log_content: str):
    """异步分类失败"""
    result = failure_classifier.classify(log_content, {})
    return result

# 使用示例
def classify_async(log_content: str):
    """异步分类"""
    task = async_classify_failure.delay(log_content)
    return task.id

# 获取结果
from celery.result import AsyncResult

task_id = classify_async(log_content)
task = AsyncResult(task_id)
result = task.get(timeout=30)
```

---

## 11. 常见使用场景

### 场景1: 持续集成中的自动修复

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - auto-fix

build:
  stage: build
  script:
    - cmake -B build && cd build
    - make -j$(nproc)
  artifacts:
    paths:
      - build/

test:
  stage: test
  script:
    - cd build
    - ctest --output-on-failure
  dependencies:
    - build

auto_fix:
  stage: auto-fix
  script:
    - |
      # 只有简单的配置问题才自动修复
      ANALYSIS=$(curl -s -X POST "$MAINTENANCE_API/classify" \
        -H "Content-Type: application/json" \
        -d @<(cat <<'EOF'
      {
        "project_id": $CI_PROJECT_ID,
        "pipeline_id": $CI_PIPELINE_ID,
        "job_id": $CI_JOB_ID,
        "log_content": "$(cat build/error.log)",
        "is_build": true
      }
      EOF
      ))

      FAILURE_TYPE=$(echo $ANALYSIS | jq -r '.failure_type')

      if [[ "$FAILURE_TYPE" =~ ^(configuration_error|missing_dependency)$ ]]; then
        echo "尝试自动修复..."
        curl -X POST "$MAINTENANCE_API/execute-fix" \
          -H "Content-Type: application/json" \
          -d @<(cat <<'EOF'
          {
            "project_id": $CI_PROJECT_ID,
            "pipeline_id": $CI_PIPELINE_ID,
            "job_id": $CI_JOB_ID,
            "suggestion_id": "auto",
            "fix_type": "config_change",
            "complexity": "simple",
            "title": "Auto fix",
            "description": "Auto-generated fix",
            "commands": ["cmake -B build", "cd build", "make"],
            "project_path": "$(pwd)",
            "dry_run": false
          }
          EOF
          )
      fi
  when:
    - on_failure
  dependencies:
    - build
  allow_failure: true
```

### 场景2: 批量分析历史失败

```python
import requests
from pathlib import Path

def analyze_history_logs(log_dir: str):
    """批量分析历史日志"""
    log_files = Path(log_dir).glob("**/*.log")

    results = []
    for log_file in log_files:
        print(f"分析: {log_file}")

        log_content = log_file.read_text()

        result = requests.post(
            "http://localhost:8000/api/v1/pipeline_maintenance/v2/classify",
            json={
                "project_id": 1,
                "pipeline_id": "historical",
                "job_id": log_file.stem,
                "log_content": log_content,
                "is_build": True
            }
        ).json()

        results.append({
            "file": str(log_file),
            "failure_type": result["failure_type"],
            "severity": result["severity"],
            "confidence": result["confidence"]
        })

    # 生成报告
    import pandas as pd
    df = pd.DataFrame(results)

    print("\n失败类型统计:")
    print(df["failure_type"].value_counts())

    print("\n严重程度统计:")
    print(df["severity"].value_counts())

    print(f"\n平均置信度: {df["confidence"].mean():.2%}")

# 使用
analyze_history_logs("/path/to/logs")
```

### 场景3: 定期健康检查

```python
import schedule
import time
from datetime import datetime

def daily_health_check():
    """每日健康检查"""
    print(f"[{datetime.now()}] 开始健康检查...")

    # 检查API服务
    try:
        response = requests.get(
            "http://localhost:8000/health",
            timeout=5
        )
        if response.status_code == 200:
            print("✓ API服务正常")
        else:
            print("✗ API服务异常")
    except Exception as e:
        print(f"✗ API服务无法访问: {e}")

    # 检查统计信息
    try:
        stats = requests.get(
            "http://localhost:8000/api/v1/pipeline-maintenance/v2/statistics"
        ).json()

        if stats.get("available"):
            print(f"✓ 统计服务正常")
            metrics = stats["metrics"]
            print(f"  总修复数: {metrics['total_fixes']}")
            print(f"  成功率: {metrics['overall_success_rate']:.1%}")
        else:
            print("✗ 统计服务未初始化")
    except Exception as e:
        print(f"✗ 统计服务异常: {e}")

    print()

# 每天早上8点运行
schedule.every().day.at("08:00").do(daily_health_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 12. 更新和维护

### 12.1 系统更新

#### 更新到最新版本

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 运行数据库迁移
alembic upgrade head

# 重启服务
docker-compose down
docker-compose up -d
```

#### 备份和恢复

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U ai_cicd ai_cicd > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker-compose exec -T postgres psql -U ai_cicd ai_cicd < backup_20260309.sql
```

### 12.2 日志管理

#### 日志轮转

```bash
# /etc/logrotate.d/ai-cicd
/var/log/ai-cicd/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
    systemctl reload nginx > /dev/null 2>&1 || true
}
```

---

## 13. 附录

### 13.1 环境变量完整列表

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | string | - | PostgreSQL连接字符串 |
| `REDIS_URL` | string | - | Redis连接字符串 |
| `SECRET_KEY` | string | - | JWT密钥（至少32字符） |
| `DEBUG` | boolean | false | 调试模式 |
| `LOG_LEVEL` | string | INFO | 日志级别 |
| `MAX_WORKERS` | int | 4 | 最大worker数 |
| `LLM_PROVIDER` | string | zhipu | LLM提供商 |
| `GITLAB_URL` | string | - | GitLab实例URL |
| `GITLAB_TOKEN` | string | - | GitLab访问令牌 |
| `CORS_ORIGINS` | list | [] | CORS允许的来源 |

### 13.2 API端点列表

#### 失败分析

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/pipeline-maintenance/v2/classify` | 分类失败 |
| POST | `/api/v1/pipeline-maintenance/v2/analyze-root-cause` | 分析根因 |
| POST | `/api/v1/pipeline-maintenance/v2/generate-fix` | 生成修复 |
| POST | `/api/v1/pipeline-maintenance/v2/execute-fix` | 执行修复 |
| POST | `/api/v1/pipeline-maintenance/v2/feedback` | 提交反馈 |
| GET | `/api/v1/pipeline-maintenance/v2/statistics` | 获取统计 |

#### 其他功能

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/docs` | API文档 |
| GET | `/api/v1/pipeline-maintenance/v2/best-practices` | 最佳实践 |

### 13.3 故障代码参考

| 代码 | 类型 | 说明 |
|------|------|------|
| `compilation_error` | 构建错误 | 编译错误 |
| `link_error` | 构建错误 | 链接错误 |
| `missing_dependency` | 构建错误 | 缺失依赖 |
| `test_failure` | 测试错误 | 测试失败 |
| `timeout` | 测试错误 | 超时 |
| `segmentation_fault` | 运行时错误 | 段错误 |
| `memory_leak` | 运行时错误 | 内存泄漏 |
| `out_of_memory` | 资源错误 | 内存不足 |
| `disk_full` | 资源错误 | 磁盘满 |

### 13.4 联系方式

- **文档**: https://docs.ai-cicd.example.com
- **GitHub**: https://github.com/your-org/ai-cicd
- **Issue**: https://github.com/your-org/ai-cicd/issues
- **邮件**: support@example.com

---

**文档版本**: 1.0
**最后更新**: 2026-03-09
**维护者**: AI-CICD开发团队
