"""CI/CD configuration models."""

from src.models.cicd.requests import (
    CICDConfigRequest,
    OptimizationRequest,
    ParsedRequirements,
)
from src.models.cicd.results import (
    CICDConfigResult,
    OptimizationResult,
    TemplateInfo,
)
from src.models.cicd.templates import (
    Template,
    TemplateCategory,
)

__all__ = [
    # Requests
    "CICDConfigRequest",
    "OptimizationRequest",
    "ParsedRequirements",
    # Results
    "CICDConfigResult",
    "OptimizationResult",
    "TemplateInfo",
    # Templates
    "Template",
    "TemplateCategory",
]
