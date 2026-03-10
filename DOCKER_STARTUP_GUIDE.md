# AI-CICD Platform Docker 启动指南

**文档版本**: v1.0
**创建日期**: 2026-03-09
**适用环境**: Linux/WSL2 + Docker Compose v2

---

## 📋 前置要求

### 系统要求

- **操作系统**: Linux (Ubuntu 20.04+) 或 WSL2
- **Docker**: 20.10+
- **Docker Compose**: v2.0+
- **内存**: 至少 4GB RAM
- **磁盘**: 至少 10GB 可用空间

### 检查环境

```bash
# 检查Docker版本
docker --version

# 检查Docker Compose版本
docker compose version

# 检查Python版本 (本地开发)
python3 --version
```

---

## 🔧 Docker权限配置

### 问题：permission denied

如果运行`docker ps`时遇到权限错误：

```
permission denied while trying to connect to the Docker daemon socket
```

### 解决方案1：将用户添加到docker组（推荐）

```bash
# 1. 将当前用户添加到docker组
sudo usermod -aG docker $USER

# 2. 刷新组权限（需要重新登录或执行）
newgrp docker

# 3. 验证
docker ps
```

**注意**: 如果使用WSL2，需要在Windows上重启WSL：

```powershell
# 在PowerShell中执行
wsl --shutdown
# 然后重新打开WSL终端
```

### 解决方案2：使用sudo（临时方案）

如果不想配置用户组，可以在所有docker命令前加sudo：

```bash
sudo docker compose up -d
```

---

## 📝 环境变量配置

### 1. 复制环境变量模板

```bash
cd /home/kerfs/AI-CICD-new
cp .env.example .env
```

### 2. 编辑.env文件

**必需配置** (修改以下值):

```bash
# LLM API配置 (至少配置一个)
ANTHROPIC_API_KEY=your_actual_anthropic_key_here
ZHIPU_API_KEY=your_actual_zhipu_key_here

# GitLab配置 (如果需要GitLab集成)
GITLAB_TOKEN=your_actual_gitlab_token_here
GITLAB_WEBHOOK_SECRET=your_random_secret_string

# 数据库密码 (生产环境请修改)
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_secure_redis_password
```

**可选配置** (使用默认值即可):

```bash
# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
WORKERS=4

# 日志配置
LOG_LEVEL=INFO
DEBUG=false

# 环境配置
ENVIRONMENT=development
```

### 3. 获取API密钥

**Anthropic Claude API**:
1. 访问 https://console.anthropic.com/
2. 注册/登录
3. 创建API密钥
4. 复制密钥到`ANTHROPIC_API_KEY`

**智谱AI API**:
1. 访问 https://open.bigmodel.cn/
2. 注册/登录
3. 创建API密钥
4. 复制密钥到`ZHIPU_API_KEY`

**GitLab Token** (可选):
1. 登录GitLab
2. Settings → Access Tokens
3. 创建Personal Access Token
4. 复制token到`GITLAB_TOKEN`

---

## 🚀 启动步骤

### 步骤1：构建并启动所有服务

```bash
cd /home/kerfs/AI-CICD-new

# 构建镜像并启动服务（后台运行）
docker compose up -d --build

# 查看日志
docker compose logs -f

# 只查看主应用日志
docker compose logs -f ai-cicd
```

**预期输出**:

```
[+] Running 7/7
 ✔ Network ai-cicd-network      Created
 ✔ Volume "postgres_data"       Created
 ✔ Volume "redis_data"          Created
 ✔ Container ai-cicd-postgres   Started
 ✔ Container ai-cicd-redis      Started
 ✔ Container ai-cicd-rabbitmq   Started
 ✔ Container ai-cicd            Started
 ✔ Container celery-worker      Started
 ✔ Container celery-beat        Started
```

### 步骤2：等待服务健康检查

所有服务都有健康检查，等待1-2分钟让服务完全启动：

```bash
# 查看容器状态
docker compose ps

# 预期输出中所有服务状态应为 "Up (healthy)"
```

### 步骤3：执行数据库迁移

```bash
# 等待PostgreSQL完全启动后执行
docker compose exec ai-cicd alembic upgrade head

# 预期输出:
# Running upgrade  -> 001_initial_schema
```

### 步骤4：验证服务

```bash
# 1. 检查API健康状态
curl http://localhost:8000/health

# 预期输出:
# {"status":"healthy","version":"0.2.0"}

# 2. 访问API文档
# 在浏览器中打开: http://localhost:8000/docs

# 3. 检查所有容器状态
docker compose ps
```

---

## 🛑 停止和清理

### 停止服务

```bash
# 停止所有服务（保留数据）
docker compose stop

# 停止并删除容器（保留数据）
docker compose down

# 停止并删除容器和数据卷（警告：会删除所有数据）
docker compose down -v
```

### 查看日志

```bash
# 实时查看所有日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f ai-cicd
docker compose logs -f celery-worker

# 查看最近100行日志
docker compose logs --tail=100
```

### 重启服务

```bash
# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart ai-cicd
```

---

## 🔍 故障排查

### 问题1：容器启动失败

**症状**: `docker compose ps` 显示容器状态为 `Exited`

**解决步骤**:

```bash
# 1. 查看容器日志
docker compose logs ai-cicd

# 2. 常见原因：
#    - 端口冲突（8000端口被占用）
#    - 环境变量配置错误
#    - 依赖服务未就绪

# 3. 检查端口占用
sudo netstat -tulpn | grep :8000

# 4. 如果端口冲突，修改docker-compose.yml中的端口映射
#    ports:
#      - "8001:8000"  # 使用8001端口
```

### 问题2：数据库连接失败

**症状**: 日志显示 `connection refused` 或 `could not connect to server`

**解决步骤**:

```bash
# 1. 确认PostgreSQL容器健康
docker compose ps postgres

# 2. 查看PostgreSQL日志
docker compose logs postgres

# 3. 手动测试连接
docker compose exec postgres psql -U ai_cicd -d ai_cicd

# 4. 重新执行数据库迁移
docker compose exec ai-cicd alembic upgrade head
```

### 问题3：健康检查失败

**症状**: 容器状态显示 `Up (unhealthy)`

**解决步骤**:

```bash
# 1. 查看健康检查日志
docker inspect --format='{{json .State.Health}}' ai-cicd-postgres | jq

# 2. 手动执行健康检查命令
docker compose exec ai-cicd curl -f http://localhost:8000/health

# 3. 查看应用日志
docker compose logs ai-cicd --tail=50
```

### 问题4：权限问题（文件写入）

**症状**: 日志显示 `Permission denied` 写入 `/app/data` 或 `/app/logs`

**解决步骤**:

```bash
# 1. 在宿主机创建目录并设置权限
sudo mkdir -p /home/kerfs/AI-CICD-new/data
sudo mkdir -p /home/kerfs/AI-CICD-new/logs
sudo chown -R $USER:$USER /home/kerfs/AI-CICD-new/data
sudo chown -R $USER:$USER /home/kerfs/AI-CICD-new/logs

# 2. 或者修改docker-compose.yml中的volumes配置
#    使用绝对路径而不是相对路径
```

### 问题5：镜像构建失败

**症状**: `docker compose build` 失败

**解决步骤**:

```bash
# 1. 清理Docker缓存重新构建
docker compose build --no-cache

# 2. 如果网络问题，使用国内镜像源
#    在Dockerfile中添加：
#    RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 检查requirements.txt中的包版本是否冲突
pip install --dry-run -r requirements.txt
```

---

## 📊 服务端口说明

启动后，以下端口将被占用：

| 服务 | 端口 | 用途 |
|------|------|------|
| **AI-CICD API** | 8000 | 主API服务 |
| **PostgreSQL** | 5432 | 数据库 |
| **Redis** | 6379 | 缓存 |
| **RabbitMQ** | 5672 | 消息队列AMQP |
| **RabbitMQ Management** | 15672 | Web管理界面 |

**访问地址**:
- API文档: http://localhost:8000/docs
- API Redoc: http://localhost:8000/redoc
- RabbitMQ管理界面: http://localhost:15672 (guest/guest)

---

## 🔐 生产环境配置

### 安全建议

1. **修改默认密码**:
   ```bash
   # .env文件
   POSTGRES_PASSWORD=your_strong_password_here
   REDIS_PASSWORD=your_strong_redis_password
   RABBITMQ_PASSWORD=your_strong_rabbitmq_password
   ```

2. **配置HTTPS** (使用Nginx反向代理):
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **限制容器资源** (在docker-compose.yml中):
   ```yaml
   services:
     ai-cicd:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 2G
           reservations:
             cpus: '1'
             memory: 1G
   ```

4. **配置防火墙**:
   ```bash
   # 只开放必要的端口
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

---

## 📈 监控和维护

### 查看资源使用

```bash
# 查看容器资源使用情况
docker stats

# 查看磁盘使用
docker system df

# 清理未使用的资源
docker system prune -a
```

### 备份数据

```bash
# 备份PostgreSQL数据库
docker compose exec postgres pg_dump -U ai_cicd ai_cicd > backup_$(date +%Y%m%d).sql

# 备份Redis数据
docker compose exec redis redis-cli --rdb /data/dump.rdb BGSAVE

# 备份数据卷
docker run --rm -v ai-cicd-postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

### 日志管理

```bash
# 清理旧日志
docker compose logs --since 24h > logs_$(date +%Y%m%d).log

# 配置日志轮转（在docker-compose.yml中）
services:
   ai-cicd:
     logging:
       driver: "json-file"
       options:
         max-size: "10m"
         max-file: "3"
```

---

## 🎯 下一步

服务启动成功后：

1. ✅ 访问 http://localhost:8000/docs 查看API文档
2. ✅ 测试API端点可用性
3. ✅ 启动前端开发服务器
4. ✅ 进行前后端集成测试
5. ✅ 配置GitLab Webhook（如需要）

---

## 📞 获取帮助

如果遇到问题：

1. 查看容器日志: `docker compose logs -f`
2. 检查容器状态: `docker compose ps`
3. 查看文档:
   - API文档: http://localhost:8000/docs
   - 项目文档: `/home/kerfs/AI-CICD-new/*.md`
4. 检查系统资源: `docker stats`

---

**文档版本**: v1.0
**最后更新**: 2026-03-09
**适用项目**: AI-CICD Platform v0.2.0
