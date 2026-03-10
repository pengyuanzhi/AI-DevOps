"""
API v1 路由

提供版本1的API接口。
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .projects import router as projects_router
from .pipelines import router as pipelines_router
from .jobs import router as jobs_router
from .analysis import router as analysis_router
from .webhooks import router as webhooks_router
from . import build as build_module
from . import test as test_module
from . import websocket as websocket_module
from . import nl_config as nl_config_module
from . import memory_safety as memory_safety_module
from . import pipeline_maintenance as pipeline_maintenance_module
from . import ai_test as ai_test_module
from . import smart_test_selection as smart_test_selection_module

api_router = APIRouter(prefix="/api/v1")

# 注册各个模块的路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(projects_router, prefix="/projects", tags=["项目"])
api_router.include_router(pipelines_router, prefix="/pipelines", tags=["流水线"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["作业"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["AI分析"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(build_module.router, prefix="/build", tags=["构建"])
api_router.include_router(test_module.router, prefix="/test", tags=["测试"])
api_router.include_router(websocket_module.router, tags=["WebSocket"])
api_router.include_router(nl_config_module.router, tags=["Natural Language Config"])
api_router.include_router(memory_safety_module.router, tags=["Memory Safety"])
api_router.include_router(pipeline_maintenance_module.router, tags=["Pipeline Maintenance"])
api_router.include_router(ai_test_module.router, tags=["AI测试"])
api_router.include_router(smart_test_selection_module.router, prefix="/test-selection", tags=["智能测试选择"])

__all__ = ["api_router"]
