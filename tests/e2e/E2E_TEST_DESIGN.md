# 端到端（E2E）测试设计文档

**日期**: 2026-03-09
**目的**: 使用真实Qt C++项目验证自主流水线维护系统
**范围**: 完整的CI/CD流水线维护流程

---

## 测试目标

### 1. 功能验证
- ✅ 失败分类准确性
- ✅ 根因分析准确性
- ✅ 修复建议有效性
- ✅ 自动修复安全性
- ✅ MR自动化完整性

### 2. 性能验证
- 响应时间 < 30秒
- 分类准确率 > 85%
- 修复成功率 > 60%（可修复问题）
- 系统稳定性（长时间运行）

### 3. 集成验证
- GitLab CI/CD集成
- Git仓库分析
- 构建日志解析
- 测试结果解析

---

## 测试场景设计

### 场景1: 编译错误 - 缺失头文件

**问题类型**: Compilation Error
**严重程度**: High
**可修复性**: 高（自动修复）

**测试项目**: `qt_calculator`

**错误设计**:
```cpp
// calculator.cpp
#include "math_utils.h"  // ❌ 文件不存在
#include <QWidget>

double Calculator::calculate(double x, double y) {
    return MathUtils::add(x, y);  // ❌ 未定义的类型
}
```

**预期行为**:
1. 系统识别为 COMPILATION_ERROR
2. 定位到 calculator.cpp:1
3. 根因分析：DEPENDENCY_ISSUE
4. 修复建议：创建 math_utils.h 或移除引用
5. 自动修复：创建缺失的头文件

**验证点**:
- [ ] 分类正确：COMPILATION_ERROR
- [ ] 置信度 > 0.7
- [ ] 错误位置准确：calculator.cpp:1
- [ ] 修复建议可执行
- [ ] 自动修复成功
- [ ] 构建通过

---

### 场景2: 链接错误 - 未定义引用

**问题类型**: Link Error
**严重程度**: High
**可修复性**: 中等

**测试项目**: `qt_app`

**错误设计**:
```cpp
// main.cpp
extern int get_value();  // 声明

int main() {
    int v = get_value();  // ❌ 链接错误：undefined reference
    return 0;
}
// ❌ 缺少 get_value() 的定义
```

**预期行为**:
1. 系统识别为 LINK_ERROR
2. 根因分析：DEPENDENCY_ISSUE
3. 修复建议：添加函数定义或链接库
4. 修复方案：提供实现文件

**验证点**:
- [ ] 分类正确：LINK_ERROR
- [ ] 识别 undefined reference 模式
- [ ] 修复建议包含添加函数实现
- [ ] 修复后链接成功

---

### 场景3: 测试失败 - 断言错误

**问题类型**: Test Failure
**严重程度**: Medium
**可修复性**: 低（需要人工判断）

**测试项目**: `qt_test_project`

**错误设计**:
```cpp
// tst_calculator.cpp
void CalculatorTest::testAddition() {
    Calculator calc;
    // ❌ 错误的期望值
    QCOMPARE(calc.add(2, 3), 6);  // 期望6，实际5
}
```

**预期行为**:
1. 系统识别为 TEST_FAILURE
2. 提取失败信息：Expected: 6, Actual: 5
3. 根因分析：CODE_DEFECT
4. 修复建议：修正期望值或实现
5. 标记为需要人工审核

**验证点**:
- [ ] 分类正确：TEST_FAILURE
- [ ] 提取断言信息
- [ ] 识别期望值不匹配
- [ ] 不自动应用修复（risk=high）
- [ ] 创建MR供人工审核

---

### 场景4: Qt特定错误 - MOC文件缺失

**问题类型**: Configuration Issue
**严重程度**: High
**可修复性**: 中等

**测试项目**: `qt_widget_app`

**错误设计**:
```cpp
// MyWidget.h
#include <QWidget>
#include <QObject>

class MyWidget : public QWidget {  // ❌ 缺少 Q_OBJECT
    Q_OBJECT  // 但没有正确配置

signals:
    void clicked();

public:
    MyWidget(QWidget* parent = nullptr);
};
```

**CMakeLists.txt 问题**:
```cmake
# ❌ 缺少 Qt5::Widgets 链接
# ❌ 未设置 AUTOMOC ON
```

**预期行为**:
1. 系统识别为 CONFIGURATION_ISSUE
2. 检测到 vtable 错误或 MOC 相关错误
3. 根因分析：CONFIGURATION_ISSUE
4. 修复建议：启用 AUTOMOC，添加 Q_OBJECT
5. 修复 CMakeLists.txt

**验证点**:
- [ ] 识别 Qt MOC 问题
- [ ] 检测 CMake 配置错误
- [ ] 修复建议包含 AUTOMOC
- [ ] 修复后构建成功

---

### 场景5: 内存泄漏

**问题类型**: Runtime Error
**严重程度**: High
**可修复性**: 低

**测试项目**: `qt_memory_test`

**错误设计**:
```cpp
void DataManager::processData() {
    auto* data = new LargeObject();  // ❌ 内存泄漏
    // 使用 data
    // ❌ 忘记 delete
}
```

**预期行为**:
1. 通过 Valgrind 或 ASan 检测
2. 系统识别为 MEMORY_LEAK
3. 定位到具体代码行
4. 修复建议：使用智能指针
5. 提供代码示例

**验证点**:
- [ ] 检测到内存泄漏
- [ ] 识别泄漏位置
- [ ] 建议使用智能指针
- [ ] 修复后无泄漏

---

### 场景6: 资源泄漏 - 文件句柄

**问题类型**: Resource Leak
**严重程度**: Medium
**可修复性**: 中等

**错误设计**:
```cpp
void FileReader::readConfig() {
    QFile file("config.txt");
    file.open(QIODevice::ReadOnly);
    // ❌ 没有关闭文件（RAII应该自动关闭，但显式关闭更好）
    processFile(file);
    // 如果在 processFile 中抛出异常...
}
```

**预期行为**:
1. 通过代码分析检测
2. 识别资源泄漏模式
3. 建议使用 RAII 或显式关闭

---

### 场景7: 依赖版本不匹配

**问题类型**: Dependency Issue
**严重程度**: Medium
**可修复性**: 中等

**错误设计**:
```cmake
# CMakeLists.txt
find_package(Qt6 6.5 REQUIRED)  # ❌ 需要6.5，但系统只有6.2
```

或

```cpp
// 使用已废弃的API
auto* widget = new QWidget();
widget->raise();  // ❌ Qt6中已废弃
```

**预期行为**:
1. 检测版本不兼容
2. 识别废弃API使用
3. 建议升级或替换API

---

## 测试项目结构

```
tests/e2e/qt_projects/
├── scenario1_missing_header/
│   ├── CMakeLists.txt
│   ├── calculator.cpp
│   ├── calculator.h
│   └── main.cpp
│
├── scenario2_link_error/
│   ├── CMakeLists.txt
│   ├── main.cpp
│   └── lib/
│
├── scenario3_test_failure/
│   ├── CMakeLists.txt
│   ├── calculator.cpp
│   ├── calculator.h
│   └── tst_calculator.cpp
│
├── scenario4_qt_moc/
│   ├── CMakeLists.txt
│   ├── MyWidget.h
│   ├── MyWidget.cpp
│   └── main.cpp
│
├── scenario5_memory_leak/
│   ├── CMakeLists.txt
│   ├── DataManager.h
│   ├── DataManager.cpp
│   └── main.cpp
│
├── scenario6_resource_leak/
│   ├── CMakeLists.txt
│   ├── FileReader.h
│   ├── FileReader.cpp
│   └── main.cpp
│
└── scenario7_dependency_version/
    ├── CMakeLists.txt
    ├── main.cpp
    └── .qtversion
```

---

## E2E测试流程

### 阶段1: 环境准备
```bash
1. 创建测试目录
2. 克隆/创建Qt测试项目
3. 配置Git仓库（模拟真实项目）
4. 设置GitLab CI/CD配置
5. 初始化测试环境
```

### 阶段2: 触发构建
```bash
1. 提交有问题的代码
2. 触发CI/CD流水线
3. 收集构建日志
4. 收集测试结果
```

### 阶段3: 失败分析
```bash
1. 调用失败分类API
2. 调用根因分析API
3. 调用变更关联分析API
4. 生成分析报告
```

### 阶段4: 修复生成
```bash
1. 调用修复生成API
2. 评估修复建议
3. 排序修复建议
4. 选择最佳修复方案
```

### 阶段5: 自动修复（可选）
```bash
1. Dry-run模式执行修复
2. 验证修复效果
3. 实际应用修复（如果安全）
4. 触发验证构建
```

### 阶段6: MR自动化
```bash
1. 创建修复分支
2. 提交修复代码
3. 创建Merge Request
4. 添加标签和描述
5. 触发验证流水线
```

### 阶段7: 验证和清理
```bash
1. 验证修复后的构建
2. 验证测试通过
3. 收集性能指标
4. 清理测试环境
5. 生成测试报告
```

---

## 测试脚本架构

### 主测试脚本
```python
# tests/e2e/run_e2e_tests.py

class E2ETestRunner:
    """E2E测试运行器"""

    def __init__(self):
        self.scenarios = []
        self.results = []

    def load_scenarios(self):
        """加载所有测试场景"""

    def run_scenario(self, scenario: TestScenario):
        """运行单个场景"""

    def verify_classification(self, scenario, result):
        """验证分类结果"""

    def verify_root_cause(self, scenario, result):
        """验证根因分析"""

    def verify_fix(self, scenario, suggestions):
        """验证修复建议"""

    def generate_report(self):
        """生成测试报告"""
```

### 场景定义
```python
# tests/e2e/scenarios/scenario_definitions.py

@dataclass
class TestScenario:
    """测试场景定义"""
    name: str
    description: str
    project_path: str
    failure_type: FailureType
    expected_confidence: float
    auto_fixable: bool
    verification_steps: List[str]
```

---

## 成功标准

### 功能指标
- ✅ 所有场景都能正确分类
- ✅ 分类准确率 ≥ 85%
- ✅ 根因分析准确率 ≥ 70%
- ✅ 修复建议合理率 ≥ 80%
- ✅ 自动修复成功率 ≥ 60%（可修复问题）

### 性能指标
- ✅ 失败分类 < 5秒
- ✅ 根因分析 < 20秒
- ✅ 修复生成 < 15秒
- ✅ 完整流程 < 60秒

### 质量指标
- ✅ 无误报（将正确代码误报为错误）
- ✅ 无危险修复（破坏正常功能）
- ✅ 所有自动修复都可回滚
- ✅ MR描述清晰完整

---

## 持续集成

### GitLab CI配置
```yaml
# .gitlab-ci.yml

e2e-tests:
  stage: test
  image: qt-6-dev:latest
  services:
    - postgres:latest
    - redis:latest
  variables:
    TEST_ENV: "e2e"
  script:
    - python tests/e2e/run_e2e_tests.py
    - python tests/e2e/verify_results.py
  artifacts:
    reports:
      junit: tests/e2e/results/*.xml
    paths:
      - tests/e2e/results/
      - tests/e2e/logs/
  only:
    - main
    - merge_requests
```

---

## 下一步行动

### 立即执行
1. ✅ 创建测试项目结构
2. ✅ 实现场景1-3的Qt项目
3. ✅ 编写E2E测试脚本
4. ✅ 运行初始测试

### 短期（1-2周）
1. 实现所有7个场景
2. 完善测试脚本
3. 添加性能监控
4. 生成测试报告

### 中期（1个月）
1. 在真实项目中测试
2. 收集用户反馈
3. 优化准确率
4. 完善文档

---

**创建时间**: 2026-03-09
**测试场景**: 7个
**测试项目**: Qt C++
**目标覆盖率**: 100%核心功能
