# 🚀 快速启动开发服务器

本文档提供快速启动前后端开发服务器的指南。

---

## ⚡ 最快方式（推荐）

### 1. 同时启动前后端

使用tmux在分屏中启动：

```bash
./scripts/start-all.sh
```

**需要tmux**:
```bash
sudo apt-get install tmux
```

**tmux操作**:
- `Ctrl+B 0` - 切换到后端窗口
- `Ctrl+B 1` - 切换到前端窗口
- `Ctrl+B d` - 分离（服务继续运行）

---

## 📦 分别启动

### 后端服务器

**启动命令**:
```bash
./scripts/start-backend.sh
```

**访问地址**:
- API服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

**功能**:
- ✅ 自动创建虚拟环境
- ✅ 自动安装依赖
- ✅ 自动生成.env配置
- ✅ 热重载（代码修改自动重启）
- ✅ 彩色日志

### 前端服务器

**启动命令**:
```bash
./scripts/start-frontend.sh
```

**访问地址**:
- 前端界面: http://localhost:5173
- 网络访问: http://YOUR_IP:5173

**功能**:
- ✅ 自动安装Node依赖
- ✅ 检查后端服务状态
- ✅ Vite热模块替换（HMR）
- ✅ 自动打开浏览器

---

## 🛠️ 首次使用

### 1. 安装系统依赖

```bash
# Python和pip
sudo apt-get install python3 python3-pip python3-venv

# Node.js（使用nvm推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18

# PostgreSQL（或使用Docker）
sudo apt-get install postgresql postgresql-contrib

# Redis（或使用Docker）
sudo apt-get install redis-server

# tmux（可选，用于分屏）
sudo apt-get install tmux
```

### 2. 启动数据库服务

```bash
# PostgreSQL
sudo systemctl start postgresql

# Redis
sudo systemctl start redis

# 或使用Docker
docker-compose up -d db redis
```

### 3. 配置环境变量

后端会自动创建`.env`文件，编辑配置：

```bash
vim .env
```

**必要配置**:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/ai_cicd
REDIS_URL=redis://localhost:6379/0
GITLAB_URL=https://gitlab.example.com
GITLAB_TOKEN=your_token_here
ZHIPU_API_KEY=your_key_here
```

### 4. 启动开发服务器

```bash
# 方式1: 同时启动（推荐）
./scripts/start-all.sh

# 方式2: 分别启动
./scripts/start-backend.sh    # 终端1
./scripts/start-frontend.sh   # 终端2
```

---

## 💻 开发界面

### 浏览器访问

1. **打开前端**:
   ```
   http://localhost:5173
   ```

2. **查看API文档**:
   ```
   http://localhost:8000/docs
   ```

### 开发者工具

**前端**:
- 按F12打开浏览器开发者工具
- Vue DevTools扩展

**后端**:
- 终端查看日志
- 访问/docs查看API

---

## 🔧 常用命令

### 后端

```bash
# 指定端口
./scripts/start-backend.sh --port 9000

# 禁用热重载
./scripts/start-backend.sh --no-reload

# 调试模式
./scripts/start-backend.sh --debug
```

### 前端

```bash
# 指定端口
./scripts/start-frontend.sh --port 3000

# 只监听本地（不暴露到网络）
./scripts/start-frontend.sh --local-only
```

---

## 🐛 常见问题

### 端口被占用

```bash
# 查找占用进程
sudo lsof -i :8000

# 杀死进程
sudo kill -9 <PID>

# 或使用其他端口
./scripts/start-backend.sh --port 9000
```

### 后端连接失败

1. 检查后端是否运行:
   ```bash
   curl http://localhost:8000/health
   ```

2. 检查CORS配置:
   ```bash
   cat .env | grep CORS_ORIGINS
   ```

3. 查看后端日志

### 依赖安装失败

**后端**:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**前端**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 相关文档

- [详细使用指南](./README.md)
- [安装指南](../INSTALLATION_AND_USER_GUIDE.md)
- [Docker指南](../DOCKER_STARTUP_GUIDE.md)

---

**创建时间**: 2026-03-09
**维护者**: AI-CICD Team
