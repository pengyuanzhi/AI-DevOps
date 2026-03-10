# 端到端（E2E）测试 - 自主流水线维护系统

使用真实Qt C++项目验证AI驱动的CI/CD流水线维护功能。

---

## 概述

这套E2E测试使用包含真实错误的Qt C++项目来验证：

1. **失败分类准确性** - 能否正确识别编译错误、链接错误、测试失败等
2. **根因分析准确性** - 能否找出问题的根本原因
3. **修复建议质量** - 生成的修复建议是否合理可行
4. **系统性能** - 响应时间、资源使用等

---

## 测试场景

### 场景1: 编译错误 - 缺失头文件

**项目**: `scenario1_missing_header`
**问题**: `calculator.cpp` 引用了不存在的 `math_utils.h`
**预期**: 系统识别为 `COMPILATION_ERROR`，定位错误位置，建议创建头文件或移除引用

```cpp
// calculator.cpp
#include "math_utils.h"  // ❌ 文件不存在
double result = MathUtils::add(a, b);  // ❌ 类型未定义
```

### 场景2: 链接错误 - 未定义引用

**项目**: `scenario2_link_error`
**问题**: `main.cpp` 声明了函数但没有提供实现
**预期**: 系统识别为 `LINK_ERROR`，建议添加函数实现

```cpp
extern int get_value();  // 声明
int v = get_value();     // ❌ 链接错误：undefined reference
// ❌ 缺少 get_value() 的定义
```

### 场景3: 测试失败 - 断言错误

**项目**: `scenario3_test_failure`
**问题**: 测试用例中的期望值不正确
**预期**: 系统识别为 `TEST_FAILURE`，提取断言信息，建议人工审核

```cpp
QCOMPARE(calc.add(2, 3), 6.0);  // ❌ 期望6，实际5
```

---

## 快速开始

### 前置要求

1. **Qt 6** (6.2或更高版本)
```bash
# Ubuntu/Debian
sudo apt-get install qt6-base-dev qt6-tools-dev cmake build-essential

# 或使用 Qt 安装器从官网下载
```

2. **CMake 3.16+**
```bash
cmake --version
```

3. **Python 3.8+**
```bash
python --version
```

4. **C++ 编译器** (GCC, Clang, 或 MSVC)

### 运行测试

**方式1: 使用快速启动脚本（推荐）**

```bash
cd /home/kerfs/AI-CICD-new/tests/e2e
./quick_start.sh
```

**方式2: 手动运行**

```bash
cd /home/kerfs/AI-CICD-new/tests/e2e
python run_e2e_tests.py
```

### 测试输出

测试运行时会显示：
- 每个场景的执行进度
- 构建和测试日志
- 分类结果
- 根因分析
- 修复建议
- 性能指标

测试完成后会生成：
- JSON报告：`results/e2e_report_YYYYMMDD_HHMMSS.json`
- 构建日志：`logs/<scenario>_build.log`
- 测试日志：`logs/<scenario>_test.log`

---

## 测试结果示例

```
================================================================================
端到端（E2E）测试 - 自主流水线维护系统
================================================================================
测试场景数: 3
测试开始时间: 2026-03-09T20:30:00

================================================================================
测试场景 1/3: scenario1_missing_header
描述: 编译错误：缺失头文件
================================================================================

步骤1: 配置构建环境...
步骤2: 构建项目（预期失败）...
  ❌ 构建失败 (2.34秒) - 符合预期
  错误日志（前20行）:
    error: math_utils.h: No such file or directory
    error: 'MathUtils' was not declared in this scope

步骤3: 失败分类...
  ✅ 分类正确: compilation_error
     置信度: 0.85 (期望 >= 0.70)
     耗时: 0.12秒
     错误位置: calculator.cpp:1

步骤4: 根因分析...
  📊 根因分析结果:
     类型: dependency_issue
     置信度: 0.75
     标题: 缺少必要的依赖文件
     耗时: 0.05秒
     修复建议:
       - 创建缺失的math_utils.h头文件
       - 或移除对MathUtils的依赖

步骤5: 修复建议生成...
  🔧 修复建议:
     数量: 2
     耗时: 0.08秒

     建议 1:
       类型: dependency_update
       复杂度: simple
       标题: 更新依赖库配置
       风险: low
       可自动应用: false
       置信度: 0.70

     建议 2:
       类型: code_change
       复杂度: trivial
       标题: 创建缺失的头文件
       风险: low
       可自动应用: true
       置信度: 0.85

步骤6: 验证结果...
  ✅ 验证结果:
     ✅ 分类正确
     ✅ 置信度达标 (0.85 >= 0.70)
     ✅ 生成了修复建议 (2条)
     ✅ 分类速度快 (0.12s < 10s)

================================================================================
测试结果: scenario1_missing_header
================================================================================
  成功: ✅ 是
  构建成功: ❌ 否
  测试成功: ✅ 是
  分类正确: ✅ 是
  根因正确: ✅ 是
  修复建议: 2条

  性能指标:
    分类耗时: 0.12秒
    分析耗时: 0.05秒
    修复生成: 0.08秒
    总耗时: 0.25秒
================================================================================

[场景2和3的输出...]
```

---

## 目录结构

```
tests/e2e/
├── E2E_TEST_DESIGN.md           # 详细的设计文档
├── README.md                     # 本文件
├── quick_start.sh                # 快速启动脚本
├── run_e2e_tests.py              # 主测试脚本
├── scenarios.py                  # 场景定义（可选）
│
├── qt_projects/                  # Qt测试项目
│   ├── scenario1_missing_header/
│   │   ├── CMakeLists.txt
│   │   ├── calculator.cpp
│   │   ├── calculator.h
│   │   ├── main.cpp
│   │   └── tests/
│   │       ├── CMakeLists.txt
│   │       └── tst_calculator.cpp
│   │
│   ├── scenario2_link_error/
│   │   ├── CMakeLists.txt
│   │   └── main.cpp
│   │
│   └── scenario3_test_failure/
│       ├── CMakeLists.txt
│       ├── calculator.cpp
│       ├── calculator.h
│       ├── main.cpp
│       └── tests/
│           ├── CMakeLists.txt
│           └── tst_calculator.cpp
│
├── results/                      # 测试结果
│   └── e2e_report_*.json
│
└── logs/                         # 日志文件
    ├── scenario1_*_build.log
    ├── scenario1_*_test.log
    └── ...
```

---

## 添加新的测试场景

### 1. 创建项目目录

```bash
mkdir -p tests/e2e/qt_projects/scenario4_my_scenario
```

### 2. 添加源文件和CMakeLists.txt

创建包含特定错误的Qt项目。

### 3. 在 `run_e2e_tests.py` 中注册场景

```python
TestScenario(
    name="scenario4_my_scenario",
    description="我的测试场景",
    project_path=str(self.base_dir / "scenario4_my_scenario"),
    failure_type=FailureType.YOUR_TYPE,
    expected_confidence=0.7,
    auto_fixable=True,
    build_command=["cmake", "--build", "build"],
    expected_error_patterns=[
        "error pattern 1",
        "error pattern 2",
    ],
)
```

### 4. 运行测试

```bash
python run_e2e_tests.py
```

---

## 持续集成配置

### GitLab CI

```yaml
# .gitlab-ci.yml

e2e-tests:
  stage: test
  image: debian:bookworm
  before_script:
    - apt-get update -qq
    - apt-get install -y qt6-base-dev qt6-tools-dev cmake build-essential python3 python3-pip
    - pip3 install -r requirements.txt
  script:
    - cd tests/e2e
    - python3 run_e2e_tests.py
  artifacts:
    reports:
      junit: results/e2e_report_*.json
    paths:
      - tests/e2e/results/
      - tests/e2e/logs/
    when: always
  only:
    - main
    - merge_requests
```

---

## 故障排除

### 问题1: 找不到Qt6

**错误**: `Could not find Qt6`

**解决方案**:
```bash
# 设置Qt路径
export Qt6_DIR=/path/to/qt6/lib/cmake/Qt6
export CMAKE_PREFIX_PATH=/path/to/qt6

# 或安装Qt6
sudo apt-get install qt6-base-dev
```

### 问题2: Python导入错误

**错误**: `ModuleNotFoundError: No module named 'src'`

**解决方案**:
```bash
# 从项目根目录运行
cd /home/kerfs/AI-CICD-new
python -m pytest tests/e2e/run_e2e_tests.py

# 或设置PYTHONPATH
export PYTHONPATH=/home/kerfs/AI-CICD-new:$PYTHONPATH
```

### 问题3: CMake配置失败

**错误**: `CMake Error: Could not find CMAKE_ROOT`

**解决方案**:
```bash
# 安装CMake
sudo apt-get install cmake

# 或指定CMake路径
export CMAKE_ROOT=/path/to/cake
```

---

## 性能基准

| 指标 | 目标 | 当前 | 状态 |
|------|------|------|------|
| 失败分类时间 | < 5秒 | ~0.1秒 | ✅ |
| 根因分析时间 | < 20秒 | ~0.05秒 | ✅ |
| 修复生成时间 | < 15秒 | ~0.08秒 | ✅ |
| 分类准确率 | > 85% | TBD | ⏳ |
| 根因分析准确率 | > 70% | TBD | ⏳ |

---

## 下一步

- [ ] 添加更多测试场景（内存泄漏、Qt MOC问题等）
- [ ] 实现真实的自动修复验证
- [ ] 集成GitLab CI/CD
- [ ] 收集性能数据
- [ ] 优化准确率

---

## 相关文档

- [E2E_TEST_DESIGN.md](E2E_TEST_DESIGN.md) - 详细的测试设计文档
- [PIPELINE_MAINTENANCE_SUMMARY.md](../../PIPELINE_MAINTENANCE_SUMMARY.md) - 功能总结
- [LLM_SERVICE_FIX_SUMMARY.md](../../LLM_SERVICE_FIX_SUMMARY.md) - LLM服务修复总结

---

**创建时间**: 2026-03-09
**维护者**: AI-CICD Team
**版本**: 1.0.0
