"""
WebSocket API endpoints

提供实时通信端点，用于构建日志流、测试结果推送等
"""
import json
import asyncio
from typing import Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from pydantic import BaseModel

from src.services.websocket.manager import manager
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str
    data: dict


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    subscribe: Optional[str] = Query(None, description="初始订阅的主题，多个主题用逗号分隔"),
    token: Optional[str] = Query(None, description="认证令牌（可选）"),
):
    """
    WebSocket连接端点

    支持的主题格式：
    - build:{job_id} - 构建日志流
    - test:{test_run_id} - 测试结果流
    - pipeline:{pipeline_id} - 流水线状态更新
    - project:{project_id} - 项目整体更新

    消息类型：
    - log: 日志消息
    - status_update: 状态更新
    - progress: 进度更新
    - error: 错误消息

    示例：
    - ws://localhost:8000/api/v1/ws/connect?subscribe=build:123,test:456
    """
    # TODO: 验证token（如果需要）
    connection_id = None

    try:
        # 接受连接
        connection_id = await manager.connect(websocket)

        # 处理初始订阅
        if subscribe:
            topics = [t.strip() for t in subscribe.split(",")]
            for topic in topics:
                manager.subscribe(connection_id, topic)

        # 发送欢迎消息
        await manager.send_personal_message(
            {
                "type": "connected",
                "connection_id": connection_id,
                "message": "WebSocket connection established",
            },
            connection_id,
        )

        # 消息循环
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # 处理不同类型的消息
                message_type = message.get("type")

                if message_type == "subscribe":
                    # 订阅主题
                    topic = message.get("topic")
                    if topic:
                        manager.subscribe(connection_id, topic)
                        await manager.send_personal_message(
                            {
                                "type": "subscribed",
                                "topic": topic,
                            },
                            connection_id,
                        )

                elif message_type == "unsubscribe":
                    # 取消订阅
                    topic = message.get("topic")
                    if topic:
                        manager.unsubscribe(topic, connection_id)
                        await manager.send_personal_message(
                            {
                                "type": "unsubscribed",
                                "topic": topic,
                            },
                            connection_id,
                        )

                elif message_type == "ping":
                    # 心跳检测
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                        connection_id,
                    )

                elif message_type == "echo":
                    # 回显消息（用于测试）
                    await manager.send_personal_message(
                        {
                            "type": "echo",
                            "data": message.get("data"),
                        },
                        connection_id,
                    )

                else:
                    # 未知消息类型
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        },
                        connection_id,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    },
                    connection_id,
                )
            except Exception as e:
                logger.error(
                    "websocket_message_handling_error",
                    connection_id=connection_id,
                    error=str(e),
                )
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": f"Error processing message: {str(e)}",
                    },
                    connection_id,
                )

    except WebSocketDisconnect:
        logger.info(
            "websocket_client_disconnected",
            connection_id=connection_id,
        )
    except Exception as e:
        logger.error(
            "websocket_connection_error",
            connection_id=connection_id,
            error=str(e),
        )
    finally:
        # 清理连接
        if connection_id:
            await manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息

    Returns:
        连接统计信息
    """
    return {
        "active_connections": manager.get_connection_count(),
        "topics": {
            topic: len(subscribers)
            for topic, subscribers in manager.topic_subscriptions.items()
        },
    }


@router.post("/broadcast")
async def broadcast_message(message: WebSocketMessage, topic: Optional[str] = None):
    """
    广播消息到所有连接（或指定主题的订阅者）

    Args:
        message: 要广播的消息
        topic: 可选的主题名称

    Returns:
        广播结果
    """
    success_count = await manager.broadcast(message.data, topic=topic)

    return {
        "success": True,
        "message_type": message.type,
        "topic": topic,
        "sent_count": success_count,
    }


@router.post("/build/{job_id}/log")
async def send_build_log(job_id: int, level: str, message: str):
    """
    发送构建日志（用于构建服务）

    Args:
        job_id: 构建任务ID
        level: 日志级别（info, warning, error）
        message: 日志消息

    Returns:
        发送结果
    """
    topic = f"build:{job_id}"
    success_count = await manager.send_log(topic, level, message, job_id=job_id)

    return {
        "success": True,
        "job_id": job_id,
        "sent_count": success_count,
    }


@router.post("/test/{test_run_id}/result")
async def send_test_result(test_run_id: int, status: str, **extra_data):
    """
    发送测试结果更新（用于测试服务）

    Args:
        test_run_id: 测试运行ID
        status: 测试状态
        **extra_data: 额外的测试数据

    Returns:
        发送结果
    """
    topic = f"test:{test_run_id}"
    success_count = await manager.send_status_update(topic, status, test_run_id=test_run_id, **extra_data)

    return {
        "success": True,
        "test_run_id": test_run_id,
        "sent_count": success_count,
    }


@router.post("/pipeline/{pipeline_id}/status")
async def send_pipeline_status(pipeline_id: str, status: str, **extra_data):
    """
    发送流水线状态更新

    Args:
        pipeline_id: 流水线ID
        status: 流水线状态
        **extra_data: 额外的流水线数据

    Returns:
        发送结果
    """
    topic = f"pipeline:{pipeline_id}"
    success_count = await manager.send_status_update(topic, status, pipeline_id=pipeline_id, **extra_data)

    return {
        "success": True,
        "pipeline_id": pipeline_id,
        "sent_count": success_count,
    }
