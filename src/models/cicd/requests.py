"""CI/CD configuration request models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParsedRequirements:
    """解析后的CI/CD需求.

    从自然语言描述中提取的结构化需求信息。
    """

    project_type: str  # cpp, qt, python, nodejs, etc.
    build_system: Optional[str] = None  # cmake, make, qmake, npm, etc.
    test_framework: Optional[str] = None  # gtest, catch2, pytest, jest, etc.
    stages: List[str] = field(default_factory=list)  # build, test, deploy, etc.
    needs_ccache: bool = False
    needs_parallel: bool = False
    deployment_targets: List[str] = field(default_factory=list)
    special_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典格式."""
        return {
            "project_type": self.project_type,
            "build_system": self.build_system,
            "test_framework": self.test_framework,
            "stages": self.stages,
            "needs_ccache": self.needs_ccache,
            "needs_parallel": self.needs_parallel,
            "deployment_targets": self.deployment_targets,
            "special_requirements": self.special_requirements,
        }


@dataclass
class CICDConfigRequest:
    """CI/CD配置生成请求.

    用户通过自然语言或结构化方式请求生成GitLab CI配置。
    """

    user_input: str  # 自然语言描述
    project_id: int  # GitLab项目ID
    branch: str = "main"  # 目标分支
    commit_config: bool = True  # 是否提交到仓库
    optimization_goals: List[str] = field(default_factory=list)
    additional_context: Optional[str] = None  # 额外的项目上下文信息


@dataclass
class OptimizationRequest:
    """CI/CD配置优化请求.

    请求优化现有的GitLab CI配置。
    """

    current_config: str  # 当前的.gitlab-ci.yml内容
    project_id: int  # GitLab项目ID
    optimization_goals: List[str] = field(default_factory=list)  # speed, cost, reliability
    project_type: Optional[str] = None  # 项目类型（用于更精确的优化）
    current_issues: List[str] = field(default_factory=list)  # 已知的当前问题
