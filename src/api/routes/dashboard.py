"""
Dashboard API 路由

提供统计数据和 WebSocket 实时更新端点。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import asyncio

from src.utils.logger import get_logger
from src.services.stats_service import get_stats_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"]
)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._broadcast_task = None
        self._is_running = False

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "websocket_connected",
            client_id=id(websocket),
            total_connections=len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "websocket_disconnected",
                client_id=id(websocket),
                total_connections=len(self.active_connections)
            )

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接"""
        if not self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "websocket_send_failed",
                    client_id=id(connection),
                    error=str(e)
                )
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def start_broadcasting(self, interval: int = 1):
        """
        开始广播统计数据

        Args:
            interval: 广播间隔（秒）
        """
        if self._is_running:
            return

        self._is_running = True
        logger.info("broadcast_started", interval=interval)

        stats_service = get_stats_service()

        while self._is_running:
            try:
                stats = await stats_service.get_stats()

                # 添加类型和时间戳
                message = {
                    "type": "stats_update",
                    "timestamp": stats["data"]["timestamp"],
                    "data": stats["data"]
                }

                await self.broadcast(message)

            except Exception as e:
                logger.error(
                    "broadcast_error",
                    error=str(e),
                    exc_info=True
                )

            await asyncio.sleep(interval)

    def stop_broadcasting(self):
        """停止广播"""
        self._is_running = False
        logger.info("broadcast_stopped")


# 全局连接管理器
manager = ConnectionManager()


@router.get("/stats")
async def get_stats() -> JSONResponse:
    """
    获取统计数据

    Returns:
        包含测试、审查、MR、LLM 统计数据的 JSON 响应
    """
    try:
        stats_service = get_stats_service()
        stats = await stats_service.get_stats()

        logger.debug("stats_requested")

        return JSONResponse(content=stats)

    except Exception as e:
        logger.error(
            "stats_fetch_error",
            error=str(e),
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "STATS_FETCH_ERROR",
                    "message": "无法获取统计数据"
                }
            }
        )


@router.get("/trends")
async def get_trends(hours: int = 24) -> JSONResponse:
    """
    获取趋势数据

    Args:
        hours: 获取最近几小时的数据（默认24小时）

    Returns:
        包含趋势数据的 JSON 响应
    """
    try:
        stats_service = get_stats_service()
        trends = stats_service.get_trends(hours=hours)

        logger.debug("trends_requested", hours=hours)

        return JSONResponse(content=trends)

    except Exception as e:
        logger.error(
            "trends_fetch_error",
            error=str(e),
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "TRENDS_FETCH_ERROR",
                    "message": "无法获取趋势数据"
                }
            }
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点 - 实时统计数据推送

    连接到此端点以接收实时统计更新：
    - 客户端连接后，服务器每秒推送最新统计数据
    - 数据格式：{"type": "stats_update", "timestamp": "...", "data": {...}}

    Example:
        ```javascript
        const ws = new WebSocket('ws://localhost:8000/api/dashboard/ws');
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('Stats update:', message.data);
        };
        ```
    """
    await manager.connect(websocket)

    # 如果这是第一个连接，启动广播任务
    if len(manager.active_connections) == 1:
        # 在后台启动广播
        asyncio.create_task(manager.start_broadcasting(interval=1))

    try:
        # 发送初始数据
        stats_service = get_stats_service()
        stats = await stats_service.get_stats()

        await websocket.send_json({
            "type": "connected",
            "timestamp": stats["data"]["timestamp"],
            "data": stats["data"]
        })

        # 保持连接活跃
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()

            logger.debug(
                "websocket_message_received",
                client_id=id(websocket),
                message=data
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)

        # 如果没有活跃连接，停止广播
        if len(manager.active_connections) == 0:
            manager.stop_broadcasting()

    except Exception as e:
        logger.error(
            "websocket_error",
            client_id=id(websocket),
            error=str(e),
            exc_info=True
        )
        manager.disconnect(websocket)
