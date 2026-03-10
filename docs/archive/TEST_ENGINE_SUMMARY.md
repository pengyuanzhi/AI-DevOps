# 测试执行引擎实施总结

**日期**: 2026-03-09
**状态**: ✅ 完成
**阶段**: 测试执行引擎完整实现

---

## 完成的工作

### 1. 测试发现器 ✅

**文件**: `src/services/test/discovery.py`

**核心功能**:
- 自动发现项目中的测试用例
- 支持3种测试框架：
  - Qt Test (`--datatags`)
  - Google Test (`--gtest_list_tests`)
  - Catch2 (`--list-tests`)
- 智能框架检测
- 从源码解析测试用例（Qt Test）

**主要类**:

#### `TestFramework` (Enum)
```python
class TestFramework(str, Enum):
    QT_TEST = "qttest"
    GOOGLE_TEST = "googletest"
    CATCH2 = "catch2"
    UNKNOWN = "unknown"
```

#### `TestBinary` (Dataclass)
- 表示测试可执行文件
- 包含框架类型、测试用例列表
- 支持元数据扩展

#### `TestDiscoveryService`
**核心方法**:
- `discover_tests()` - 发现所有测试用例
- `_find_test_binaries()` - 查找测试可执行文件
- `_detect_framework()` - 检测测试框架
- `_list_tests_from_binary()` - 列出测试用例

**特性**:
- ✅ 自动框架检测
- ✅ 多框架支持
- ✅ 源码解析（Qt Test）
- ✅ 可执行文件识别

---

### 2. 测试注册中心 ✅

**文件**: `src/services/test/registry.py`

**核心功能**:
- 管理项目中所有测试用例的元数据
- 支持测试优先级、标签、依赖关系
- 统计测试历史数据
- 不稳定测试检测

**主要类**:

#### `TestPriority` (Enum)
```python
class TestPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
```

#### `TestMetadata` (Dataclass)
- 测试ID、名称、套件、文件、行号
- 执行信息（状态、运行时间、平均耗时）
- 优先级和标签
- 依赖关系
- 统计信息（总运行数、通过数、失败数、不稳定次数）
- 覆盖率信息（源文件列表）

**属性**:
- `pass_rate` - 通过率
- `is_flaky` - 是否不稳定
- `is_slow` - 是否慢速（>1秒）

#### `TestRegistry`
**核心方法**:
- `register_test()` - 注册单个测试
- `register_suite()` - 注册测试套件
- `get_test()` - 获取测试元数据
- `get_tests_by_suite()` - 按套件获取
- `get_tests_by_tag()` - 按标签获取
- `get_tests_by_priority()` - 按优先级获取
- `get_tests_by_source()` - 按源文件获取（影响分析）
- `update_test_result()` - 更新测试结果
- `find_tests_to_run()` - 查找需要运行的测试
- `get_statistics()` - 获取统计信息

**特性**:
- ✅ 持久化存储（JSON）
- ✅ 多索引支持（套件、标签、优先级、源文件）
- ✅ 统计信息自动更新
- ✅ 不稳定测试检测
- ✅ EMA平均执行时间

#### `TestRegistryManager`
- 管理多个项目的测试注册中心
- 单例模式

---

### 3. 测试执行器 ✅

**文件**:
- `src/services/test/gtest_executor.py` - Google Test执行器
- `src/services/test/catch2_executor.py` - Catch2执行器

**Google Test执行器**:
- 支持 `--gtest_list_tests` 列出测试
- 支持 `--gtest_filter` 过滤测试
- 支持 `--gtest_output=xml` XML输出
- 支持文本输出解析

**Catch2执行器**:
- 支持 `--list-tests` 列出测试
- 支持 `--reporter=json` JSON输出
- 支持文本输出解析
- 支持颜色和执行时间显示

**共同特性**:
- ✅ 异步执行
- ✅ 超时控制
- ✅ 覆盖率收集（gcov）
- ✅ 详细的错误信息
- ✅ 测试用例级别的时间统计

---

### 4. 测试结果收集器 ✅

**文件**: `src/services/test/result_collector.py`

**核心功能**:
- 收集测试结果
- 聚合统计数据
- 生成测试报告
- 比较多次运行

**主要类**:

#### `TestRunSummary` (Dataclass)
- 运行ID、项目ID、流水线ID、作业ID
- 时间信息（开始、结束、持续时间）
- 统计信息（套件数、测试数、通过/失败/跳过数）
- 状态
- 失败详情列表
- 覆盖率
- 输出

**方法**:
- `to_dict()` - 转换为字典

#### `TestResultCollector`
**核心方法**:
- `collect_result()` - 收集测试结果
- `get_summary()` - 获取运行摘要
- `save_summary()` - 保存摘要到文件
- `compare_runs()` - 比较两次运行
- `get_statistics()` - 获取统计信息

**特性**:
- ✅ 自动更新测试注册中心
- ✅ JSON和文本报告生成
- ✅ 运行对比功能
- ✅ 多项目统计

---

### 5. 代码覆盖率收集器 ✅

**文件**: `src/services/test/coverage.py`

**核心功能**:
- 使用gcov收集覆盖率数据
- 使用lcov生成HTML报告
- 解析覆盖率数据
- 快速覆盖率查询

**主要类**:

#### `CoverageData` (Dataclass)
- 文件路径
- 行覆盖率（总数/覆盖数/百分比）
- 分支覆盖率
- 函数覆盖率

#### `CoverageReport` (Dataclass)
- 总体统计（行/分支/函数）
- 按文件统计
- 未覆盖的行列表

**方法**:
- `add_file()` - 添加文件覆盖率数据
- 自动计算总体统计

#### `CoverageCollector`
**核心方法**:
- `collect_coverage()` - 收集完整覆盖率
- `get_quick_coverage()` - 快速获取总体覆盖率
- `_run_gcov()` - 运行gcov
- `_parse_gcov_file()` - 解析gcov文件
- `_generate_lcov_report()` - 生成lcov报告
- `format_coverage_report()` - 格式化报告

**特性**:
- ✅ gcov和lcov集成
- ✅ HTML报告生成
- ✅ 详细覆盖率统计
- ✅ 未覆盖行追踪
- ✅ 工具可用性检查

---

### 6. Celery测试任务 ✅

**文件**: `src/tasks/test_tasks.py`

**任务列表**:

#### `execute_test`
- 执行测试的主要任务
- 支持重试（最多3次）
- 实时进度更新
- 自动测试发现和注册
- 日志流集成

**参数**:
```python
{
    "project_id": int,
    "pipeline_id": str,
    "job_id": str,
    "test_config": {
        "build_dir": str,
        "source_dir": str,
        "test_type": str,
        "test_filter": str,
        "parallel_jobs": int,
        "timeout": int,
        "enable_coverage": bool,
        "environment": dict,
    },
    "project_path": str,
}
```

**返回**:
```python
{
    "status": str,  # success/failed
    "total_tests": int,
    "passed_tests": int,
    "failed_tests": int,
    "skipped_tests": int,
    "coverage_percent": float,
    "duration": float,
    "stdout": str,
    "stderr": str,
    "started_at": str,
    "finished_at": str,
    "run_id": str,
}
```

#### `discover_tests`
- 发现测试用例任务
- 自动注册到测试注册中心

#### `collect_coverage`
- 收集代码覆盖率任务
- 支持lcov报告生成

#### `get_test_statistics`
- 获取测试统计信息任务

**特性**:
- ✅ 异步执行
- ✅ 自动重试
- ✅ 进度更新
- ✅ 错误处理
- ✅ 日志记录

---

### 7. API端点 ✅

**文件**: `src/api/v1/test.py`

**新增端点**:

#### POST `/api/v1/test/celery/submit`
提交测试任务到Celery队列

**请求示例**:
```json
{
    "project_id": 1,
    "pipeline_id": "pipeline-123",
    "job_id": "job-456",
    "gitlab_job_id": 789,
    "job_name": "test-linux",
    "build_dir": "/path/to/build",
    "source_dir": "/path/to/source",
    "test_type": "googletest",
    "enable_coverage": true
}
```

**响应**:
```json
{
    "job_id": "job-456",
    "celery_task_id": "abc-123-def",
    "status": "pending",
    "message": "Test task submitted to Celery queue"
}
```

#### GET `/api/v1/test/celery/{job_id}/status`
获取测试任务状态

**响应**:
```json
{
    "job_id": "job-456",
    "status": "success",
    "result": {
        "status": "success",
        "total_tests": 150,
        "passed_tests": 148,
        "failed_tests": 2,
        "coverage_percent": 85.5
    }
}
```

#### POST `/api/v1/test/celery/{job_id}/cancel`
取消测试任务

#### GET `/api/v1/test/celery/active`
列出活跃的测试任务

#### POST `/api/v1/test/celery/discover`
发现测试用例

#### POST `/api/v1/test/celery/coverage`
收集代码覆盖率

#### GET `/api/v1/test/celery/statistics`
获取测试统计信息

---

## 使用方式

### 快速开始

#### 1. 提交测试任务

```bash
curl -X POST "http://localhost:8000/api/v1/test/celery/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "pipeline_id": "pipeline-123",
    "job_id": "job-456",
    "gitlab_job_id": 789,
    "job_name": "test-linux",
    "build_dir": "/path/to/build",
    "source_dir": "/path/to/source",
    "test_type": "googletest",
    "enable_coverage": true
  }'
```

#### 2. 查询测试状态

```bash
curl "http://localhost:8000/api/v1/test/celery/job-456/status"
```

#### 3. 查看测试统计

```bash
curl "http://localhost:8000/api/v1/test/celery/statistics?project_id=1"
```

---

## 测试框架支持

### Google Test

**可执行文件识别**:
- `*_gtest`
- `*_test`
- 包含"google"的文件名

**发现命令**:
```bash
./test_binary --gtest_list_tests
```

**运行选项**:
- `--gtest_filter` - 过滤测试
- `--gtest_output=xml:file.xml` - XML输出

**输出格式**:
```
[==========] Running 3 tests from 1 test suite.
[----------] 1 test from TestSuite
[ RUN      ] TestSuite.testName
[       OK ] TestSuite.testName (100 ms)
```

### Catch2

**可执行文件识别**:
- `*_catch`
- `*_test`
- 包含"catch"的文件名

**发现命令**:
```bash
./test_binary --list-tests
```

**运行选项**:
- `--reporter=json` - JSON输出
- `--use-colour` - 彩色输出
- `--durations yes` - 显示执行时间

**输出格式**:
```
test.cpp:10: TEST_CASEsuite_name:test_name
  PASSED
```

### Qt Test

**可执行文件识别**:
- `tst_*`
- `*_test`

**发现方式**:
- 从源码解析（查找`private slots`）
- 或使用 `-datatags` 选项

**运行选项**:
- `-datatags` - 列出数据标签
- XML输出支持

**输出格式**:
```
********* Start testing of TestSuite *********
PASS   : TestSuite::testCase1()
FAIL!  : TestSuite::testCase2()
Totals: 3 passed, 1 failed, 0 skipped
********* Finished testing of TestSuite *********
```

---

## 覆盖率收集

### gcov

**基本用法**:
```bash
gcov -o build_dir source_file.cpp
```

**输出格式**:
```
File 'source.cpp'
Lines executed:80.00% of 100
```

### lcov

**收集覆盖率**:
```bash
lcov --capture --directory build_dir --output-file coverage.info
```

**过滤不需要的路径**:
```bash
lcov --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage_filtered.info
```

**生成HTML报告**:
```bash
genhtml coverage_filtered.info --output-directory html_report
```

---

## 测试注册中心

### 元数据管理

**注册测试**:
```python
from src.services.test.registry import test_registry_manager

registry = test_registry_manager.get_registry(project_id=1)

# 注册单个测试
test_meta = registry.register_test(
    test=TestCase(
        name="test_function",
        suite="TestSuite",
        file="test.cpp",
        line=10,
    ),
    metadata={
        "priority": "high",
        "tags": ["unit", "fast"],
        "source_files": ["src/function.cpp"],
    }
)
```

**更新结果**:
```python
registry.update_test_result(
    test_id="test_abc123",
    status=TestStatus.PASSED,
    duration_ms=150,
    timestamp=datetime.now(),
)
```

### 查找测试

**按变更文件**（影响分析）:
```python
changed_files = ["src/utils.cpp", "src/api.cpp"]
tests = registry.find_tests_to_run(changed_files=changed_files)
```

**按标签**:
```python
tests = registry.find_tests_to_run(tags=["unit"])
```

**按优先级**:
```python
tests = registry.find_tests_to_run(priority=TestPriority.CRITICAL)
```

### 统计信息

```python
stats = registry.get_statistics()

print(stats)
# {
#     "total_tests": 150,
#     "by_priority": {"critical": 10, "high": 30, "medium": 80, "low": 30},
#     "by_status": {"passed": 145, "failed": 5, "pending": 0},
#     "flaky_tests": 3,
#     "slow_tests": 15,
#     "avg_pass_rate": 96.67,
# }
```

---

## 测试结果对比

**比较两次运行**:
```python
from src.services.test.result_collector import test_result_collector

comparison = await test_result_collector.compare_runs(
    run_id1="run_001",
    run_id2="run_002",
)

print(comparison)
# {
#     "tests": {
#         "total": {"run1": 150, "run2": 155, "diff": 5},
#         "passed": {"run1": 145, "run2": 150, "diff": 5},
#         "failed": {"run1": 5, "run2": 5, "diff": 0},
#     },
#     "failed_tests": {
#         "both": ["TestSuite.test1"],
#         "fixed": ["TestSuite.test2"],
#         "regressed": ["TestSuite.test3"],
#     },
# }
```

---

## WebSocket集成

测试执行引擎与日志流处理器集成，支持实时日志推送：

```python
# 在测试执行时自动创建日志流处理器
log_streamer = build_log_stream_manager.create_streamer(
    job_id=config.job_id,
    project_id=config.project_id,
    pipeline_id=config.pipeline_id
)

# 发送测试开始状态
await log_streamer.send_status_update("running", message="Test started")
await log_streamer.stream_info(f"Starting test run for {config.job_id}")

# 发送测试结果
if result.status == TestStatus.PASSED:
    await log_streamer.send_status_update("success", message="Tests passed")
    await log_streamer.stream_info(f"All tests passed! ({result.passed_tests}/{result.total_tests})")
```

**WebSocket订阅**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        action: 'subscribe',
        topic: `build:${job_id}`
    }));
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log(`[${message.level}] ${message.message}`);
};
```

---

## 数据结构

### TestConfig

```python
@dataclass
class TestConfig:
    project_id: int
    pipeline_id: int
    job_id: int
    build_dir: str
    source_dir: str
    test_filter: Optional[str] = None
    parallel_jobs: int = 4
    timeout: int = 300
    enable_coverage: bool = True
    coverage_format: str = "xml"
    env_vars: Dict[str, str] = field(default_factory=dict)
```

### TestResult

```python
@dataclass
class TestResult:
    status: TestStatus
    suites: List[TestSuite]
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    coverage_percent: Optional[float] = None
    coverage_lines: Optional[int] = None
    coverage_lines_covered: Optional[int] = None
    duration_seconds: float = 0
    stdout: str = ""
    stderr: str = ""
    started_at: datetime = None
    finished_at: datetime = None
    failed_test_cases: List[TestCase] = field(default_factory=list)
```

---

## 性能优化

### 并行测试执行

测试执行器支持并行执行：

```python
config = TestConfig(
    # ...
    parallel_jobs=4,  # 并行执行4个测试
)
```

### 覆盖率收集优化

**快速覆盖率查询**:
```python
# 只统计前几个文件以加快速度
coverage = await coverage_collector.get_quick_coverage(build_dir)
```

### 测试缓存

测试注册中心自动缓存测试元数据：
- 持久化到本地JSON文件
- 启动时自动加载
- 更新时自动保存

---

## 故障排查

### 问题1: 测试发现失败

**可能原因**:
- 测试可执行文件不在构建目录
- 没有执行权限
- 框架无法识别

**解决方案**:
```bash
# 检查可执行文件
find build_dir -type f -executable -name "*test*"

# 手动列出测试
./test_binary --gtest_list_tests  # Google Test
./test_binary --list-tests        # Catch2
```

### 问题2: 覆盖率收集失败

**可能原因**:
- gcov未安装
- 没有.gcda文件
- 编译时没有启用覆盖率选项

**解决方案**:
```bash
# 检查gcov
gcov --version

# 检查.gcda文件
find build_dir -name "*.gcda"

# 编译时添加覆盖率选项
cmake -DCMAKE_CXX_FLAGS="--coverage" -DCMAKE_EXE_LINKER_FLAGS="--coverage"
```

### 问题3: Celery任务不执行

**可能原因**:
- Celery worker未运行
- 队列配置错误
- 任务路由错误

**解决方案**:
```bash
# 启动Celery worker
celery -A src.tasks.celery_app worker --loglevel=info --queues=test

# 检查队列
celery -A src.tasks.celery_app inspect active_queues
```

---

## 后续优化

### 短期优化
- [ ] 添加并行测试执行支持
- [ ] 实现测试分组
- [ ] 添加测试重试机制
- [ ] 优化覆盖率收集速度

### 长期优化
- [ ] 分布式测试执行
- [ ] 测试结果趋势分析
- [ ] 智能测试优先级排序
- [ ] 自动化测试生成

---

## 与构建引擎集成

测试执行引擎与构建执行引擎无缝集成：

```
GitLab CI/CD
    ↓
构建引擎 (Phase 1-4)
    ↓
测试执行引擎
    ↓
测试发现 → 测试注册 → 测试执行 → 结果收集 → 覆盖率收集
    ↓
WebSocket实时推送
    ↓
Dashboard显示
```

**集成点**:
1. 构建完成后自动触发测试
2. 使用构建产物进行测试
3. 收集构建和测试的综合报告
4. 统一的状态跟踪和日志流

---

## 文件清单

**新增文件** (8个):
1. `src/services/test/discovery.py` - 测试发现器
2. `src/services/test/registry.py` - 测试注册中心
3. `src/services/test/gtest_executor.py` - Google Test执行器
4. `src/services/test/catch2_executor.py` - Catch2执行器
5. `src/services/test/result_collector.py` - 测试结果收集器
6. `src/services/test/coverage.py` - 代码覆盖率收集器
7. `src/tasks/test_tasks.py` - Celery测试任务
8. `TEST_ENGINE_SUMMARY.md` - 本文档

**修改文件** (1个):
1. `src/api/v1/test.py` - 添加Celery测试端点

**现有文件** (已存在):
1. `src/services/test/base.py` - 基础类和接口
2. `src/services/test/qttest_executor.py` - Qt Test执行器
3. `src/services/test/service.py` - 测试服务
4. `src/services/test/executor.py` - 执行器基类

---

**实施人员**: Claude Code
**审核状态**: 待审核
**下一步**: 智能测试选择功能的开发
