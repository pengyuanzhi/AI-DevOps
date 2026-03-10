#!/usr/bin/env python3
"""
E2E测试演示 - 自主流水线维护系统

使用模拟日志验证核心功能
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.ai.pipeline_maintenance import (
    FailureClassifier,
    RootCauseAnalyzer,
    RootCauseType,
    AnalysisContext,
    FixGenerator,
)


async def test_scenario(name: str, description: str, build_log: str, expected_type, is_test=False):
    """测试单个场景"""
    print(f"\n{'=' * 80}")
    print(f"测试场景: {name}")
    print(f"描述: {description}")
    print(f"{'=' * 80}\n")

    # 步骤1: 失败分类
    print("步骤1: 失败分类")
    print("-" * 40)

    classifier = FailureClassifier()

    # 根据场景类型设置正确的上下文
    context = {"is_test": is_test} if is_test else {"is_build": True}
    classification = classifier.classify(build_log, context)

    print(f"✅ 分类结果: {classification.failure_type.value}")
    print(f"   置信度: {classification.confidence:.2f}")
    if classification.error_location:
        print(f"   错误位置: {classification.error_location}")

    if classification.suggested_actions:
        print(f"   建议操作:")
        for action in classification.suggested_actions[:3]:
            print(f"     - {action}")

    # 步骤2: 根因分析
    print("\n步骤2: 根因分析")
    print("-" * 40)

    analyzer = RootCauseAnalyzer()
    context = AnalysisContext(
        failure_log=build_log,
        failure_type=classification.failure_type,
        project_id=1,
        pipeline_id="demo-pipeline",
        job_id=name,
    )

    root_cause = await analyzer.analyze(context, use_ai=False)

    print(f"✅ 根因类型: {root_cause.root_cause_type.value}")
    print(f"   置信度: {root_cause.confidence:.2f}")
    print(f"   标题: {root_cause.title}")
    print(f"   描述: {root_cause.description[:100]}...")

    if root_cause.suggested_fixes:
        print(f"   建议修复:")
        for fix in root_cause.suggested_fixes[:2]:
            print(f"     - {fix}")

    # 步骤3: 修复建议生成
    print("\n步骤3: 修复建议生成")
    print("-" * 40)

    generator = FixGenerator()
    suggestions = await generator.generate_fix(root_cause, use_ai=False)

    print(f"✅ 生成了 {len(suggestions)} 条修复建议")

    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"\n   建议 {i}:")
        print(f"     类型: {suggestion.fix_type.value}")
        print(f"     复杂度: {suggestion.complexity.value}")
        print(f"     标题: {suggestion.title}")
        print(f"     风险: {suggestion.risk_level}")
        print(f"     可自动应用: {suggestion.auto_applicable}")

        if suggestion.description:
            desc = suggestion.description[:80] + "..." if len(suggestion.description) > 80 else suggestion.description
            print(f"     描述: {desc}")

    # 验证
    print("\n步骤4: 结果验证")
    print("-" * 40)

    type_match = classification.failure_type == expected_type
    confidence_ok = classification.confidence >= 0.5
    has_fixes = len(suggestions) > 0

    print(f"✅ 分类正确: {'是' if type_match else '否'}")
    print(f"✅ 置信度达标: {'是' if confidence_ok else '否'}")
    print(f"✅ 有修复建议: {'是' if has_fixes else '否'}")

    success = type_match and confidence_ok and has_fixes
    print(f"\n{'✅ 测试通过' if success else '❌ 测试失败'}")

    return success


async def main():
    """主函数"""
    print("=" * 80)
    print("E2E测试演示 - 自主流水线维护系统")
    print("=" * 80)
    print(f"时间: {datetime.now().isoformat()}\n")

    from src.services.ai.pipeline_maintenance import FailureType

    scenarios = [
        # 场景1: 编译错误
        (
            "scenario1_missing_header",
            "编译错误：缺失头文件",
            """
[ 25%] Building CXX object CMakeFiles/calculator.dir/calculator.cpp.o
/home/user/project/calculator.cpp:2:10: fatal error: math_utils.h: No such file or directory
    2 | #include "math_utils.h"
      |          ^~~~~~~
compilation terminated.
/home/user/project/calculator.cpp: In member function 'double Calculator::add(double, double)':
/home/user/project/calculator.cpp:13:24: error: 'MathUtils' was not declared in this scope
   13 |     double result = MathUtils::add(a, b);
      |                        ^~~~~~~~~~
make[2]: *** [CMakeFiles/calculator.dir/build.make:76: CMakeFiles/calculator.dir/calculator.cpp.o] Error 1
""",
            FailureType.COMPILATION_ERROR,
        ),

        # 场景2: 链接错误
        (
            "scenario2_link_error",
            "链接错误：未定义引用",
            """
[100%] Linking CXX executable qt_app
/usr/bin/ld: CMakeFiles/qt_app.dir/main.cpp.o: in function 'main':
main.cpp:(.text+0x15): undefined reference to `get_value()'
/usr/bin/ld: main.cpp:(.text+0x2a): undefined reference to `calculate_value(int)'
collect2: error: ld returned 1 exit status
make[2]: *** [CMakeFiles/qt_app.dir/build.make:102: qt_app] Error 1
""",
            FailureType.LINK_ERROR,
        ),

        # 场景3: 测试失败
        (
            "scenario3_test_failure",
            "测试失败：断言错误",
            """
********* Start testing of CalculatorTest *********
Config: Using QtTest library 6.4.0
FAIL!  : CalculatorTest::testAddition() Compared values are not the same
   Actual   (calc.add(2, 3)): 5
   Expected (6.0)             : 6
   Loc: [../tests/tst_calculator.cpp(19)]
FAIL!  : CalculatorTest::testSubtraction() Compared values are not the same
   Actual   (calc.subtract(10, 4)): 6
   Expected (7.0)                : 7
   Loc: [../tests/tst_calculator.cpp(24)]
Totals: 2 passed, 2 failed, 0 skipped
********* Finished testing of CalculatorTest *********
""",
            FailureType.TEST_FAILURE,
        ),

        # 场景4: 测试超时
        (
            "scenario4_test_timeout",
            "测试超时",
            """
********* Start testing of NetworkTest *********
PASS   : NetworkTest::initTestCase()
Running test "testConnect"...
Timeout! Test did not finish after 30000 ms
Process is still running, forcing termination
FAIL!  : NetworkTest::testConnect() Test timed out
Loc: [../tests/tst_network.cpp(45)]
Totals: 1 passed, 1 failed, 0 skipped
""",
            FailureType.TEST_TIMEOUT,
        ),

        # 场景5: 内存泄漏
        (
            "scenario5_memory_leak",
            "内存泄漏",
            """
==12345== Memcheck, a memory error detector
==12345== HEAP SUMMARY:
==12345==     in use at exit: 1,048,576 bytes in 1,000 blocks
==12345==   total heap usage: 2,000 allocs, 1,000 frees, 2,097,152 bytes allocated
==12345==
==12345== 1,048,576 bytes in 1,000 blocks are definitely lost
==12345==    at 0x4848899: operator new(unsigned long)
==12345==    by 0x11234AB: DataManager::processData() (DataManager.cpp:45)
==12345==
==12345== LEAK SUMMARY:
==12345==    definitely lost: 1,048,576 bytes in 1,000 blocks
==12345==
==12345== ERROR SUMMARY: 1 errors from 1 contexts
""",
            FailureType.MEMORY_LEAK,
        ),
    ]

    results = []

    for scenario in scenarios:
        name, desc, log, expected = scenario

        # 确定是否为测试场景
        is_test = expected in [FailureType.TEST_FAILURE, FailureType.TEST_TIMEOUT,
                              FailureType.TEST_CRASH, FailureType.ASSERTION_FAILED]

        success = await test_scenario(name, desc, log, expected, is_test=is_test)
        results.append((name, success))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    total = len(results)
    passed = sum(1 for _, s in results if s)
    failed = total - passed

    print(f"\n总测试数: {total}")
    print(f"  通过: {passed} ✅")
    print(f"  失败: {failed} ❌")
    print(f"  通过率: {passed/total*100:.1f}%")

    print("\n详细结果:")
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} - {name}")

    print("\n" + "=" * 80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
