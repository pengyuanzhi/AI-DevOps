"""
C++ 测试生成 Agent（Google Test）
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.analyzers.cpp import (
    CppAnalysisResult,
    CppClassInfo,
    CppFunctionInfo,
    get_cpp_parser,
)
from src.core.llm.factory import get_llm_client, LLMClient
from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedCppTest:
    """生成的 C++ 测试"""
    test_file: str  # 测试文件路径
    test_code: str  # 测试代码
    target_class: Optional[str]  # 目标类名
    target_function: Optional[str]  # 目标函数名
    test_framework: str  # gtest, catch2, qtest
    test_cases: List[str] = field(default_factory=list)  # 测试用例名称列表
    coverage_estimate: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Test for {self.target_class or self.target_function} ({self.test_framework})"


@dataclass
class CppTestGenerationResult:
    """C++ 测试生成结果"""
    target_file: str  # 源文件
    tests: List[GeneratedCppTest] = field(default_factory=list)
    total_coverage_estimate: float = 0.0
    generation_time: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)

    # CMake 配置
    cmake_updates: List[str] = field(default_factory=list)

    def get_test_code(self) -> str:
        """获取合并后的测试代码"""
        if not self.tests:
            return ""

        return "\n\n".join(test.test_code for test in self.tests)


class GoogleTestGenerator:
    """Google Test 生成器"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        cpp_parser=None,
    ):
        """
        初始化 Google Test 生成器

        Args:
            llm_client: LLM 客户端
            cpp_parser: C++ 解析器
        """
        self.llm_client = llm_client
        self.cpp_parser = cpp_parser

        # 加载 Prompt 模板
        self.prompt_template = self._load_prompt_template()

        logger.info(
            "gtest_generator_initialized",
            has_llm=llm_client is not None,
            has_parser=cpp_parser is not None,
        )

    def _load_prompt_template(self) -> str:
        """加载 Prompt 模板"""
        template_path = settings.prompts_dir / "cpp_tests" / "gtest_format.txt"

        if template_path.exists():
            logger.debug("loading_gtest_prompt_template", path=str(template_path))
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()

        # 默认模板
        return """Generate Google Test for the following C++ code:

```cpp
{source_code}
```

Generate comprehensive unit tests using Google Test framework."""

    async def generate_tests(
        self,
        source_code: str,
        file_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> CppTestGenerationResult:
        """
        为 C++ 源代码生成 Google Test 测试

        Args:
            source_code: 源代码
            file_path: 文件路径
            options: 生成选项

        Returns:
            CppTestGenerationResult: 生成结果
        """
        start_time = datetime.now()
        options = options or {}

        logger.info(
            "cpp_test_generation_started",
            file_path=file_path,
            options=options,
        )

        result = CppTestGenerationResult(target_file=file_path)

        try:
            # 1. 解析 C++ 代码
            if self.cpp_parser:
                analysis = self.cpp_parser.parse_code(source_code, file_path)
                logger.info(
                    "cpp_code_analyzed",
                    classes_count=len(analysis.classes),
                    functions_count=len(analysis.functions),
                    is_qt_project=analysis.is_qt_project,
                )
            else:
                analysis = None
                logger.warning("no_cpp_parser", message="代码分析被跳过")

            # 2. 构建 Prompt
            prompt = self._build_prompt(source_code, analysis, options)

            # 3. 调用 LLM 生成测试
            if not self.llm_client:
                raise RuntimeError("LLM 客户端未配置")

            generated_code = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.7,
                system_prompt="你是一个专业的 C++ 测试工程师，精通 Google Test 和现代 C++。",
            )

            # 4. 提取测试代码
            test_code = self._extract_test_code(generated_code)

            # 5. 生成测试文件路径
            test_file_path = self._get_test_file_path(file_path)

            # 6. 创建测试对象
            if test_code:
                # 确定测试框架
                test_framework = "gtest"

                # 确定目标类/函数
                target_class = None
                target_function = None

                if analysis and analysis.classes:
                    target_class = analysis.classes[0].name
                elif analysis and analysis.functions:
                    target_function = analysis.functions[0].name

                # 估算覆盖率
                coverage_estimate = self._estimate_coverage(analysis, test_code)

                # 生成 CMake 更新
                cmake_updates = self._generate_cmake_updates(test_file_path, file_path)

                generated_test = GeneratedCppTest(
                    test_file=test_file_path,
                    test_code=test_code,
                    target_class=target_class,
                    target_function=target_function,
                    test_framework=test_framework,
                    coverage_estimate=coverage_estimate,
                )

                result.tests.append(generated_test)
                result.total_coverage_estimate = coverage_estimate
                result.cmake_updates = cmake_updates

                logger.info(
                    "cpp_test_generated",
                    file_path=file_path,
                    test_file_path=test_file_path,
                    coverage_estimate=coverage_estimate,
                )

            # 计算生成时间
            result.generation_time = (datetime.now() - start_time).total_seconds()

            return result

        except Exception as e:
            logger.error(
                "cpp_test_generation_failed",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            result.errors.append(str(e))
            result.generation_time = (datetime.now() - start_time).total_seconds()
            return result

    def _build_prompt(
        self,
        source_code: str,
        analysis: Optional[CppAnalysisResult],
        options: Dict[str, Any],
    ) -> str:
        """构建生成测试的 Prompt"""

        # 格式化代码分析结果
        classes_info = ""
        functions_info = ""
        includes_info = ""
        cpp_version = "C++17"
        is_qt_project = "否"
        qt_modules = []

        if analysis:
            # 格式化类信息
            if analysis.classes:
                classes_info = "### 类定义\n```\n"
                for cls in analysis.classes:
                    classes_info += f"class {cls.name}"
                    if cls.bases:
                        classes_info += f" : public {', public '.join(cls.bases)}"
                    classes_info += "\n{\n"
                    classes_info += f"  公共方法 ({len(cls.public_methods)}): "
                    classes_info += ", ".join(m.name for m in cls.public_methods[:5])
                    if len(cls.public_methods) > 5:
                        classes_info += f", ... (共 {len(cls.public_methods)} 个)"
                    classes_info += "\n}\n\n"

            # 格式化函数信息
            if analysis.functions:
                functions_info = "### 函数列表\n"
                for func in analysis.functions:
                    functions_info += f"- {func.get_signature()}\n"

            # 格式化 include 信息
            if analysis.includes:
                includes_info = "### 包含头文件\n"
                for inc in analysis.includes[:10]:
                    if inc.is_system:
                        includes_info += f"- <{inc.header}>\n"
                    else:
                        includes_info += f"- \"{inc.header}\"\n"

            cpp_version = analysis.language_version
            is_qt_project = "是" if analysis.is_qt_project else "否"
            qt_modules = analysis.qt_modules

        # 填充模板
        try:
            prompt = self.prompt_template.format(
                source_code=source_code,
                classes=classes_info or "无",
                functions=functions_info or "无",
                includes=includes_info or "无",
                cpp_version=cpp_version,
                is_qt_project=is_qt_project,
                qt_modules=", ".join(qt_modules),
            )
        except KeyError as e:
            # 如果模板中有缺失的键，使用简单的格式
            logger.warning("prompt_template_key_error", error=str(e))
            prompt = f"""你是一个专业的 C++ 测试工程师，精通 Google Test 框架。

为以下 C++ 代码生成完整的单元测试：

```cpp
{source_code}
```

生成测试代码，包含：
1. 正常路径测试
2. 边界条件测试
3. 异常处理测试

仅输出 C++ 代码。
"""

        return prompt

    def _extract_test_code(self, generated_text: str) -> str:
        """从生成的文本中提取测试代码"""
        # 移除 markdown 代码块标记
        text = generated_text.strip()

        # 移除 ```cpp 和 ``` 标记
        if text.startswith("```cpp"):
            text = text[7:]  # 移除 ```cpp
        elif text.startswith("```\n"):
            text = text[4:]  # 移除 ```
        elif text.startswith("```"):
            text = text[3:]  # 移除 ```

        if text.endswith("```"):
            text = text[:-3]  # 移除结尾的 ```

        return text.strip()

    def _estimate_coverage(
        self,
        analysis: Optional[CppAnalysisResult],
        test_code: str,
    ) -> float:
        """估算测试覆盖率"""
        if not analysis:
            return 0.5  # 默认估算

        # 获取需要测试的方法数量
        methods_count = sum(len(cls.methods) for cls in analysis.classes)
        functions_count = len(analysis.functions)
        total_count = methods_count + functions_count

        if total_count == 0:
            return 0.0

        # 统计测试用例数量
        test_cases_count = test_code.count("TEST_")

        # 估算覆盖率
        coverage = min(test_cases_count / total_count, 1.0)

        # 根据测试代码长度调整
        test_length_factor = min(len(test_code) / 1000, 1.0)

        final_coverage = coverage * 0.7 + test_length_factor * 0.3

        return round(final_coverage, 2)

    def _get_test_file_path(self, source_file_path: str) -> str:
        """根据源文件路径生成测试文件路径"""
        path = Path(source_file_path)

        # src/module/file.cpp -> tests/module/test_file.cpp
        # 或者 module/file.cpp -> tests/test_file.cpp

        # 如果路径包含 src/，替换为 tests/
        if "src/" in str(path):
            test_path = str(path).replace("src/", "tests/")
        else:
            test_path = "tests/" + str(path)

        # 添加 test_ 前缀
        test_path = Path(test_path)
        test_path = test_path.parent / f"test_{test_path.name}"

        return str(test_path)

    def _generate_cmake_updates(self, test_file: str, source_file: str) -> List[str]:
        """生成 CMakeLists.txt 更新内容"""
        updates = []

        # 提取可执行文件名
        test_name = f"test_{Path(test_file).stem}"

        # 生成 CMake 配置
        cmake_config = f"""
# Google Test for {source_file}
add_executable({test_name}
    {test_file}
    {source_file}
)

target_link_libraries({test_name}
    PRIVATE
        gtest
        gmock
        gtest_main
)

discover_tests({test_name})
"""

        updates.append(cmake_config)

        return updates


# 全局实例
_gtest_generator: Optional[GoogleTestGenerator] = None


def get_gtest_generator() -> GoogleTestGenerator:
    """获取 Google Test 生成器实例（单例）"""
    global _gtest_generator
    if _gtest_generator is None:
        llm_client = get_llm_client() if settings.enable_test_generation else None
        cpp_parser = get_cpp_parser()
        _gtest_generator = GoogleTestGenerator(
            llm_client=llm_client,
            cpp_parser=cpp_parser,
        )
    return _gtest_generator
