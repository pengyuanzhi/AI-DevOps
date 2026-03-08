"""
GitLab Webhook 端点

接收并处理来自 GitLab 的 webhook 事件
"""

from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from src.utils.logger import get_logger
from src.utils.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/webhook", tags=["Webhook"])

# 全局 GitLab 客户端（延迟初始化）
_gitlab_client: Optional["GitLabClient"] = None


def get_gitlab_client():
    """获取 GitLab 客户端实例"""
    global _gitlab_client
    if _gitlab_client is None:
        from src.integrations.gitlab import get_gitlab_client

        _gitlab_client = get_gitlab_client(
            url=settings.gitlab_url,
            token=settings.gitlab_token,
        )
    return _gitlab_client


class GitLabEvent(BaseModel):
    """GitLab Webhook 事件模型"""

    object_kind: str = Field(..., description="事件类型")
    event_type: str | None = Field(None, description="事件类型（某些事件）")


class WebhookResponse(BaseModel):
    """Webhook 响应模型"""

    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")
    event_type: str = Field(..., description="事件类型")


@router.post("/gitlab", response_model=WebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def handle_gitlab_webhook(request: Request) -> WebhookResponse:
    """
    处理 GitLab Webhook 事件

    接收来自 GitLab 的 webhook 事件，并根据事件类型进行路由处理

    事件类型:
    - merge_request: 合并请求事件
    - pipeline: 流水线事件
    - push: 推送事件

    Returns:
        WebhookResponse: 处理结果
    """
    try:
        # 解析 webhook 事件
        event_data = await request.json()

        # 记录接收到的事件
        logger.info(
            "webhook_event_received",
            object_kind=event_data.get("object_kind"),
            event_type=event_data.get("event_type"),
        )

        # 创建事件对象
        event = GitLabEvent(**event_data)

        # 根据事件类型路由到不同的处理器
        if event.object_kind == "merge_request":
            return await handle_merge_request_event(event_data)

        elif event.object_kind == "pipeline":
            return await handle_pipeline_event(event_data)

        elif event.object_kind == "push":
            return await handle_push_event(event_data)

        else:
            logger.info(
                "unhandled_event_type",
                object_kind=event.object_kind,
            )
            return WebhookResponse(
                status="ignored",
                message=f"事件类型 '{event.object_kind}' 暂不支持",
                event_type=event.object_kind,
            )

    except Exception as e:
        logger.error(
            "webhook_processing_error",
            error=str(e),
            exc_info=e,
        )
        return WebhookResponse(
            status="error",
            message=f"处理 webhook 时出错: {str(e)}",
            event_type="unknown",
        )


async def handle_merge_request_event(event_data: Dict[str, Any]) -> WebhookResponse:
    """
    处理合并请求事件

    Args:
        event_data: 事件数据

    Returns:
        WebhookResponse
    """
    action = event_data.get("object_attributes", {}).get("action")
    mr_title = event_data.get("object_attributes", {}).get("title")
    project_id = event_data.get("project", {}).get("id")
    mr_iid = event_data.get("object_attributes", {}).get("iid")

    logger.info(
        "merge_request_event",
        action=action,
        title=mr_title,
        project_id=project_id,
        mr_iid=mr_iid,
    )

    # 只处理打开、更新和重新打开的 MR
    if action not in ["open", "update", "reopen"]:
        return WebhookResponse(
            status="ignored",
            message=f"MR action '{action}' 不需要处理",
            event_type="merge_request",
        )

    try:
        # 获取 GitLab 客户端
        client = get_gitlab_client()
        from src.integrations.gitlab import MROperations

        mr_ops = MROperations(client)

        # 检测项目类型（Python 或 C++）
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=project_id,
            mr_iid=mr_iid,
        )

        logger.info(
            "project_type_detected",
            project_id=project_id,
            mr_iid=mr_iid,
            project_type=project_type,
        )

        # 根据项目类型路由到相应的处理器
        if project_type == "cpp":
            return await _handle_cpp_mr(
                mr_ops=mr_ops,
                event_data=event_data,
                project_id=project_id,
                mr_iid=mr_iid,
                mr_title=mr_title,
            )
        elif project_type == "python":
            return await _handle_python_mr(
                mr_ops=mr_ops,
                event_data=event_data,
                project_id=project_id,
                mr_iid=mr_iid,
                mr_title=mr_title,
            )
        else:
            return WebhookResponse(
                status="ignored",
                message=f"未检测到支持的代码文件（Python 或 C++）",
                event_type="merge_request",
            )

    except Exception as e:
        logger.error(
            "failed_to_process_mr_event",
            project_id=project_id,
            mr_iid=mr_iid,
            error=str(e),
            exc_info=e,
        )
        return WebhookResponse(
            status="error",
            message=f"处理 MR 失败: {str(e)}",
            event_type="merge_request",
        )


async def _detect_project_type(
    mr_ops: "MROperations",
    project_id: int,
    mr_iid: int,
) -> str:
    """
    检测项目类型

    Args:
        mr_ops: MR 操作客户端
        project_id: 项目 ID
        mr_iid: MR IID

    Returns:
        str: 项目类型 ('cpp', 'python', 'unknown')
    """
    # 获取变更的文件列表，检查所有支持的文件类型
    cpp_extensions = [".cpp", ".h", ".hpp", ".cc", ".cxx", ".c"]
    python_extensions = [".py"]

    all_extensions = cpp_extensions + python_extensions

    changed_files = await mr_ops.get_changed_files(
        project_id=project_id,
        mr_iid=mr_iid,
        extensions=all_extensions,
    )

    cpp_count = sum(
        1
        for f in changed_files
        if any(f["new_path"].endswith(ext) for ext in cpp_extensions)
    )
    python_count = sum(
        1
        for f in changed_files
        if any(f["new_path"].endswith(ext) for ext in python_extensions)
    )

    logger.info(
        "project_file_counts",
        cpp_files=cpp_count,
        python_files=python_count,
    )

    # 根据文件数量判断项目类型
    if cpp_count > 0:
        return "cpp"
    elif python_count > 0:
        return "python"
    else:
        return "unknown"


async def _handle_cpp_mr(
    mr_ops: "MROperations",
    event_data: Dict[str, Any],
    project_id: int,
    mr_iid: int,
    mr_title: str,
) -> WebhookResponse:
    """
    处理 C++ 项目 MR

    Args:
        mr_ops: MR 操作客户端
        event_data: 事件数据
        project_id: 项目 ID
        mr_iid: MR IID
        mr_title: MR 标题

    Returns:
        WebhookResponse
    """
    from src.services.cpp_gitlab_service import get_cpp_gitlab_service

    try:
        # 获取 C++ GitLab 服务
        cpp_service = get_cpp_gitlab_service()

        # 确保 MR 操作客户端已配置
        if cpp_service.mr_operations is None:
            cpp_service.mr_operations = mr_ops

        # 处理 MR
        logger.info(
            "processing_cpp_mr",
            project_id=project_id,
            mr_iid=mr_iid,
        )

        result = await cpp_service.process_merge_request(
            project_id=project_id,
            mr_iid=mr_iid,
            options={
                "generate_tests": True,
                "run_review": True,
                "post_comments": True,
            },
        )

        if result.success:
            return WebhookResponse(
                status="completed",
                message=f"C++ MR 处理完成: 生成 {result.total_tests_generated} 个测试，审查 {result.total_reviews_done} 个文件",
                event_type="merge_request",
            )
        else:
            return WebhookResponse(
                status="partial_success",
                message=f"C++ MR 部分处理完成，遇到 {len(result.errors)} 个错误",
                event_type="merge_request",
            )

    except Exception as e:
        logger.error(
            "failed_to_handle_cpp_mr",
            project_id=project_id,
            mr_iid=mr_iid,
            error=str(e),
            exc_info=e,
        )
        raise


async def _handle_python_mr(
    mr_ops: "MROperations",
    event_data: Dict[str, Any],
    project_id: int,
    mr_iid: int,
    mr_title: str,
) -> WebhookResponse:
    """
    处理 Python 项目 MR

    Args:
        mr_ops: MR 操作客户端
        event_data: 事件数据
        project_id: 项目 ID
        mr_iid: MR IID
        mr_title: MR 标题

    Returns:
        WebhookResponse
    """
    # 获取变更的文件列表
    changed_files = await mr_ops.get_changed_files(
        project_id=project_id,
        mr_iid=mr_iid,
        extensions=[".py"],
    )

    logger.info(
        "mr_files_analyzed",
        project_id=project_id,
        mr_iid=mr_iid,
        changed_files_count=len(changed_files),
    )

    # TODO: 在后续 Phase 中调用 Python 特定的服务
    # Phase 3: Python 测试生成服务
    # Phase 4: Python 代码审查服务

    return WebhookResponse(
        status="queued",
        message=f"Python MR '{mr_title}' 已加入处理队列（{len(changed_files)} 个 Python 文件）",
        event_type="merge_request",
    )


async def handle_pipeline_event(event_data: Dict[str, Any]) -> WebhookResponse:
    """
    处理流水线事件

    Args:
        event_data: 事件数据

    Returns:
        WebhookResponse
    """
    pipeline_status = event_data.get("object_attributes", {}).get("status")
    project_id = event_data.get("project", {}).get("id")

    logger.info(
        "pipeline_event",
        status=pipeline_status,
        project_id=project_id,
    )

    return WebhookResponse(
        status="received",
        message=f"Pipeline 状态: {pipeline_status}",
        event_type="pipeline",
    )


async def handle_push_event(event_data: Dict[str, Any]) -> WebhookResponse:
    """
    处理推送事件

    Args:
        event_data: 事件数据

    Returns:
        WebhookResponse
    """
    ref = event_data.get("ref")
    project_id = event_data.get("project", {}).get("id")

    logger.info(
        "push_event",
        ref=ref,
        project_id=project_id,
    )

    return WebhookResponse(
        status="received",
        message=f"推送到分支: {ref}",
        event_type="push",
    )
