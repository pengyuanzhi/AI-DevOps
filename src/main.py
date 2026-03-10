"""
FastAPI 应用入口

AI-CICD: AI驱动的CI/CD助手
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api.middleware.auth import GitLabWebhookAuthMiddleware
from src.api.routes import cicd, dashboard, webhooks
from src.api.v1 import api_router
from src.utils.config import settings
from src.utils.logger import get_logger, setup_logging

# 设置日志
setup_logging(level=settings.log_level, log_format=settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理

    启动时创建必要的目录和资源，初始化数据库
    关闭时清理资源
    """
    # 启动时执行
    logger.info(
        "starting_ai_cicd",
        version="0.2.0",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    # 创建必要的目录
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.generated_tests_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        "directories_created",
        cache_dir=str(settings.cache_dir),
        tests_dir=str(settings.generated_tests_dir),
    )

    # 初始化数据库连接池
    from src.db.session import get_async_engine
    try:
        engine = get_async_engine()
        logger.info(
            "database_connection_initialized",
            database_url=settings.database_url.split("@")[-1] if "@" in settings.database_url else "local",
        )
    except Exception as e:
        logger.error(
            "database_initialization_failed",
            error=str(e),
        )
        raise

    yield

    # 关闭时执行
    logger.info("shutting_down_ai_cicd")

    # 关闭数据库连接
    try:
        from src.db.session import get_async_engine
        engine = get_async_engine()
        await engine.dispose()
        logger.info("database_connections_closed")
    except Exception as e:
        logger.warning(
            "database_cleanup_failed",
            error=str(e),
        )


# 创建 FastAPI 应用
app = FastAPI(
    title="AI-CICD",
    description="""AI 驱动的 CI/CD 配置生成与优化工具

## 核心功能

### 🎯 自然语言配置生成
- 用自然语言描述需求，自动生成 .gitlab-ci.yml
- 支持C++/QT项目（CMake, QMake, Google Test）
- 自动检测项目类型和依赖关系

### ⚡ 智能优化
- ccache配置（减少30-50%编译时间）
- 并行构建策略
- 缓存优化
- 资源成本优化

### 🔧 项目分析
- C++依赖关系分析
- 变更影响范围识别
- 智能测试选择（减少90%测试运行时间）
""",
    version="0.2.0",
    docs_url="/docs" if settings.log_level == "DEBUG" else None,
    redoc_url="/redoc" if settings.log_level == "DEBUG" else None,
    lifespan=lifespan,
)

# 添加 webhook 签名验证中间件
app.add_middleware(GitLabWebhookAuthMiddleware)

# 注册路由
app.include_router(api_router)
app.include_router(cicd.router)
app.include_router(webhooks.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["健康检查"])
async def health_check() -> dict[str, str]:
    """
    健康检查端点

    用于负载均衡器和容器编排系统的健康检查
    """
    return {
        "status": "healthy",
        "service": "ai-cicd",
        "version": "0.2.0",
    }


@app.get("/", tags=["根路径"])
async def root() -> dict[str, str]:
    """
    根路径端点

    返回服务基本信息
    """
    return {
        "service": "AI-CICD",
        "description": "AI 驱动的 CI/CD 配置生成与优化工具",
        "version": "0.2.0",
        "docs": "/docs" if settings.log_level == "DEBUG" else "disabled",
        "features": [
            "自然语言生成 GitLab CI 配置",
            "智能优化（ccache、并行构建、缓存）",
            "项目类型自动检测",
            "C++/QT 项目支持",
        ],
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器

    捕获所有未处理的异常，记录日志并返回友好的错误信息
    """
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "服务器内部错误，请稍后重试",
            "detail": str(exc) if settings.log_level == "DEBUG" else None,
        },
    )


# 启动事件
@app.on_event("startup")
async def startup_event() -> None:
    """应用启动时的初始化"""
    logger.info(
        "application_started",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.workers,
    )


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """应用关闭时的清理"""
    logger.info("application_shutdown")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # 开发模式，自动重载
        log_level=settings.log_level.lower(),
    )
