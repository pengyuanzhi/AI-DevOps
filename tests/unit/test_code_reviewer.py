"""
代码审查 Agent 单元测试
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.core.agents import (
    CodeReviewResult,
    CodeReviewerAgent,
    FileReview,
    Issue,
    IssueSeverity,
    ReviewDimension,
    RiskLevel,
    get_code_reviewer,
)


class TestIssue:
    """问题测试"""

    def test_issue_creation(self):
        """测试创建问题"""
        issue = Issue(
            severity=IssueSeverity.HIGH,
            category=ReviewDimension.SECURITY,
            file="test.py",
            line=10,
            message="SQL injection risk",
            suggestion="Use parameterized queries",
            source="static",
        )

        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == ReviewDimension.SECURITY
        assert issue.file == "test.py"
        assert issue.line == 10

    def test_issue_to_dict(self):
        """测试问题转换为字典"""
        issue = Issue(
            severity=IssueSeverity.MEDIUM,
            category=ReviewDimension.QUALITY,
            file="example.py",
            line=5,
            message="Missing docstring",
            source="static",
        )

        data = issue.to_dict()

        assert data["severity"] == "medium"
        assert data["category"] == "quality"
        assert data["file"] == "example.py"
        assert data["line"] == 5


class TestFileReview:
    """文件审查测试"""

    def test_file_review_creation(self):
        """测试创建文件审查"""
        review = FileReview(file_path="test.py")

        assert review.file_path == "test.py"
        assert review.quality_score == 0.0
        assert review.complexity_score == 0.0
        assert review.overall_score == 0.0
        assert review.total_issues == 0

    def test_add_issue(self):
        """测试添加问题"""
        review = FileReview(file_path="test.py")

        issue = Issue(
            severity=IssueSeverity.HIGH,
            category=ReviewDimension.SECURITY,
            file="test.py",
            line=10,
            message="Test issue",
            source="static",
        )

        review.add_issue(issue)

        assert len(review.issues) == 1
        assert review.high_count == 1

    def test_issue_counts(self):
        """测试问题计数"""
        review = FileReview(file_path="test.py")

        # 添加不同严重性的问题
        review.add_issue(
            Issue(
                severity=IssueSeverity.CRITICAL,
                category=ReviewDimension.SECURITY,
                file="test.py",
                line=1,
                message="Critical issue",
                source="static",
            )
        )
        review.add_issue(
            Issue(
                severity=IssueSeverity.HIGH,
                category=ReviewDimension.QUALITY,
                file="test.py",
                line=2,
                message="High issue",
                source="static",
            )
        )
        review.add_issue(
            Issue(
                severity=IssueSeverity.MEDIUM,
                category=ReviewDimension.PERFORMANCE,
                file="test.py",
                line=3,
                message="Medium issue",
                source="static",
            )
        )
        review.add_issue(
            Issue(
                severity=IssueSeverity.LOW,
                category=ReviewDimension.MAINTAINABILITY,
                file="test.py",
                line=4,
                message="Low issue",
                source="static",
            )
        )

        assert review.critical_count == 1
        assert review.high_count == 1
        assert review.medium_count == 1
        assert review.low_count == 1
        assert review.total_issues == 4


class TestCodeReviewResult:
    """代码审查结果测试"""

    def test_result_creation(self):
        """测试创建结果"""
        result = CodeReviewResult(
            project_id=123,
            mr_iid=1,
        )

        assert result.project_id == 123
        assert result.mr_iid == 1
        assert result.status == "pending"
        assert result.risk_level == RiskLevel.LOW

    def test_calculate_risk_level(self):
        """测试计算风险等级"""
        result = CodeReviewResult(project_id=123, mr_iid=1)

        # 添加文件审查
        file_review = FileReview(file_path="test.py")

        # 添加高严重性问题
        for i in range(5):
            file_review.add_issue(
                Issue(
                    severity=IssueSeverity.HIGH,
                    category=ReviewDimension.QUALITY,
                    file="test.py",
                    line=i,
                    message=f"High issue {i}",
                    source="static",
                )
            )

        result.file_reviews.append(file_review)

        # 应该是严重风险（5个高严重性问题）
        risk = result.calculate_risk_level()
        assert risk == RiskLevel.CRITICAL

    def test_calculate_risk_level_critical(self):
        """测试计算严重风险等级"""
        result = CodeReviewResult(project_id=123, mr_iid=1)

        file_review = FileReview(file_path="test.py")

        # 添加严重问题
        file_review.add_issue(
            Issue(
                severity=IssueSeverity.CRITICAL,
                category=ReviewDimension.SECURITY,
                file="test.py",
                line=1,
                message="Critical issue",
                source="static",
            )
        )

        result.file_reviews.append(file_review)

        risk = result.calculate_risk_level()
        assert risk == RiskLevel.CRITICAL


class TestCodeReviewerAgent:
    """代码审查代理测试"""

    def test_agent_initialization(self):
        """测试代理初始化"""
        # 不需要 LLM 客户端也可以初始化（用于静态分析）
        agent = CodeReviewerAgent(
            llm_client=None,
            pylint_checker=None,
            radon_checker=None,
        )

        assert agent is not None
        assert agent.llm_client is None
        assert agent.pylint_checker is None
        assert agent.radon_checker is None

    @pytest.mark.asyncio
    async def test_review_merge_request_without_llm(self):
        """测试没有 LLM 时审查 MR"""
        agent = CodeReviewerAgent(
            llm_client=None,
            pylint_checker=None,
            radon_checker=None,
        )

        diff = "diff --git a/test.py b/test.py"
        files_content = {"test.py": "def foo(): pass"}

        result = await agent.review_merge_request(
            project_id=123,
            mr_iid=1,
            diff=diff,
            files_content=files_content,
        )

        # 应该返回结果，但没有 AI 审查
        assert isinstance(result, CodeReviewResult)
        assert result.project_id == 123
        assert result.mr_iid == 1
        assert result.status == "completed"  # 即使没有检查器，也应该完成

    def test_map_pylint_severity(self):
        """测试映射 Pylint 严重性"""
        agent = CodeReviewerAgent()

        # 测试各种类别
        assert agent._map_pylint_severity("fatal") == IssueSeverity.CRITICAL
        assert agent._map_pylint_severity("error") == IssueSeverity.HIGH
        assert agent._map_pylint_severity("warning") == IssueSeverity.MEDIUM
        assert agent._map_pylint_severity("convention") == IssueSeverity.LOW
        assert agent._map_pylint_severity("info") == IssueSeverity.INFO

    def test_map_pylint_category(self):
        """测试映射 Pylint 类别"""
        agent = CodeReviewerAgent()

        # 安全相关
        assert agent._map_pylint_category("hardcoded-password") == ReviewDimension.SECURITY

        # 性能相关
        assert agent._map_pylint_category("broad-except") == ReviewDimension.PERFORMANCE

        # 默认为质量
        assert agent._map_pylint_category("missing-docstring") == ReviewDimension.QUALITY

    def test_calculate_file_score(self):
        """测试计算文件分数"""
        agent = CodeReviewerAgent()

        file_review = FileReview(file_path="test.py")
        file_review.quality_score = 8.0
        file_review.complexity_score = 5.0

        score = agent._calculate_file_score(file_review)

        # 应该接近质量分数
        assert score > 0
        assert score <= 10

    def test_calculate_file_score_high_complexity(self):
        """测试计算高复杂度文件分数"""
        agent = CodeReviewerAgent()

        file_review = FileReview(file_path="test.py")
        file_review.quality_score = 8.0
        file_review.complexity_score = 15.0  # 高复杂度

        score = agent._calculate_file_score(file_review)

        # 高复杂度应该导致分数降低
        assert score < 8.0

    def test_calculate_dimension_scores(self):
        """测试计算维度分数"""
        agent = CodeReviewerAgent()

        file_reviews = [
            FileReview(file_path="test1.py"),
            FileReview(file_path="test2.py"),
        ]

        file_reviews[0].quality_score = 8.0
        file_reviews[0].complexity_score = 5.0
        file_reviews[1].quality_score = 9.0
        file_reviews[1].complexity_score = 3.0

        scores = agent._calculate_dimension_scores(file_reviews)

        # 应该有所有维度
        assert "quality" in scores
        assert "maintainability" in scores
        assert scores["quality"] > 0

    def test_calculate_overall_score(self):
        """测试计算总体分数"""
        agent = CodeReviewerAgent()

        dimension_scores = {
            "quality": 8.0,
            "security": 7.0,
            "performance": 6.0,
            "maintainability": 9.0,
        }

        overall = agent._calculate_overall_score(dimension_scores)

        # 应该在合理范围内
        assert overall > 0
        assert overall <= 10

    def test_generate_summary(self):
        """测试生成摘要"""
        agent = CodeReviewerAgent()

        result = CodeReviewResult(project_id=123, mr_iid=1)
        result.overall_score = 8.5
        result.risk_level = RiskLevel.LOW
        result.dimension_scores = {
            "quality": 8.0,
            "security": 9.0,
            "performance": 8.5,
            "maintainability": 8.0,
        }

        summary = agent._generate_summary(result, None)

        # 应该包含关键信息
        assert "总体评估" in summary
        assert "8.5" in summary
        assert "LOW" in summary

    def test_generate_recommendations(self):
        """测试生成建议"""
        agent = CodeReviewerAgent()

        # 创建有严重问题的文件审查
        file_review = FileReview(file_path="test.py")
        file_review.add_issue(
            Issue(
                severity=IssueSeverity.CRITICAL,
                category=ReviewDimension.SECURITY,
                file="test.py",
                line=1,
                message="Critical issue",
                source="static",
            )
        )

        file_review.complexity_score = 15.0  # 高复杂度

        recommendations = agent._generate_recommendations([file_review], None)

        # 应该有建议
        assert len(recommendations) > 0

    @pytest.mark.asyncio
    async def test_run_ai_review_without_llm(self):
        """测试没有 LLM 时运行 AI 审查"""
        agent = CodeReviewerAgent(llm_client=None)

        ai_review = await agent._run_ai_review("diff", [])

        assert ai_review is None

    @pytest.mark.asyncio
    async def test_run_ai_review_with_mock_llm(self):
        """测试使用 Mock LLM 运行 AI 审查"""
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(return_value="## 审查意见\n代码质量良好")

        agent = CodeReviewerAgent(llm_client=mock_llm)

        ai_review = await agent._run_ai_review("diff --git a/test.py", [])

        assert ai_review is not None
        assert "代码质量" in ai_review


class TestGetCodeReviewer:
    """测试代码审查代理单例"""

    @patch("src.core.llm.get_claude_client")
    @patch("src.core.quality.get_pylint_checker")
    @patch("src.core.quality.get_radon_checker")
    def test_singleton_pattern(self, mock_radon, mock_pylint, mock_claude):
        """测试单例模式"""
        # Mock 返回值
        mock_claude.return_value = Mock()
        mock_pylint.return_value = Mock()
        mock_radon.return_value = Mock()

        # 重置全局变量
        import src.core.agents.code_reviewer
        src.core.agents.code_reviewer._code_reviewer = None

        reviewer1 = get_code_reviewer()
        reviewer2 = get_code_reviewer()

        assert reviewer1 is reviewer2
