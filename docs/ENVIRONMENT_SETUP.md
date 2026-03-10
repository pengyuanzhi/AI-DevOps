# AI-CICD 开发环境搭建指南

> 本文档提供完整的开发环境搭建步骤，包括自动安装、手动配置和测试环境管理。

## 📋 目录

- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [自动安装](#自动安装)
- [手动安装](#手动安装)
- [测试环境](#测试环境)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### 一键安装（推荐）

```bash
# 1. 进入项目目录
cd /home/kerfs/AI-CICD-new

# 2. 运行环境检测和安装脚本
./scripts/setup-environment.sh

# 3. 配置环境变量
cp .env.example .env
nano .env  # 或使用你喜欢的编辑器

# 4. 启动服务
./start.sh
```

### 验证安装

```bash
# 检查服务状态
docker compose ps

# 访问 API 文档
open http://localhost:8000/docs

# 运行快速测试
./scripts/run-integration-tests.sh quick
```

---

## 💻 环境要求

### 核心依赖

| 工具 | 版本要求 | 用途 | 必需 |
|------|---------|------|------|
| Python | 3.13+ | 后端运行环境 | ✅ |
| Docker | 20.10+ | 容器化部署 | ✅ |
| Docker Compose | 2.0+ | 服务编排 | ✅ |
| Git | 2.0+ | 版本控制 | ✅ |
| pip | 最新版 | Python 包管理 | ✅ |

### C/C++ 工具链（可选）

| 工具 | 用途 | 必需场景 |
|------|------|---------|
| CMake 3.15+ | C++ 项目构建 | C/C++ 项目 |
| GCC/G++ 9+ | C++ 编译器 | C/C++ 项目 |
| Make/Ninja | 构建系统 | C/C++ 项目 |
| Clang-Tidy | 静态代码分析 | 代码质量检测 |
| Cppcheck | 静态代码分析 | 代码质量检测 |
| Valgrind | 内存检测 | 内存安全检测 |

### 服务依赖（Docker 自动启动）

- PostgreSQL 15+
- Redis 7.0+
- RabbitMQ 3.12+

---

## 🔧 自动安装

### Linux (Ubuntu/Debian)

```bash
# 1. 运行自动安装脚本
./scripts/setup-environment.sh

# 如果脚本提示缺少 C/C++ 工具，手动安装：
sudo apt-get update
sudo apt-get install -y build-essential cmake clang-tidy cppcheck valgrind

# 2. 配置 Python 虚拟环境（可选）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### macOS

```bash
# 1. 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 运行自动安装脚本
./scripts/setup-environment.sh

# 如果需要 C/C++ 工具：
brew install cmake llvm cppcheck valgrind

# 3. 配置 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🛠️ 手动安装

### 1. 安装 Python 3.13

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.13 python3.13-venv python3.13-dev python3.13-distutils
```

**macOS:**
```bash
brew install python@3.13
```

### 2. 安装 Docker

**Linux:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录以生效
```

**macOS:**
```bash
brew install --cask docker
# 启动 Docker Desktop 应用
```

### 3. 安装项目依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 开发工具
pip install black isort mypy flake8 pytest
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置必需的配置：

```bash
# LLM API（至少配置一个）
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ZHIPU_API_KEY=your_zhipu_api_key_here

# GitLab（可选）
GITLAB_TOKEN=your_gitlab_token
GITLAB_WEBHOOK_SECRET=your_webhook_secret
```

---

## 🧪 测试环境

### 启动测试环境

```bash
# 启动测试数据库、Redis、RabbitMQ
./scripts/start-test-env.sh start

# 查看状态
./scripts/start-test-env.sh status
```

### 运行测试

```bash
# 快速测试（无外部依赖）
./scripts/run-integration-tests.sh quick

# 完整集成测试（需要测试环境）
./scripts/start-test-env.sh start
./scripts/run-integration-tests.sh integration

# 带覆盖率报告
./scripts/run-integration-tests.sh coverage

# 单元测试
./scripts/run-integration-tests.sh unit
```

### 停止测试环境

```bash
# 停止服务
./scripts/start-test-env.sh stop

# 清理所有测试数据
./scripts/start-test-env.sh clean
```

---

## 📊 项目结构

```
AI-CICD-new/
├── src/                    # 源代码
│   ├── main.py            # 应用入口
│   ├── api/               # API 路由
│   ├── core/              # 核心业务逻辑
│   ├── models/            # 数据模型
│   ├── services/          # 服务层
│   └── utils/             # 工具类
├── tests/                 # 测试代码
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── e2e/               # 端到端测试
├── scripts/               # 脚本工具
│   ├── setup-environment.sh      # 环境安装
│   ├── start-test-env.sh         # 测试环境管理
│   └── run-integration-tests.sh  # 测试运行
├── frontend/              # Vue 3 前端
├── docs/                  # 文档
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
├── docker-compose.yml     # 生产环境配置
└── start.sh               # 启动脚本
```

---

## 🔍 验证清单

安装完成后，运行以下命令验证环境：

```bash
# 1. Python 版本
python3 --version  # 应显示 3.13+

# 2. Docker 状态
docker --version
docker compose version
docker ps

# 3. 服务健康检查
curl http://localhost:8000/health

# 4. 数据库连接
docker compose exec postgres pg_isready

# 5. Redis 连接
docker compose exec redis redis-cli ping

# 6. 运行快速测试
./scripts/run-integration-tests.sh quick
```

---

## ❓ 常见问题

### Q1: Python 版本不对

**问题:** 系统默认 Python 版本低于 3.13

**解决:**
```bash
# 使用 pyenv 管理 Python 版本
curl https://pyenv.run | bash
pyenv install 3.13
pyenv global 3.13
```

### Q2: Docker 权限错误

**问题:** `permission denied while trying to connect to the Docker daemon`

**解决:**
```bash
sudo usermod -aG docker $USER
# 重新登录
```

### Q3: 端口被占用

**问题:** `port is already allocated`

**解决:**
```bash
# 查看端口占用
sudo lsof -i :8000
sudo lsof -i :5432

# 修改 docker-compose.yml 中的端口映射
```

### Q4: 数据库连接失败

**问题:** `could not connect to server: Connection refused`

**解决:**
```bash
# 检查 PostgreSQL 容器状态
docker compose ps postgres

# 查看日志
docker compose logs postgres

# 重启服务
docker compose restart postgres
```

### Q5: 测试环境端口冲突

**问题:** 测试环境端口与生产环境冲突

**解决:**
```bash
# 测试环境使用不同端口：
# - PostgreSQL: 5433 (生产: 5432)
# - Redis: 6380 (生产: 6379)
# - RabbitMQ: 5673 (生产: 5672)

# 如果仍然冲突，编辑 scripts/start-test-env.sh 中的端口配置
```

### Q6: C/C++ 工具缺失

**问题:** 找不到 cmake/clang-tidy 等工具

**解决:**
```bash
# Ubuntu/Debian
sudo apt-get install build-essential cmake clang-tidy cppcheck valgrind

# macOS
brew install cmake llvm cppcheck valgrind
```

---

## 📚 相关文档

- [README.md](../README.md) - 项目概述
- [INSTALLATION_AND_USER_GUIDE.md](../INSTALLATION_AND_USER_GUIDE.md) - 详细安装指南
- [DOCKER_STARTUP_GUIDE.md](../DOCKER_STARTUP_GUIDE.md) - Docker 使用指南
- [tests/README.md](../tests/README.md) - 测试说明

---

## 🆘 获取帮助

如果遇到问题：

1. 查看本文档的 [常见问题](#常见问题) 部分
2. 运行环境检测脚本：`./scripts/setup-environment.sh`
3. 查看服务日志：`docker compose logs`
4. 提交 Issue：https://github.com/pengyuanzhi/AI-DevOps/issues

---

**提示:** 首次安装建议使用 `./scripts/setup-environment.sh` 自动安装脚本，它会检测环境并给出明确的指导。
