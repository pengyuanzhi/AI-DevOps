# 前端部署指南

**部署方式**: Docker Compose
**访问路径**: 根路径 `/`
**配置日期**: 2026-03-09

---

## ✅ 已完成的配置

| 文件 | 状态 | 说明 |
|------|------|------|
| `frontend/nginx.conf` | ✅ 已创建 | Nginx配置（静态托管+API代理） |
| `frontend/Dockerfile` | ✅ 已创建 | 多阶段构建（Node构建+Nginx托管） |
| `frontend/.dockerignore` | ✅ 已创建 | Docker构建排除文件 |
| `frontend/vite.config.ts` | ✅ 已更新 | 添加 `base: '/'` 配置 |
| `frontend/.env.production` | ✅ 已更新 | API地址改为 `/api` |
| `docker-compose.yml` | ✅ 已更新 | 添加frontend服务 |
| `deploy-frontend.sh` | ✅ 已创建 | 一键部署脚本 |

---

## 🚀 部署步骤

### 方式1: 使用部署脚本（推荐）

```bash
# 进入项目目录
cd /home/kerfs/AI-CICD-new

# 运行部署脚本
./deploy-frontend.sh
```

### 方式2: 手动部署

```bash
# 1. 构建前端镜像
docker-compose build frontend

# 2. 启动前端容器
docker-compose up -d frontend

# 3. 查看容器状态
docker-compose ps frontend

# 4. 查看日志
docker-compose logs -f frontend
```

### 方式3: 同时部署所有服务

```bash
# 启动所有服务（包括前端）
docker-compose up -d

# 查看所有服务状态
docker-compose ps
```

---

## 🌐 访问地址

部署成功后，可通过以下地址访问：

- **前端页面**: http://localhost
- **API接口**: http://localhost/api/v1/*
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost/health

---

## 🔍 验证部署

### 1. 检查容器状态

```bash
docker-compose ps frontend
```

**预期输出**:
```
NAME                  STATUS          PORTS
ai-cicd-frontend      Up (healthy)    0.0.0.0:80->80/tcp
```

### 2. 测试前端访问

```bash
curl -I http://localhost
```

**预期输出**: `HTTP/1.1 200 OK`

### 3. 测试API代理

```bash
curl http://localhost/api/v1/projects
```

### 4. 检查健康状态

```bash
curl http://localhost/health
```

**预期输出**: `healthy`

---

## 📝 常用命令

### 查看日志

```bash
# 查看前端日志
docker-compose logs -f frontend

# 查看最近100行日志
docker-compose logs --tail=100 frontend
```

### 重启服务

```bash
# 重启前端
docker-compose restart frontend

# 重启所有服务
docker-compose restart
```

### 停止服务

```bash
# 停止前端
docker-compose stop frontend

# 停止所有服务
docker-compose down
```

### 重新构建

```bash
# 重新构建前端镜像
docker-compose build --no-cache frontend

# 构建并启动
docker-compose up -d --build frontend
```

---

## ⚙️ 配置说明

### 端口配置

默认映射为 `80:80`，如需修改：

**编辑** `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "8080:80"  # 使用8080端口访问
```

访问地址变为: `http://localhost:8080`

### 环境变量

**开发环境** (`frontend/.env.development`):
```
VITE_API_BASE_URL=http://localhost:8000
```

**生产环境** (`frontend/.env.production`):
```
VITE_API_BASE_URL=/api
```

### Nginx配置

配置文件: `frontend/nginx.conf`

关键配置:
- **静态文件**: `/usr/share/nginx/html`
- **API代理**: `/api/*` → `http://ai-cicd:8000/api/*`
- **SPA路由**: 所有路由返回 `index.html`
- **静态资源缓存**: 1年
- **WebSocket支持**: 已启用

---

## 🐛 故障排查

### 问题1: 端口80被占用

**错误信息**: `Bind for 0.0.0.0:80 failed: port is already allocated`

**解决方案**:
1. 查看占用进程: `sudo lsof -i :80`
2. 停止占用进程或修改端口映射

### 问题2: 容器无法启动

**排查步骤**:
```bash
# 查看容器日志
docker-compose logs frontend

# 检查容器状态
docker-compose ps -a

# 查看详细错误
docker inspect ai-cicd-frontend
```

### 问题3: API请求失败

**可能原因**:
1. 后端服务未启动: `docker-compose ps ai-cicd`
2. 网络配置问题: 检查 `ai-cicd-network`
3. API路径错误: 确认使用 `/api/v1/*`

**排查命令**:
```bash
# 测试后端服务
curl http://localhost:8000/health

# 测试容器间网络
docker exec ai-cicd-frontend curl http://ai-cicd:8000/health
```

### 问题4: 前端页面空白

**可能原因**:
1. 构建失败: 检查 `npm run build` 是否成功
2. 静态文件路径错误: 检查Nginx配置
3. 浏览器缓存: 清除缓存或使用无痕模式

**排查步骤**:
```bash
# 检查构建产物
docker exec ai-cicd-frontend ls -la /usr/share/nginx/html

# 查看Nginx错误日志
docker exec ai-cicd-frontend cat /var/log/nginx/error.log
```

---

## 🔒 安全建议

### 生产环境部署

1. **启用HTTPS**
   - 配置SSL证书
   - 使用Let's Encrypt

2. **安全响应头**
   ```nginx
   add_header X-Frame-Options "SAMEORIGIN";
   add_header X-Content-Type-Options "nosniff";
   add_header X-XSS-Protection "1; mode=block";
   add_header Strict-Transport-Security "max-age=31536000";
   ```

3. **限流配置**
   ```nginx
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   limit_req zone=api burst=20 nodelay;
   ```

4. **非root用户**
   - 已配置，容器使用 `nginx-app` 用户运行

---

## 📊 性能优化

### 已实现的优化

- ✅ 多阶段构建减小镜像体积
- ✅ 静态资源长期缓存（1年）
- ✅ Gzip压缩
- ✅ 代码分割（Vue、Element Plus、ECharts）
- ✅ 非root用户运行

### 后续优化建议

- [ ] CDN集成（静态资源CDN加速）
- [ ] HTTP/2支持
- [ ] Brotli压缩（替代Gzip）
- [ ] 镜像仓库缓存

---

## 📚 部署架构

```
┌─────────────────────────────────────────────┐
│            Docker Compose                   │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐      ┌──────────────┐    │
│  │  Frontend   │─────>│    Nginx     │    │
│  │  (Vue 3)    │      │   (Proxy)    │    │
│  │  Port: 80   │      └──────┬───────┘    │
│  └─────────────┘             │             │
│                              │             │
│                              ▼             │
│                     ┌──────────────┐      │
│                     │  Backend     │      │
│                     │  (FastAPI)   │      │
│                     │  Port: 8000  │      │
│                     └──────────────┘      │
│                                             │
│  ┌──────────────┐  ┌──────────────┐       │
│  │  PostgreSQL  │  │    Redis     │       │
│  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────┘
```

**通信流程**:
1. 用户访问 `http://localhost`
2. Nginx返回Vue应用静态文件
3. 前端请求 `/api/v1/*`
4. Nginx代理到 `http://ai-cicd:8000/api/*`
5. 后端处理并返回数据

---

## 📖 相关文档

- [Docker Compose文档](https://docs.docker.com/compose/)
- [Nginx配置指南](https://nginx.org/en/docs/)
- [Vite部署指南](https://vitejs.dev/guide/build.html)
- [Vue Router部署](https://router.vuejs.org/guide/essentials/history-mode.html)

---

**配置完成**: 2026-03-09
**部署状态**: 待部署
**下一步**: 运行 `./deploy-frontend.sh` 开始部署
