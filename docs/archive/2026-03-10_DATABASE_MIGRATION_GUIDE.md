# 数据库迁移指南

本文档说明如何应用数据库迁移来更新Schema。

---

## 📋 最新迁移

### 003_add_cache_fields_to_jobs.py

**日期**: 2026-03-10
**描述**: 添加构建缓存相关字段到jobs表

**变更**:
- ✅ 添加 `cached` 字段 (Boolean) - 标识是否来自缓存
- ✅ 添加 `cache_key` 字段 (String(255)) - 存储缓存键
- ✅ 为 `cache_key` 创建索引

**原因**: 支持构建缓存功能，跟踪哪些构建来自缓存

---

## 🚀 应用迁移

### 方法1: 使用Alembic命令（推荐）

```bash
# 激活虚拟环境
source venv/bin/activate

# 查看当前迁移状态
alembic current

# 查看迁移历史
alembic history

# 应用所有待处理的迁移
alembic upgrade head

# 应用特定迁移
alembic upgrade 003_add_cache_fields
```

### 方法2: 手动执行SQL

**PostgreSQL**:
```sql
-- 添加 cached 字段
ALTER TABLE jobs ADD COLUMN cached BOOLEAN NOT NULL DEFAULT false;

-- 添加 cache_key 字段
ALTER TABLE jobs ADD COLUMN cache_key VARCHAR(255);

-- 创建索引
CREATE INDEX ix_jobs_cache_key ON jobs(cache_key);
```

---

## 🔍 验证迁移

### 检查表结构

```bash
# 使用psql
psql -U your_user -d ai_cicd

# 查看jobs表结构
\d jobs

# 查看索引
\di ix_jobs_cache_key
```

### 使用Python验证

```python
from src.db.session import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('jobs')

for column in columns:
    print(f"{column['name']}: {column['type']}")

# 应该包含 cached 和 cache_key 字段
```

---

## ⚠️ 回滚迁移

如果需要回滚此迁移：

```bash
# 回滚到上一版本
alembic downgrade -1

# 或回滚到特定版本
alembic downgrade 002_add_celery_task_id
```

**手动回滚SQL**:
```sql
-- 删除索引
DROP INDEX IF EXISTS ix_jobs_cache_key;

-- 删除字段
ALTER TABLE jobs DROP COLUMN IF EXISTS cache_key;
ALTER TABLE jobs DROP COLUMN IF EXISTS cached;
```

---

## 📊 迁移历史

| 版本 | 描述 | 日期 |
|------|------|------|
| 001_initial | 初始Schema | 2026-03-09 |
| 002_add_celery_task_id | 添加Celery任务ID | 2026-03-09 |
| 003_add_cache_fields | 添加缓存字段 | 2026-03-10 |

---

## 🐛 故障排除

### 问题1: 迁移失败

**错误**: `alembic.util.exc.CommandError: Target database is not up to date`

**解决**:
```bash
# 查看当前版本
alembic current

# 强制标记为特定版本（谨慎使用）
alembic stamp 002_add_celery_task_id

# 然后重新应用迁移
alembic upgrade head
```

### 问题2: 字段已存在

**错误**: `Column 'cached' already exists`

**解决**: 检查是否已经手动添加了字段
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'jobs';
```

如果字段已存在，标记迁移为完成：
```bash
alembic stamp head
```

### 问题3: 权限不足

**错误**: `permission denied to create index`

**解决**: 确保数据库用户有CREATE权限
```sql
GRANT CREATE ON DATABASE ai_cicd TO your_user;
GRANT ALL PRIVILEGES ON TABLE jobs TO your_user;
```

---

## 🔧 开发环境设置

### 首次设置

1. **初始化数据库**:
```bash
# 创建数据库
createdb ai_cicd

# 运行所有迁移
alembic upgrade head
```

2. **验证Schema**:
```python
from src.db.models import Job

# 检查Job模型是否有cached和cache_key字段
print(Job.cached)
print(Job.cache_key)
```

---

## 📝 下一步

迁移应用后，需要在代码中更新构建逻辑以使用这些字段：

1. **设置缓存键**: 在构建前计算cache_key
2. **检查缓存**: 查询cache_key是否已存在
3. **标记缓存命中**: 设置cached=True
4. **保存缓存记录**: 保存成功的构建

参考: `src/services/build/executor.py` 中的缓存实现

---

**创建时间**: 2026-03-10
**维护者**: AI-CICD Team
