# AI-CICD 快速参考卡片

## 🚀 快速命令

### 环境管理

```bash
# 一键环境检测和安装
./scripts/setup-environment.sh

# 启动开发环境（支持热重载）
./start.sh

# 启动生产环境（推荐）
./scripts/deploy.sh

# 停止所有服务
docker compose down
docker compose -f docker-compose.prod.yml down

# 查看服务状态
docker compose ps
docker compose -f docker-compose.prod.yml ps
```

### 测试环境

```bash
# 启动测试环境
./scripts/start-test-env.sh start

# 停止测试环境
./scripts/start-test-env.sh stop

# 查看测试环境状态
./scripts/start-test-env.sh status

# 清理测试数据
./scripts/start-test-env.sh clean
```

### 运行测试

```bash
# 快速测试（推荐）
./scripts/run-integration-tests.sh quick

# 完整集成测试
./scripts/run-integration-tests.sh integration

# 带覆盖率报告
./scripts/run-integration-tests.sh coverage

# 只运行单元测试
./scripts/run-integration-tests.sh unit

# E2E 测试
./scripts/run-integration-tests.sh e2e
```

### 开发调试

```bash
# 本地启动（开发模式）
python3 -m src.main

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/

# Lint 检查
flake8 src/

# 查看日志
tail -f logs/app.log
docker compose logs -f ai-cicd
```

### 数据库操作

```bash
# 数据库迁移
docker compose exec ai-cicd alembic upgrade head

# 回滚迁移
docker compose exec ai-cicd alembic downgrade -1

# 查看迁移历史
docker compose exec ai-cicd alembic history

# 连接数据库
docker compose exec postgres psql -U ai_cicd -d ai_cicd
```

### 清理和维护

```bash
# 清理临时文件
./cleanup.sh

# Docker 清理
docker system prune -a

# 重新构建镜像
docker compose build --no-cache
docker compose up -d
```

## 🌐 访问地址

- **API 文档 (Swagger):** http://localhost:8000/docs
- **API 文档 (ReDoc):** http://localhost:8000/redoc
- **健康检查:** http://localhost:8000/health
- **前端界面:** http://localhost
- **RabbitMQ 管理:** http://localhost:15672 (guest/guest)
- **测试 RabbitMQ:** http://localhost:15673 (test_user/test_password)

## 📋 环境变量清单

### 必需配置

```bash
ANTHROPIC_API_KEY=your_key      # Claude API
# 或
ZHIPU_API_KEY=your_key          # 智谱 AI
```

### 可选配置

```bash
GITLAB_TOKEN=your_token         # GitLab 集成
OPENAI_API_KEY=your_key         # OpenAI (可选)
```

### 数据库配置（默认）

```bash
DATABASE_URL=postgresql+asyncpg://ai_cicd:ai_cicd_password@localhost:5432/ai_cicd
REDIS_URL=redis://:redis_password@localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

## 🔧 故障排查

### 服务无法启动

```bash
# 1. 检查端口占用
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :6379

# 2. 检查 Docker 状态
docker info
docker compose ps

# 3. 查看日志
docker compose logs
```

### 数据库连接失败

```bash
# 检查数据库状态
docker compose exec postgres pg_isready

# 重启数据库
docker compose restart postgres

# 检查连接
docker compose exec ai-cicd python -c "from src.core.database import test_connection; test_connection()"
```

### 测试失败

```bash
# 1. 确保测试环境已启动
./scripts/start-test-env.sh status

# 2. 检查测试环境日志
docker logs ai-cicd-test-postgres
docker logs ai-cicd-test-redis

# 3. 重置测试数据库
./scripts/start-test-env.sh reset-db
```

## 📦 依赖版本

- Python: 3.13+
- PostgreSQL: 15+
- Redis: 7.0+
- RabbitMQ: 3.12+
- Docker: 20.10+
- Node.js: 18+ (前端开发)

### 生产环境部署

```bash
# 1. 配置环境变量（必需）
cp .env.example .env.prod
nano .env.prod

# 必需配置：
# - POSTGRES_PASSWORD
# - REDIS_PASSWORD
# - RABBITMQ_PASSWORD
# - ANTHROPIC_API_KEY 或 ZHIPU_API_KEY

# 2. 一键部署
./scripts/deploy.sh

# 3. 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 4. 扩展服务
docker compose -f docker-compose.prod.yml up -d --scale backend=3 --scale celery-worker=3
```

## 📚 文档索引

- [环境搭建指南](docs/ENVIRONMENT_SETUP.md) - 完整安装步骤
- [Docker 构建指南](docs/DOCKER_BUILD_GUIDE.md) - Docker 构建和部署
- [README.md](README.md) - 项目概述
- [INSTALLATION_AND_USER_GUIDE.md](INSTALLATION_AND_USER_GUIDE.md) - 用户手册
- [DOCKER_STARTUP_GUIDE.md](DOCKER_STARTUP_GUIDE.md) - Docker 详细说明
- [FEATURES.md](FEATURES.md) - 功能列表
- [tests/README.md](tests/README.md) - 测试说明

---

💡 **提示:** 保存此文件为书签，方便日常快速查找命令！
