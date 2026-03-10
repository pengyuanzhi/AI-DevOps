"""
修复生成器单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.ai.pipeline_maintenance.fix_generator import (
    FixGenerator,
    FixSuggestion,
    FixComplexity,
    FixType,
)
from src.services.ai.pipeline_maintenance.root_cause_analyzer import (
    RootCause,
    RootCauseType,
)


class TestFixGenerator:
    """修复生成器测试"""

    @pytest.fixture
    def generator(self):
        """创建修复生成器实例"""
        return FixGenerator()

    @pytest.fixture
    def sample_root_cause(self):
        """创建示例根因"""
        return RootCause(
            root_cause_type=RootCauseType.DEPENDENCY_ISSUE,
            confidence=0.85,
            title="缺少库依赖",
            description="链接时找不到foo函数的定义",
            responsible_files=["src/foo.cpp", "include/foo.h"],
            evidence=["undefined reference to `foo'"],
            suggested_fixes=["添加foo.cpp到编译列表"],
        )

    def test_generate_fix_with_rules(self, generator, sample_root_cause):
        """测试基于规则的修复生成"""
        import asyncio

        # 不使用AI，只使用规则
        suggestions = asyncio.run(generator.generate_fix(
            root_cause=sample_root_cause,
            use_ai=False,
        ))

        assert len(suggestions) > 0
        assert all(isinstance(s, FixSuggestion) for s in suggestions)
        assert all(s.confidence > 0 for s in suggestions)

    def test_generate_fix_for_dependency_issue(self, generator):
        """测试依赖问题的修复生成"""
        import asyncio

        root_cause = RootCause(
            root_cause_type=RootCauseType.DEPENDENCY_ISSUE,
            confidence=0.9,
            title="链接错误",
            description="undefined reference",
            responsible_files=["main.cpp"],
        )

        suggestions = asyncio.run(generator.generate_fix(
            root_cause=root_cause,
            use_ai=False,
        ))

        assert len(suggestions) > 0
        # 应该有依赖更新相关的建议
        assert any(s.fix_type == FixType.DEPENDENCY_UPDATE for s in suggestions)

    def test_generate_fix_for_configuration_issue(self, generator):
        """测试配置问题的修复生成"""
        import asyncio

        root_cause = RootCause(
            root_cause_type=RootCauseType.CONFIGURATION_ISSUE,
            confidence=0.8,
            title="CMake配置错误",
            description="CMakeLists.txt配置问题",
            responsible_files=["CMakeLists.txt"],
        )

        suggestions = asyncio.run(generator.generate_fix(
            root_cause=root_cause,
            use_ai=False,
        ))

        assert len(suggestions) > 0
        assert any(s.fix_type == FixType.CONFIG_CHANGE for s in suggestions)

    def test_generate_fix_for_code_defect(self, generator):
        """测试代码缺陷的修复生成"""
        import asyncio

        root_cause = RootCause(
            root_cause_type=RootCauseType.CODE_DEFECT,
            confidence=0.7,
            title="逻辑错误",
            description="测试断言失败",
            responsible_files=["src/calculator.cpp"],
        )

        suggestions = asyncio.run(generator.generate_fix(
            root_cause=root_cause,
            use_ai=False,
        ))

        assert len(suggestions) > 0
        assert any(s.fix_type == FixType.CODE_CHANGE for s in suggestions)

    def test_rank_suggestions(self, generator):
        """测试建议排序"""
        suggestions = [
            FixSuggestion(
                suggestion_id="fix_1",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.TRIVIAL,
                title="简单修复",
                description="...",
                rationale="简单的问题，容易修复",
                confidence=0.6,
                risk_level="low",
                verification_steps=[],
                auto_applicable=True,
            ),
            FixSuggestion(
                suggestion_id="fix_2",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.COMPLEX,
                title="复杂修复",
                description="...",
                rationale="复杂的架构问题，需要仔细设计",
                confidence=0.6,
                risk_level="high",
                verification_steps=[],
                auto_applicable=False,
            ),
        ]

        ranked = generator.rank_suggestions(suggestions, prioritize_auto_applicable=True)

        # 简单且可自动应用的应该排在前面
        assert ranked[0].suggestion_id == "fix_1"
        assert ranked[1].suggestion_id == "fix_2"

    def test_rank_suggestions_by_confidence(self, generator):
        """测试按置信度排序"""
        suggestions = [
            FixSuggestion(
                suggestion_id="fix_low",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.SIMPLE,
                title="低置信度",
                description="...",
                rationale="不太确定的修复方案",
                confidence=0.5,
                risk_level="low",
                verification_steps=[],
            ),
            FixSuggestion(
                suggestion_id="fix_high",
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.SIMPLE,
                title="高置信度",
                description="...",
                rationale="确定的修复方案",
                confidence=0.9,
                risk_level="low",
                verification_steps=[],
            ),
        ]

        ranked = generator.rank_suggestions(suggestions)

        assert ranked[0].suggestion_id == "fix_high"
        assert ranked[1].suggestion_id == "fix_low"

    @pytest.mark.asyncio
    async def test_generate_fix_with_ai_mock(self, generator, sample_root_cause):
        """测试AI修复生成（模拟）"""
        # 模拟LLM响应
        mock_response = """```json
        {
          "suggestions": [
            {
              "fix_type": "dependency_update",
              "complexity": "simple",
              "title": "添加缺失的源文件",
              "description": "将foo.cpp添加到CMakeLists.txt",
              "rationale": "链接器找不到foo函数的定义",
              "code_changes": [],
              "commands": ["cmake ..", "make"],
              "risk_level": "low",
              "side_effects": [],
              "verification_steps": ["重新构建", "运行测试"],
              "expected_outcome": "链接成功",
              "estimated_time": "30分钟",
              "auto_applicable": false
            }
          ]
        }
        ```"""

        with patch.object(generator.llm_service, 'is_available', return_value=True), \
             patch.object(generator.llm_service, 'generate', new=AsyncMock(return_value=mock_response)):

            suggestions = await generator.generate_fix(
                root_cause=sample_root_cause,
                use_ai=True,
            )

            assert len(suggestions) > 0
            assert suggestions[0].fix_type == FixType.DEPENDENCY_UPDATE
            assert suggestions[0].complexity == FixComplexity.SIMPLE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
