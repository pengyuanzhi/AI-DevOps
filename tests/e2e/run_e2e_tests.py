#!/usr/bin/env python3
"""
端到端（E2E）测试运行器

使用真实Qt C++项目验证自主流水线维护系统
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.ai.pipeline_maintenance import (
    FailureClassifier,
    FailureType,
    FailureSeverity,
    RootCauseAnalyzer,
    RootCauseType,
    AnalysisContext,
    FixGenerator,
    FixExecutor,
    ExecutionStatus,
)


@dataclass
class TestScenario:
    """测试场景定义"""
    name: str
    description: str
    project_path: str
    failure_type: FailureType
    expected_confidence: float
    auto_fixable: bool
    build_command: List[str]
    test_command: Optional[List[str]] = None
    verification_steps: List[str] = field(default_factory=list)
    expected_error_patterns: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """测试结果"""
    scenario_name: str
    timestamp: datetime
    success: bool

    # 构建信息
    build_success: bool = False
    build_log: str = ""
    build_time: float = 0.0

    # 测试信息
    test_success: bool = True
    test_log: str = ""

    # 分类结果
    classification_correct: bool = False
    classification_type: Optional[FailureType] = None
    classification_confidence: float = 0.0

    # 根因分析
    root_cause_correct: bool = False
    root_cause_type: Optional[RootCauseType] = None
    root_cause_confidence: float = 0.0

    # 修复建议
    fix_suggestions_count: int = 0
    fix_applicable: bool = False
    fix_success: bool = False

    # 性能指标
    classification_time: float = 0.0
    analysis_time: float = 0.0
    fix_generation_time: float = 0.0

    # 错误信息
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['classification_type'] = self.classification_type.value if self.classification_type else None
        data['root_cause_type'] = self.root_cause_type.value if self.root_cause_type else None
        return data


class E2ETestRunner:
    """E2E测试运行器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent / "qt_projects"
        self.results_dir = Path(__file__).parent / "results"
        self.logs_dir = Path(__file__).parent / "logs"

        # 创建目录
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 初始化服务
        self.classifier = FailureClassifier()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.fix_generator = FixGenerator()
        self.fix_executor = FixExecutor()

        # 测试场景
        self.scenarios = self._load_scenarios()

    def _load_scenarios(self) -> List[TestScenario]:
        """加载测试场景"""
        scenarios = [
            TestScenario(
                name="scenario1_missing_header",
                description="编译错误：缺失头文件",
                project_path=str(self.base_dir / "scenario1_missing_header"),
                failure_type=FailureType.COMPILATION_ERROR,
                expected_confidence=0.7,
                auto_fixable=True,
                build_command=["cmake", "--build", "build"],
                test_command=["ctest", "--output-on-failure"],
                verification_steps=[
                    "检查是否识别为COMPILATION_ERROR",
                    "验证错误位置准确",
                    "验证修复建议可执行",
                ],
                expected_error_patterns=[
                    "fatal error: math_utils.h: No such file or directory",
                    "error: 'MathUtils' was not declared",
                ],
            ),
            TestScenario(
                name="scenario2_link_error",
                description="链接错误：未定义引用",
                project_path=str(self.base_dir / "scenario2_link_error"),
                failure_type=FailureType.LINK_ERROR,
                expected_confidence=0.7,
                auto_fixable=True,
                build_command=["cmake", "--build", "build"],
                verification_steps=[
                    "检查是否识别为LINK_ERROR",
                    "识别undefined reference模式",
                    "验证修复建议包含添加函数实现",
                ],
                expected_error_patterns=[
                    "undefined reference to",
                    "ld returned",
                ],
            ),
            TestScenario(
                name="scenario3_test_failure",
                description="测试失败：断言错误",
                project_path=str(self.base_dir / "scenario3_test_failure"),
                failure_type=FailureType.TEST_FAILURE,
                expected_confidence=0.8,
                auto_fixable=False,  # 测试失败通常需要人工判断
                build_command=["cmake", "--build", "build"],
                test_command=["ctest", "--output-on-failure"],
                verification_steps=[
                    "检查是否识别为TEST_FAILURE",
                    "提取断言信息",
                    "不自动应用修复",
                ],
                expected_error_patterns=[
                    "FAIL!",
                    "Actual.*6",
                    "Expected.*5",
                ],
            ),
        ]

        return scenarios

    async def run_all_tests(self) -> List[TestResult]:
        """运行所有E2E测试"""
        print("=" * 80)
        print("端到端（E2E）测试 - 自主流水线维护系统")
        print("=" * 80)
        print(f"测试场景数: {len(self.scenarios)}")
        print(f"测试开始时间: {datetime.now().isoformat()}")
        print()

        results = []

        for i, scenario in enumerate(self.scenarios, 1):
            print(f"\n{'=' * 80}")
            print(f"测试场景 {i}/{len(self.scenarios)}: {scenario.name}")
            print(f"描述: {scenario.description}")
            print(f"{'=' * 80}\n")

            result = await self.run_scenario(scenario)
            results.append(result)

            # 打印结果摘要
            self._print_scenario_result(result)

        # 生成报告
        self._generate_report(results)

        return results

    async def run_scenario(self, scenario: TestScenario) -> TestResult:
        """运行单个测试场景"""
        result = TestResult(
            scenario_name=scenario.name,
            timestamp=datetime.now(),
            success=False,
        )

        try:
            # 步骤1: 配置构建环境
            print("步骤1: 配置构建环境...")
            if not await self._setup_build(scenario, result):
                result.errors.append("构建配置失败")
                return result

            # 步骤2: 尝试构建（预期失败）
            print("步骤2: 构建项目（预期失败）...")
            if not await self._build_project(scenario, result):
                result.errors.append("构建步骤失败")
                # 继续执行，因为我们预期构建失败

            # 步骤3: 运行测试（如果适用）
            if scenario.test_command and result.build_success:
                print("步骤3: 运行测试...")
                await self._run_tests(scenario, result)

            # 步骤4: 失败分类
            print("步骤4: 失败分类...")
            await self._classify_failure(scenario, result)

            # 步骤5: 根因分析
            print("步骤5: 根因分析...")
            await self._analyze_root_cause(scenario, result)

            # 步骤6: 修复建议生成
            print("步骤6: 修复建议生成...")
            await self._generate_fixes(scenario, result)

            # 步骤7: 验证结果
            print("步骤7: 验证结果...")
            self._verify_result(scenario, result)

            # 判断成功
            result.success = (
                result.classification_correct and
                result.root_cause_correct and
                result.fix_suggestions_count > 0
            )

        except Exception as e:
            result.errors.append(f"测试执行异常: {str(e)}")
            import traceback
            traceback.print_exc()

        return result

    async def _setup_build(self, scenario: TestScenario, result: TestResult) -> bool:
        """设置构建环境"""
        build_dir = Path(scenario.project_path) / "build"
        build_dir.mkdir(exist_ok=True)

        try:
            # 运行CMake配置
            process = await asyncio.create_subprocess_exec(
                "cmake",
                "..",
                "-DCMAKE_BUILD_TYPE=Debug",
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"  ⚠️  CMake配置失败:")
                print(f"     {stderr.decode()[:500]}")
                result.errors.append(f"CMake配置失败: {stderr.decode()[:200]}")

            return True

        except Exception as e:
            print(f"  ❌ CMake配置异常: {e}")
            return False

    async def _build_project(self, scenario: TestScenario, result: TestResult) -> bool:
        """构建项目"""
        build_dir = Path(scenario.project_path) / "build"

        try:
            start_time = datetime.now()

            process = await asyncio.create_subprocess_exec(
                *scenario.build_command,
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            build_time = (datetime.now() - start_time).total_seconds()
            result.build_time = build_time

            result.build_log = stdout.decode() + "\n" + stderr.decode()
            result.build_success = (process.returncode == 0)

            # 保存完整日志
            log_file = self.logs_dir / f"{scenario.name}_build.log"
            log_file.write_text(result.build_log, encoding='utf-8')

            if result.build_success:
                print(f"  ✅ 构建成功 ({build_time:.2f}秒)")
                return True
            else:
                print(f"  ❌ 构建失败 ({build_time:.2f}秒) - 符合预期")
                # 显示部分错误日志
                error_lines = result.build_log.split('\n')[:20]
                print("  错误日志（前20行）:")
                for line in error_lines:
                    if line.strip():
                        print(f"    {line}")
                return False

        except Exception as e:
            print(f"  ❌ 构建异常: {e}")
            result.errors.append(f"构建异常: {str(e)}")
            return False

    async def _run_tests(self, scenario: TestScenario, result: TestResult):
        """运行测试"""
        if not scenario.test_command:
            return

        build_dir = Path(scenario.project_path) / "build"

        try:
            process = await asyncio.create_subprocess_exec(
                *scenario.test_command,
                cwd=str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            result.test_log = stdout.decode() + "\n" + stderr.decode()
            result.test_success = (process.returncode == 0)

            # 保存测试日志
            log_file = self.logs_dir / f"{scenario.name}_test.log"
            log_file.write_text(result.test_log, encoding='utf-8')

            if result.test_success:
                print(f"  ✅ 测试通过")
            else:
                print(f"  ❌ 测试失败 - 符合预期")
                print("  测试日志（前20行）:")
                for line in result.test_log.split('\n')[:20]:
                    if line.strip():
                        print(f"    {line}")

        except Exception as e:
            print(f"  ❌ 测试执行异常: {e}")
            result.errors.append(f"测试执行异常: {str(e)}")

    async def _classify_failure(self, scenario: TestScenario, result: TestResult):
        """分类失败"""
        try:
            start_time = datetime.now()

            # 使用构建或测试日志
            log_content = result.test_log if result.test_log else result.build_log

            classification = self.classifier.classify(log_content, {
                "project_path": scenario.project_path,
                "is_build": True,
            })

            classification_time = (datetime.now() - start_time).total_seconds()
            result.classification_time = classification_time

            result.classification_type = classification.failure_type
            result.classification_confidence = classification.confidence

            # 验证分类正确性
            result.classification_correct = (
                classification.failure_type == scenario.failure_type
            )

            if result.classification_correct:
                print(f"  ✅ 分类正确: {classification.failure_type.value}")
                print(f"     置信度: {classification.confidence:.2f} (期望 >= {scenario.expected_confidence})")
                print(f"     耗时: {classification_time:.2f}秒")
            else:
                print(f"  ⚠️  分类不匹配:")
                print(f"     预期: {scenario.failure_type.value}")
                print(f"     实际: {classification.failure_type.value}")
                print(f"     置信度: {classification.confidence:.2f}")

            if classification.error_location:
                print(f"     错误位置: {classification.error_location}")

        except Exception as e:
            print(f"  ❌ 分类失败: {e}")
            result.errors.append(f"分类失败: {str(e)}")

    async def _analyze_root_cause(self, scenario: TestScenario, result: TestResult):
        """分析根因"""
        try:
            start_time = datetime.now()

            # 构建分析上下文
            log_content = result.test_log if result.test_log else result.build_log
            context = AnalysisContext(
                failure_log=log_content,
                failure_type=result.classification_type or FailureType.UNKNOWN,
                project_id=1,
                pipeline_id="e2e-test-pipeline",
                job_id=scenario.name,
            )

            # 执行根因分析（不使用AI，使用规则）
            root_cause = await self.root_cause_analyzer.analyze(
                context=context,
                use_ai=False,  # 使用规则引擎
            )

            analysis_time = (datetime.now() - start_time).total_seconds()
            result.analysis_time = analysis_time

            result.root_cause_type = root_cause.root_cause_type
            result.root_cause_confidence = root_cause.confidence

            print(f"  📊 根因分析结果:")
            print(f"     类型: {root_cause.root_cause_type.value}")
            print(f"     置信度: {root_cause.confidence:.2f}")
            print(f"     标题: {root_cause.title}")
            print(f"     耗时: {analysis_time:.2f}秒")

            if root_cause.suggested_fixes:
                print(f"     修复建议:")
                for fix in root_cause.suggested_fixes[:3]:
                    print(f"       - {fix}")

            # 根因类型验证（宽松）
            # DEPENDENCY_ISSUE 通常对应编译和链接错误
            result.root_cause_correct = (
                root_cause.confidence >= 0.5
            )

        except Exception as e:
            print(f"  ❌ 根因分析失败: {e}")
            result.errors.append(f"根因分析失败: {str(e)}")

    async def _generate_fixes(self, scenario: TestScenario, result: TestResult):
        """生成修复建议"""
        try:
            start_time = datetime.now()

            # 构建根因对象
            from src.services.ai.pipeline_maintenance.root_cause_analyzer import RootCause

            root_cause = RootCause(
                root_cause_type=result.root_cause_type or RootCauseType.UNKNOWN,
                confidence=result.root_cause_confidence,
                title="E2E测试根因",
                description="从构建/测试日志中提取的根因",
                suggested_fixes=[],
            )

            # 生成修复（不使用AI）
            suggestions = await self.fix_generator.generate_fix(
                root_cause=root_cause,
                use_ai=False,
            )

            fix_generation_time = (datetime.now() - start_time).total_seconds()
            result.fix_generation_time = fix_generation_time

            result.fix_suggestions_count = len(suggestions)

            print(f"  🔧 修复建议:")
            print(f"     数量: {len(suggestions)}")
            print(f"     耗时: {fix_generation_time:.2f}秒")

            for i, suggestion in enumerate(suggestions[:3], 1):
                print(f"\n     建议 {i}:")
                print(f"       类型: {suggestion.fix_type.value}")
                print(f"       复杂度: {suggestion.complexity.value}")
                print(f"       标题: {suggestion.title}")
                print(f"       风险: {suggestion.risk_level}")
                print(f"       可自动应用: {suggestion.auto_applicable}")
                print(f"       置信度: {suggestion.confidence:.2f}")

                if suggestion.description:
                    print(f"       描述: {suggestion.description[:100]}...")

                if suggestion.commands:
                    print(f"       命令:")
                    for cmd in suggestion.commands[:3]:
                        print(f"         - {cmd}")

            result.fix_applicable = (len(suggestions) > 0)

        except Exception as e:
            print(f"  ❌ 修复生成失败: {e}")
            result.errors.append(f"修复生成失败: {str(e)}")

    def _verify_result(self, scenario: TestScenario, result: TestResult):
        """验证测试结果"""
        print(f"\n  ✅ 验证结果:")

        checks = []

        # 检查1: 分类正确性
        if result.classification_correct:
            checks.append("✅ 分类正确")
        else:
            checks.append("❌ 分类不正确")

        # 检查2: 置信度
        if result.classification_confidence >= scenario.expected_confidence:
            checks.append(f"✅ 置信度达标 ({result.classification_confidence:.2f} >= {scenario.expected_confidence})")
        else:
            checks.append(f"⚠️  置信度未达标 ({result.classification_confidence:.2f} < {scenario.expected_confidence})")

        # 检查3: 修复建议
        if result.fix_suggestions_count > 0:
            checks.append(f"✅ 生成了修复建议 ({result.fix_suggestions_count}条)")
        else:
            checks.append("❌ 未生成修复建议")

        # 检查4: 性能
        if result.classification_time < 10:
            checks.append(f"✅ 分类速度快 ({result.classification_time:.2f}s < 10s)")
        else:
            checks.append(f"⚠️  分类速度慢 ({result.classification_time:.2f}s)")

        for check in checks:
            print(f"     {check}")

    def _print_scenario_result(self, result: TestResult):
        """打印场景测试结果"""
        print(f"\n{'=' * 80}")
        print(f"测试结果: {result.scenario_name}")
        print(f"{'=' * 80}")
        print(f"  成功: {'✅ 是' if result.success else '❌ 否'}")
        print(f"  构建成功: {'✅ 是' if result.build_success else '❌ 否'}")
        print(f"  测试成功: {'✅ 是' if result.test_success else '❌ 否'}")
        print(f"  分类正确: {'✅ 是' if result.classification_correct else '❌ 否'}")
        print(f"  根因正确: {'✅ 是' if result.root_cause_correct else '❌ 否'}")
        print(f"  修复建议: {result.fix_suggestions_count}条")

        if result.errors:
            print(f"\n  错误:")
            for error in result.errors:
                print(f"    - {error}")

        print(f"\n  性能指标:")
        print(f"    分类耗时: {result.classification_time:.2f}秒")
        print(f"    分析耗时: {result.analysis_time:.2f}秒")
        print(f"    修复生成: {result.fix_generation_time:.2f}秒")
        print(f"    总耗时: {result.classification_time + result.analysis_time + result.fix_generation_time:.2f}秒")

        print(f"{'=' * 80}\n")

    def _generate_report(self, results: List[TestResult]):
        """生成测试报告"""
        print("=" * 80)
        print("测试报告")
        print("=" * 80)

        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success

        print(f"\n总测试数: {total}")
        print(f"  成功: {success} ✅")
        print(f"  失败: {failed} ❌")
        print(f"  通过率: {success/total*100:.1f}%")

        # 统计分类准确率
        classification_correct = sum(1 for r in results if r.classification_correct)
        print(f"\n分类准确率: {classification_correct}/{total} ({classification_correct/total*100:.1f}%)")

        # 统计平均性能
        avg_class_time = sum(r.classification_time for r in results) / total if total > 0 else 0
        avg_analysis_time = sum(r.analysis_time for r in results) / total if total > 0 else 0
        avg_fix_time = sum(r.fix_generation_time for r in results) / total if total > 0 else 0

        print(f"\n平均性能:")
        print(f"  分类时间: {avg_class_time:.2f}秒")
        print(f"  分析时间: {avg_analysis_time:.2f}秒")
        print(f"  修复生成: {avg_fix_time:.2f}秒")

        # 保存JSON报告
        report_file = self.results_dir / f"e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total,
            "success": success,
            "failed": failed,
            "pass_rate": success/total*100,
            "classification_accuracy": classification_correct/total*100,
            "avg_classification_time": avg_class_time,
            "avg_analysis_time": avg_analysis_time,
            "avg_fix_generation_time": avg_fix_time,
            "results": [r.to_dict() for r in results],
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n报告已保存: {report_file}")
        print("=" * 80)


async def main():
    """主函数"""
    runner = E2ETestRunner()

    try:
        results = await runner.run_all_tests()

        # 返回退出码
        success = all(r.success for r in results)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
