# 开发脚本使用指南

本目录包含用于开发和调试AI-CICD项目的脚本。

---

## 🚀 快速开始

### 方式1: 同时启动前后端（推荐）

使用tmux在分屏中同时启动前后端：

```bash
./scripts/start-all.sh
```

**要求**: 需要安装tmux
```bash
sudo apt-get install tmux
```

**操作**:
- `Ctrl+B c` - 创建新窗口
- `Ctrl+B 0` - 切换到后端窗口
- `Ctrl+B 1` - 切换到前端窗口
- `Ctrl+B d` - 分离会话（服务器继续运行）

### 方式2: 分别启动

**终端1 - 启动后端**:
```bash
./scripts/start-backend.sh
```

**终端2 - 启动前端**:
```bash
./scripts/start-frontend.sh
```

---

## 📋 脚本说明

### start-backend.sh

启动FastAPI后端开发服务器

**功能**:
- ✅ 自动检查Python环境
- ✅ 自动创建虚拟环境（如果不存在）
- ✅ 自动安装依赖
- ✅ 自动创建.env配置文件
- ✅ 检查PostgreSQL和Redis
- ✅ 支持热重载
- ✅ 彩色日志输出

**使用**:
```bash
# 默认配置（localhost:8000，热重载）
./scripts/start-backend.sh

# 指定端口
./scripts/start-backend.sh --port 9000

# 指定主机
./scripts/start-backend.sh --host 127.0.0.1

# 禁用热重载
./scripts/start-backend.sh --no-reload

# 调试模式
./scripts/start-backend.sh --debug
```

**访问**:
- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

### start-frontend.sh

启动Vue 3前端开发服务器

**功能**:
- ✅ 自动检查Node.js环境
- ✅ 自动安装依赖（如果需要）
- ✅ 自动检测package.json更新
- ✅ 自动创建环境配置文件
- ✅ 检查后端服务状态
- ✅ Vite热模块替换（HMR）

**使用**:
```bash
# 默认配置（localhost:5173）
./scripts/start-frontend.sh

# 指定端口
./scripts/start-frontend.sh --port 3000

# 指定主机
./scripts/start-frontend.sh --host localhost
```

**访问**:
- 前端界面: http://localhost:5173
- 网络访问: http://YOUR_IP:5173

---

## 🔧 环境配置

### 后端配置 (.env)

脚本会自动创建默认配置，你需要修改：

```bash
# 编辑配置
vim .env
```

**必要配置**:
```env
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ai_cicd

# Redis
REDIS_URL=redis://localhost:6379/0

# GitLab
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_token_here

# LLM（至少配置一个）
ZHIPU_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### 前端配置 (frontend/.env.development)

脚本会自动创建：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_ENABLE_MOCK=false
VITE_LOG_LEVEL=debug
```

---

## 🛠️ 依赖安装

### 后端依赖

**Python 3.8+**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip python3-venv

# Fedora
sudo dnf install python3 python3-pip
```

**PostgreSQL 13+**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# 或使用Docker
docker-compose up -d db
```

**Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# 或使用Docker
docker-compose up -d redis
```

### 前端依赖

**Node.js 18+**
```bash
# 使用nvm安装（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18

# Ubuntu/Debian
sudo apt-get install nodejs npm
```

---

## 🐛 故障排除

### 问题1: 端口已被占用

**错误**: `Error: listen EADDRINUSE: address already in use :::8000`

**解决**:
```bash
# 查找占用端口的进程
sudo lsof -i :8000

# 或
sudo netstat -tulpn | grep :8000

# 杀死进程
sudo kill -9 <PID>

# 或使用其他端口
./scripts/start-backend.sh --port 9000
```

### 问题2: 虚拟环境激活失败

**错误**: `venv/bin/activate: No such file or directory`

**解决**:
```bash
# 删除旧的虚拟环境
rm -rf venv

# 重新创建
python3 -m venv venv

# 激活
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 问题3: 前端依赖安装失败

**错误**: `npm ERR!`

**解决**:
```bash
cd frontend

# 清理缓存
npm cache clean --force

# 删除node_modules和lock文件
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

### 问题4: 后端连接失败

**错误**: `API request failed`

**解决**:
1. 检查后端是否运行:
   ```bash
   curl http://localhost:8000/health
   ```

2. 检查前端配置:
   ```bash
   cat frontend/.env.development
   ```

3. 检查CORS配置:
   ```bash
   cat .env | grep CORS_ORIGINS
   ```

### 问题5: 数据库连接失败

**错误**: `connection to server at "localhost" (::1), port 5432 failed`

**解决**:
```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 启动PostgreSQL
sudo systemctl start postgresql

# 或使用Docker
docker-compose up -d db
```

---

## 📊 开发工作流

### 典型开发流程

1. **启动服务**
   ```bash
   # 方式1: tmux（推荐）
   ./scripts/start-all.sh

   # 方式2: 分别启动
   ./scripts/start-backend.sh  # 终端1
   ./scripts/start-frontend.sh  # 终端2
   ```

2. **开发前端**
   - 访问 http://localhost:5173
   - 修改 `frontend/src/` 下的代码
   - Vite自动热更新

3. **开发后端**
   - 访问 http://localhost:8000/docs 查看API
   - 修改 `src/` 下的代码
   - Uvicorn自动重载

4. **查看日志**
   - 后端日志在终端窗口
   - 前端日志在浏览器控制台

5. **停止服务**
   - 按 `Ctrl+C` 停止服务
   - 或在tmux中按 `Ctrl+B d` 分离

### 调试技巧

**后端调试**:
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用ipdb（更好的体验）
import ipdb; ipdb.set_trace()
```

**前端调试**:
- 在浏览器中按 `F12` 打开开发者工具
- Vue DevTools扩展：https://devtools.vuejs.org/

---

## 📝 相关文档

- [安装指南](../INSTALLATION_AND_USER_GUIDE.md)
- [前端部署指南](../FRONTEND_DEPLOYMENT_GUIDE.md)
- [Docker启动指南](../DOCKER_STARTUP_GUIDE.md)
- [开发规范](../CLAUDE.md)

---

**创建时间**: 2026-03-09
**维护者**: AI-CICD Team
