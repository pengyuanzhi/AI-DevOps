# 文档归档 (Archive)

本目录存放项目的所有总结性、报告类文档。

---

## 📋 文档索引

### 2026-03-09

1. **[E2E_TEST_RESULTS.md](2026-03-09_E2E_TEST_RESULTS.md)**
   - 端到端测试结果报告
   - 5个测试场景，20%通过率
   - 验证核心功能工作正常

2. **[PIPELINE_MAINTENANCE_SUMMARY.md](PIPELINE_MAINTENANCE_SUMMARY.md)**
   - 自主流水线维护功能总结
   - 8个核心服务模块
   - 完整的API文档

3. **[PIPELINE_MAINTENANCE_TEST_SUMMARY.md](PIPELINE_MAINTENANCE_TEST_SUMMARY.md)**
   - 自主流水线维护测试总结
   - 32个测试用例
   - 测试覆盖率分析

4. **[LLM_SERVICE_FIX_SUMMARY.md](LLM_SERVICE_FIX_SUMMARY.md)**
   - LLM服务集成修复总结
   - 解决导入错误问题
   - 测试通过率75%

5. **[PROJECT_STATUS_REPORT.md](PROJECT_STATUS_REPORT.md)**
   - 项目状态报告
   - 4个高优先级功能分析
   - 实施计划

6. **[API_ENDPOINT_COMPLETION_REPORT.md](API_ENDPOINT_COMPLETION_REPORT.md)**
   - API端点完成报告
   - FastAPI路由实现
   - 数据模型定义

7. **[BUILD_ENGINE_PHASE1_SUMMARY.md](BUILD_ENGINE_PHASE1_SUMMARY.md)**
   - 构建引擎阶段1总结
   - 执行器框架实现

8. **[BUILD_ENGINE_PHASE2_SUMMARY.md](BUILD_ENGINE_PHASE2_SUMMARY.md)**
   - 构建引擎阶段2总结
   - CMake集成

9. **[BUILD_ENGINE_PHASE4_SUMMARY.md](BUILD_ENGINE_PHASE4_SUMMARY.md)**
   - 构建引擎阶段4总结
   - QMake集成

10. **[SMART_TEST_SELECTION_SUMMARY.md](SMART_TEST_SELECTION_SUMMARY.md)**
    - 智能测试选择总结
    - 依赖分析实现

11. **[TEST_ENGINE_SUMMARY.md](TEST_ENGINE_SUMMARY.md)**
    - 测试引擎总结
    - 测试执行器实现

12. **[SESSION_SUMMARY.md](SESSION_SUMMARY.md)**
    - 会话总结
    - 开发进展记录

---

## 📁 文档分类

### 功能总结

- `PIPELINE_MAINTENANCE_SUMMARY.md` - 自主流水线维护
- `SMART_TEST_SELECTION_SUMMARY.md` - 智能测试选择
- `BUILD_ENGINE_*_SUMMARY.md` - 构建引擎
- `TEST_ENGINE_SUMMARY.md` - 测试引擎

### 测试报告

- `PIPELINE_MAINTENANCE_TEST_SUMMARY.md`
- `E2E_TEST_RESULTS.md`

### 修复总结

- `LLM_SERVICE_FIX_SUMMARY.md`
- `API_ENDPOINT_COMPLETION_REPORT.md`

### 项目状态

- `PROJECT_STATUS_REPORT.md`
- `SESSION_SUMMARY.md`

---

## 🔍 搜索文档

### 按关键词搜索

```bash
# 在归档目录中搜索
cd docs/archive
grep -r "keyword" *.md

# 查找特定类型
ls -1 | grep SUMMARY
ls -1 | grep TEST
ls -1 | grep REPORT
```

### 按日期查找

```bash
# 查找今天的文档
ls -1 | grep "2026-03-09"

# 按日期排序
ls -1t | head -10
```

---

## 📝 创建新文档

### 命名规范

使用日期前缀和描述性名称：

```bash
# 格式: YYYY-MM-DD_描述性名称_类型.md
2026-03-09_PIPELINE_MAINTENANCE_SUMMARY.md
2026-03-09_E2E_TEST_RESULTS.md
2026-03-09_LLM_SERVICE_FIX_SUMMARY.md
```

### 文档模板

```markdown
# [标题]

**日期**: YYYY-MM-DD
**状态**: ✅ 完成 / ⏳ 进行中
**功能**: [功能描述]

---

## 概述

[简要描述]

## 完成的工作

1. ...
2. ...

## 结果

...

## 下一步

...

---

**创建时间**: YYYY-MM-DD
**版本**: 1.0.0
```

---

## 🗂️ 归档策略

### 保留期限

- **活跃开发** (最近3个月): 保留所有文档
- **近期** (3-6个月): 保留总结文档
- **长期** (6个月以上): 保留重要里程碑文档

### 清理规则

每季度清理一次：
- 删除重复文档
- 合并相似文档
- 压缩旧日志

---

## 🔗 相关文档

- [../README.md](../README.md) - 文档导航
- [../user-guide/](../user-guide/) - 用户指南
- [../api/](../api/) - API文档

---

**最后更新**: 2026-03-09
**维护者**: AI-CICD Team
