"""CI/CD configuration result models."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TemplateInfo:
    """模板信息."""

    name: str
    display_name: str
    description: str
    category: str
    tags: List[str] = field(default_factory=list)
    estimated_build_time: Optional[str] = None


@dataclass
class CICDConfigResult:
    """CI/CD配置生成结果.

    包含生成的配置、说明和相关元数据。
    """

    config: str  # 生成的.gitlab-ci.yml内容
    explanation: str  # 配置说明
    parsed_requirements: dict  # 解析出的需求
    stages: List[str]  # 配置包含的stages
    template_used: Optional[str] = None  # 使用的基础模板
    optimization_applied: List[str] = field(default_factory=list)  # 应用的优化
    warnings: List[str] = field(default_factory=list)  # 警告信息
    estimated_time_saved: Optional[str] = None  # 预计节省的时间

    def to_dict(self) -> dict:
        """转换为字典格式."""
        return {
            "config": self.config,
            "explanation": self.explanation,
            "parsed_requirements": self.parsed_requirements,
            "stages": self.stages,
            "template_used": self.template_used,
            "optimization_applied": self.optimization_applied,
            "warnings": self.warnings,
            "estimated_time_saved": self.estimated_time_saved,
        }


@dataclass
class OptimizationSuggestion:
    """优化建议."""

    type: str  # speed, cost, reliability, etc.
    description: str  # 建议描述
    impact: str  # 预期影响（如"减少30%构建时间"）
    priority: str  # high, medium, low
    code_change: Optional[str] = None  # 需要修改的代码片段


@dataclass
class OptimizationResult:
    """配置优化结果."""

    optimized_config: str  # 优化后的配置
    improvements: List[str]  # 改进点列表
    suggestions: List[OptimizationSuggestion]  # 详细建议
    diff: Optional[str] = None  # 配置变更diff
    before_metrics: dict = field(default_factory=dict)  # 优化前指标
    after_metrics: dict = field(default_factory=dict)  # 优化后指标
    estimated_improvement: Optional[str] = None  # 预计整体改进
