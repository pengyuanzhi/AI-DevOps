# AI-CICD Project 清理计划

**创建日期**: 2026-03-09
**目的**: 清理不必要的文件，优化项目结构

---

## 📊 发现的问题

### 1. Python缓存文件
- **35个** `__pycache__` 目录
- **124个** `.pyc` 文件
- **影响**: 增加仓库大小，不应该提交到git

### 2. 重复的node_modules
- **根目录node_modules**: 170MB
- **问题**: 根目录的package.json只包含前端依赖，这些依赖应该在frontend/node_modules中
- **建议**: 删除根目录的node_modules和package-lock.json

### 3. 构建产物
- `frontend/dist/` - 前端构建产物
- **影响**: 应该被gitignore，但实际存在

### 4. 运行时数据
- `data/ai_cicd.db` (319KB SQLite数据库)
- `data/cache/*`
- `data/generated/*`
- `logs/*.log`
- **影响**: 运行时生成的数据，不应该提交到git

### 5. 测试缓存
- `.pytest_cache/`
- `frontend/.pytest_cache/`
- **影响**: 测试缓存，不应该提交到git

### 6. 重复文档
发现多个会话总结文档：
- `SESSION_SUMMARY.md`
- `SESSION_SUMMARY_2026_03_09_PART2.md`
- `SESSION_UPDATE_2026_03_09.md`
- `PROGRESS_REPORT.md`
- `INTEGRATION_TEST_SUMMARY.md`
- `DOCKER_FIX.md`

**建议**: 整合为一个主文档，旧的移动到docs/archive/

---

## 🧹 清理方案

### 立即清理（推荐）

```bash
cd /home/kerfs/AI-CICD-new

# 运行清理脚本
./cleanup.sh
```

### 手动清理

#### 1. 清理Python缓存
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

#### 2. 删除根目录node_modules
```bash
rm -rf node_modules
rm -f package-lock.json
```

#### 3. 清理构建产物
```bash
rm -rf frontend/dist
```

#### 4. 清理运行时数据
```bash
rm -rf data/cache/*
rm -rf data/generated/*
rm -rf data/*.db
rm -rf logs/*.log
```

#### 5. 清理测试缓存
```bash
rm -rf .pytest_cache
rm -rf frontend/.pytest_cache
```

#### 6. 整合文档
```bash
mkdir -p docs/archive
mv SESSION_SUMMARY_2026_03_09_PART2.md docs/archive/
mv SESSION_UPDATE_2026_03_09.md docs/archive/
mv PROGRESS_REPORT.md docs/archive/
mv INTEGRATION_TEST_SUMMARY.md docs/archive/
mv DOCKER_FIX.md docs/archive/
```

---

## 📋 清理后的目录结构

```
AI-CICD-new/
├── .git/                    # Git仓库
├── .github/                 # GitHub配置
├── alembic/                 # 数据库迁移
├── configs/                 # 配置文件
├── docs/                    # 文档
│   └── archive/            # 归档的旧文档
├── examples/                # 示例项目
│   └── cpp-calculator/
├── frontend/                # 前端项目
│   ├── src/
│   ├── public/
│   ├── node_modules/       # 保留
│   ├── dist/               # 清理
│   └── ...
├── k8s/                     # Kubernetes配置
├── prompts/                 # AI提示模板
├── scripts/                 # 脚本工具
├── src/                     # 后端源码
│   ├── api/
│   ├── cache/
│   ├── core/
│   ├── db/
│   ├── integrations/
│   ├── message_queue/
│   ├── middleware/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── tasks/
│   └── utils/
├── static/                  # 静态文件
├── tests/                   # 测试
│   ├── integration/
│   └── unit/
├── data/                    # 运行时数据（清空内容）
├── logs/                    # 日志（清空内容）
├── cleanup.sh               # 清理脚本
├── start.sh                 # 启动脚本
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .gitignore
├── .env.example
└── 核心文档...              # 保留重要文档
```

---

## 🎯 预期效果

### 清理前
- Python缓存: 124个.pyc文件
- node_modules: 170MB（根目录）+ frontend/node_modules
- 构建产物: frontend/dist
- 运行时数据: data/*.db, logs/*.log
- 测试缓存: .pytest_cache

### 清理后
- ✅ 无Python缓存文件
- ✅ 删除170MB重复的node_modules
- ✅ 清理所有构建产物
- ✅ 清理运行时数据
- ✅ 清理测试缓存
- ✅ 文档整合到docs/archive/

---

## ⚠️ 注意事项

### 不要删除的文件/目录

1. **frontend/node_modules** - 前端依赖，需要保留
2. **.env** - 环境变量配置（如果存在）
3. **源代码** - src/, frontend/src/
4. **配置文件** - docker-compose.yml, Dockerfile等
5. **重要文档** - README.md, FEATURES.md等
6. **数据库迁移** - alembic/versions/

### 提交前检查

```bash
# 查看更改
git status

# 查看文件大小变化
du -sh .

# 确认.gitignore正确配置
cat .gitignore | grep -E "(node_modules|__pycache__|dist|\.pyc|data/|logs/)"
```

---

## 📈 后续维护

### 定期清理

建议定期运行清理脚本：

```bash
# 每周清理一次
./cleanup.sh
```

### 预防措施

1. **更新.gitignore**
   - 确保所有临时文件都被忽略
   - 添加常见临时文件模式

2. **Git hooks**
   - 添加pre-commit hook检查临时文件
   - 自动运行清理脚本

3. **文档管理**
   - 及时归档旧文档
   - 保持根目录文档精简

---

**清理脚本**: `cleanup.sh`
**执行方式**: `./cleanup.sh`
**预计节省空间**: ~200MB
