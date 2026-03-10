# Docker构建修复说明

**问题**: `psycopg2-binary`在Python 3.13中需要PostgreSQL开发库

**已修复**:
1. ✅ 在Dockerfile中添加了`libpq-dev`和`build-essential`
2. ✅ 将`psycopg2-binary`替换为`psycopg[binary]==3.2.3`（更现代的版本）

**重新执行**:
```bash
cd /home/kerfs/AI-CICD-new

# 清理旧镜像
docker compose down
docker system prune -f

# 重新构建并启动
./start.sh
```

如果还有错误，可以手动构建查看详细日志：
```bash
docker compose build --no-cache ai-cicd
```
