"""
Natural Language Configuration API

Endpoints for generating CI/CD configurations from natural language.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List

from ...services.ai.nl_config.service import nl_config_service


router = APIRouter(prefix="/nl-config", tags=["Natural Language Config"])


class GenerateConfigRequest(BaseModel):
    """Request to generate CI/CD configuration"""
    description: str = Field(..., description="Natural language description of desired CI/CD pipeline", min_length=10)
    project_name: str = Field(default="project", description="Name of the project")
    use_ai_enhancement: bool = Field(default=True, description="Use AI for enhanced understanding and explanation")


class GenerateConfigResponse(BaseModel):
    """Response with generated configuration"""
    success: bool
    config: Optional[str] = None
    intent: Optional[dict] = None
    validation: Optional[dict] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class OptimizeConfigRequest(BaseModel):
    """Request to optimize CI/CD configuration"""
    current_config: str = Field(..., description="Current YAML configuration")
    optimization_goals: List[str] = Field(
        default=["speed"],
        description="Optimization goals (speed, cost, reliability)"
    )


class OptimizeConfigResponse(BaseModel):
    """Response with optimized configuration"""
    success: bool
    optimized_config: Optional[str] = None
    suggestions: Optional[List[dict]] = None
    error: Optional[str] = None


class ExplainConfigRequest(BaseModel):
    """Request to explain CI/CD configuration"""
    yaml_content: str = Field(..., description="YAML configuration to explain")


class ExplainConfigResponse(BaseModel):
    """Response with configuration explanation"""
    success: bool
    explanation: Optional[dict] = None
    error: Optional[str] = None


class CompleteConfigRequest(BaseModel):
    """Request to complete partial configuration"""
    partial_config: str = Field(..., description="Partial YAML configuration")
    user_goal: str = Field(..., description="Description of what needs to be completed", min_length=5)


class CompleteConfigResponse(BaseModel):
    """Response with completed configuration"""
    success: bool
    config: Optional[str] = None
    validation_errors: Optional[List[str]] = None
    error: Optional[str] = None


@router.post("/generate", response_model=GenerateConfigResponse)
async def generate_config(request: GenerateConfigRequest):
    """
    Generate CI/CD configuration from natural language

    Converts natural language description into a complete .gitlab-ci.yml configuration.

    **Example descriptions:**
    - "Build my C++ project with CMake, run tests with coverage, and deploy to staging"
    - "Use Qt framework, build in release mode, enable ccache for faster builds"
    - "Compile with QMake, run Qt tests, send notifications on failure"
    """
    result = await nl_config_service.generate_config(
        description=request.description,
        project_name=request.project_name,
        use_ai_enhancement=request.use_ai_enhancement,
    )

    if result["success"]:
        return GenerateConfigResponse(
            success=True,
            config=result["config"],
            intent={
                "build": result["intent"].build.__dict__,
                "test": result["intent"].test.__dict__,
                "deploy": result["intent"].deploy.__dict__,
                "cache": result["intent"].cache.__dict__,
                "notification": result["intent"].notification.__dict__,
            },
            validation=result["validation"],
            explanation=result.get("explanation"),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to generate configuration"),
        )


@router.post("/optimize", response_model=OptimizeConfigResponse)
async def optimize_config(request: OptimizeConfigRequest):
    """
    Optimize existing CI/CD configuration

    Analyzes current configuration and provides optimization suggestions
    and optimized version based on specified goals.

    **Optimization goals:**
    - `speed`: Faster pipeline execution (caching, parallelization, etc.)
    - `cost`: Reduced resource usage (shorter expiration times, fewer jobs, etc.)
    - `reliability`: Better error handling and recovery (retries, fallbacks, etc.)
    """
    result = await nl_config_service.optimize_config(
        current_config=request.current_config,
        optimization_goals=request.optimization_goals,
    )

    if result["success"]:
        return OptimizeConfigResponse(
            success=True,
            optimized_config=result.get("optimized_config"),
            suggestions=result.get("suggestions"),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to optimize configuration"),
        )


@router.post("/explain", response_model=ExplainConfigResponse)
async def explain_config(request: ExplainConfigRequest):
    """
    Explain CI/CD configuration

    Provides a detailed breakdown of what the configuration does,
    including stages, jobs, and their purposes.
    """
    result = nl_config_service.explain_config(request.yaml_content)

    if result["success"]:
        return ExplainConfigResponse(
            success=True,
            explanation=result["explanation"],
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to explain configuration"),
        )


@router.post("/complete", response_model=CompleteConfigResponse)
async def complete_config(request: CompleteConfigRequest):
    """
    Complete partial CI/CD configuration

    Takes a partial configuration and completes it based on user goals.
    Useful when you have a basic config and want to add specific features.
    """
    result = await nl_config_service.complete_config(
        partial_config=request.partial_config,
        user_goal=request.user_goal,
    )

    return CompleteConfigResponse(
        success=result["success"],
        config=result.get("config"),
        validation_errors=result.get("validation_errors"),
        error=result.get("error"),
    )


@router.get("/examples")
async def get_examples():
    """
    Get example natural language descriptions

    Returns a list of example descriptions that demonstrate
    different CI/CD configurations.
    """
    return {
        "examples": [
            {
                "name": "Basic CMake Build",
                "description": "Build my C++ project using CMake in release mode",
            },
            {
                "name": "Full Pipeline with Tests",
                "description": "Build with CMake, run all unit tests with coverage, and deploy to production",
            },
            {
                "name": "Qt Application",
                "description": "Use QMake to build Qt application, run Qt tests, enable ccache",
            },
            {
                "name": "Multi-Environment",
                "description": "Build and test code, deploy to dev and staging environments automatically, production requires approval",
            },
            {
                "name": "Fast Feedback",
                "description": "Use ccache and build cache to speed up compilation, run tests in parallel, send Slack notification on failure",
            },
            {
                "name": "Nightly Build",
                "description": "Run full build with all tests and generate coverage report every night",
            },
        ]
    }
