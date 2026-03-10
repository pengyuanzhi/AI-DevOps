# Docker 构建和部署指南

## 📦 Dockerfile 文件说明

### 后端

| 文件 | 用途 | 特点 |
|------|------|------|
| `Dockerfile` | 生产环境 | 多阶段构建、gunicorn、最小镜像、包含 C/C++ 工具 |
| `Dockerfile.dev` | 开发环境 | 单阶段、热重载、开发工具 |

### 前端

| 文件 | 用途 | 特点 |
|------|------|------|
| `frontend/Dockerfile` | 生产环境 | 多阶段构建、nginx、静态文件服务 |
| `frontend/nginx.conf` | Nginx 配置 | 反向代理、缓存、SPA 支持 |

---

## 🏗️ 构建镜像

### 本地构建

```bash
# 后端（生产环境）
docker build -t ai-cicd-backend:latest .

# 后端（开发环境）
docker build -f Dockerfile.dev -t ai-cicd-backend:dev .

# 前端
docker build -t ai-cicd-frontend:latest ./frontend/

# 查看镜像大小
docker images | grep ai-cicd
```

### 多架构构建（可选）

```bash
# 启用 buildx
docker buildx create --name multiarch --use

# 构建 amd64 和 arm64
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ai-cicd-backend:latest .
```

---

## 🚀 部署模式

### 1. 开发模式（推荐本地开发）

```bash
# 使用开发配置（支持热重载）
docker compose -f docker-compose.yml up -d

# 查看日志
docker compose logs -f backend

# 停止服务
docker compose down
```

**特点：**
- ✅ 代码修改自动重载
- ✅ 完整的调试日志
- ✅ 挂载本地代码目录

### 2. 生产模式（推荐生产环境）

```bash
# 创建生产环境配置
cp .env.example .env.prod
nano .env.prod

# 使用生产配置部署
docker compose -f docker-compose.prod.yml up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 扩展服务
docker compose -f docker-compose.prod.yml up -d --scale backend=3
```

**特点：**
- ✅ 多副本部署
- ✅ 资源限制
- ✅ 自动重启
- ✅ 健康检查
- ✅ 监控集成（可选）

### 3. 混合模式（前后端分离）

```bash
# 只启动后端
docker compose up -d postgres redis rabbitmq backend celery-worker

# 前端单独部署（例如：CDN、独立服务器）
cd frontend
docker build -t ai-cicd-frontend:latest .
docker run -d -p 80:80 ai-cicd-frontend:latest
```

---

## 🔧 环境变量配置

### 必需变量（生产环境）

```bash
# 数据库
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_PASSWORD=your_redis_password

# RabbitMQ
RABBITMQ_PASSWORD=your_rabbitmq_password

# LLM API（至少一个）
ANTHROPIC_API_KEY=your_anthropic_key
# 或
ZHIPU_API_KEY=your_zhipu_key
```

### 可选变量

```bash
# Docker 镜像仓库
DOCKER_REGISTRY=your-registry.com/

# 镜像版本
VERSION=v1.0.0

# 资源限制
WORKERS=4
CELERY_CONCURRENCY=4

# 日志级别
LOG_LEVEL=INFO
```

---

## 📊 生产环境检查清单

### 部署前检查

- [ ] 修改所有默认密码
- [ ] 配置 HTTPS/SSL 证书
- [ ] 设置防火墙规则（只开放必要端口）
- [ ] 配置日志收集
- [ ] 设置监控告警
- [ ] 配置数据库备份
- [ ] 测试健康检查端点

### 部署后验证

```bash
# 1. 检查服务状态
docker compose -f docker-compose.prod.yml ps

# 2. 检查健康检查
curl http://localhost/health
curl http://localhost:8000/health

# 3. 检查日志
docker compose -f docker-compose.prod.yml logs backend

# 4. 检查资源使用
docker stats

# 5. 运行测试
./scripts/run-integration-tests.sh integration
```

---

## 🔄 更新和维护

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker compose -f docker-compose.prod.yml build

# 滚动更新（零停机）
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend

# 更新所有服务
docker compose -f docker-compose.prod.yml up -d
```

### 数据备份

```bash
# 备份 PostgreSQL
docker compose exec postgres pg_dump -U ai_cicd ai_cicd > backup_$(date +%Y%m%d).sql

# 备份 Redis
docker compose exec redis redis-cli BGSAVE
docker cp ai-cicd-redis:/data/dump.rdb redis_backup_$(date +%Y%m%d).rdb
```

### 日志管理

```bash
# 查看最近日志
docker compose logs --tail=100 backend

# 实时日志
docker compose logs -f backend

# 清理日志（如果日志文件过大）
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

---

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细错误
docker compose logs backend

# 进入容器调试
docker compose exec backend /bin/bash

# 检查健康状态
docker inspect ai-cicd-backend-prod | grep -A 10 Health
```

### 镜像过大

```bash
# 查看镜像层
docker history ai-cicd-backend:latest

# 清理未使用的镜像
docker image prune -a

# 使用多阶段构建减小镜像大小
```

### 网络问题

```bash
# 检查网络
docker network ls
docker network inspect ai-cicd-network

# 重建网络
docker compose down
docker compose up -d
```

### 性能问题

```bash
# 查看资源使用
docker stats

# 调整资源限制（docker-compose.prod.yml）
deploy:
  resources:
    limits:
      memory: 4G
```

---

## 📈 监控和日志（可选）

### 启用 Prometheus + Grafana

```bash
# 启动监控服务
docker compose -f docker-compose.prod.yml --profile monitoring up -d

# 访问
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### 配置日志收集

```bash
# 使用 ELK 或 Loki 收集日志
# 修改 docker-compose.prod.yml 添加日志驱动
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 🔐 安全加固

### 1. 使用非 root 用户（已配置）

所有容器都使用非 root 用户运行。

### 2. 网络隔离

```bash
# 创建隔离网络
docker network create --driver bridge --subnet=172.20.0.0/16 ai-cicd-internal

# 只暴露必要端口
# 前端: 80, 443
# 后端: 不对外暴露（通过 nginx 反向代理）
```

### 3. 镜像安全扫描

```bash
# 使用 Trivy 扫描漏洞
trivy image ai-cicd-backend:latest

# 使用 Docker Scout
docker scout quickview ai-cicd-backend:latest
```

### 4. 定期更新

```bash
# 更新基础镜像
docker compose pull
docker compose build --no-cache
docker compose up -d
```

---

## 📚 相关文档

- [ENVIRONMENT_SETUP.md](./docs/ENVIRONMENT_SETUP.md) - 环境搭建
- [QUICKSTART.md](./QUICKSTART.md) - 快速参考
- [DOCKER_STARTUP_GUIDE.md](./DOCKER_STARTUP_GUIDE.md) - Docker 详细说明

---

## 💡 最佳实践

1. **使用多阶段构建** - 减小镜像大小
2. **非 root 用户运行** - 提高安全性
3. **健康检查** - 自动恢复故障
4. **资源限制** - 防止资源耗尽
5. **日志管理** - 避免日志文件过大
6. **定期备份** - 数据安全
7. **监控告警** - 及时发现问题
8. **滚动更新** - 零停机部署

---

**提示:** 生产环境务必使用 `docker-compose.prod.yml` 并配置所有必需的环境变量！
