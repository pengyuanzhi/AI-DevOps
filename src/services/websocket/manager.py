"""
WebSocket连接管理器

管理WebSocket连接，支持广播和定向消息发送
"""
import asyncio
import json
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 存储所有活动连接: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # 存储订阅关系: {topic: Set[connection_id]}
        # 支持按主题订阅，如 build:123, test:456, pipeline:789
        self.topic_subscriptions: Dict[str, Set[str]] = {}

        # 连接元数据: {connection_id: {user_id, client_info, ...}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # 连接ID计数器
        self._connection_id_counter = 0

    def _generate_connection_id(self) -> str:
        """生成唯一连接ID"""
        self._connection_id_counter += 1
        return f"conn_{self._connection_id_counter}"

    async def connect(self, websocket: WebSocket, connection_id: Optional[str] = None) -> str:
        """
        接受WebSocket连接

        Args:
            websocket: WebSocket连接对象
            connection_id: 可选的连接ID（用于重连）

        Returns:
            分配的连接ID
        """
        await websocket.accept()

        conn_id = connection_id or self._generate_connection_id()
        self.active_connections[conn_id] = websocket
        self.connection_metadata[conn_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "subscriptions": set(),
        }

        logger.info(
            f"websocket_connected connection_id={conn_id} active_connections={len(self.active_connections)}"
        )

        return conn_id

    async def disconnect(self, connection_id: str) -> None:
        """
        断开WebSocket连接

        Args:
            connection_id: 连接ID
        """
        if connection_id in self.active_connections:
            # 从所有订阅中移除（创建副本避免迭代时修改）
            if connection_id in self.connection_metadata:
                subscriptions = self.connection_metadata[connection_id].get("subscriptions", set()).copy()
                for topic in subscriptions:
                    self.unsubscribe(topic, connection_id)

            # 移除连接
            del self.active_connections[connection_id]
            del self.connection_metadata[connection_id]

            logger.info(
                f"websocket_disconnected connection_id={connection_id} active_connections={len(self.active_connections)}"
            )

    def subscribe(self, connection_id: str, topic: str) -> None:
        """
        订阅主题

        Args:
            connection_id: 连接ID
            topic: 主题名称（如 build:123, test:456, pipeline:789）
        """
        if connection_id not in self.active_connections:
            return

        if topic not in self.topic_subscriptions:
            self.topic_subscriptions[topic] = set()

        self.topic_subscriptions[topic].add(connection_id)
        self.connection_metadata[connection_id]["subscriptions"].add(topic)

        logger.debug(
            f"websocket_subscribed connection_id={connection_id} topic={topic} subscribers_count={len(self.topic_subscriptions[topic])}"
        )

    def unsubscribe(self, topic: str, connection_id: str) -> None:
        """
        取消订阅主题

        Args:
            topic: 主题名称
            connection_id: 连接ID
        """
        if topic in self.topic_subscriptions and connection_id in self.topic_subscriptions[topic]:
            self.topic_subscriptions[topic].discard(connection_id)

            # 如果主题没有订阅者了，删除主题
            if not self.topic_subscriptions[topic]:
                del self.topic_subscriptions[topic]

        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].discard(topic)

        logger.debug(
            f"websocket_unsubscribed connection_id={connection_id} topic={topic}"
        )

    async def send_personal_message(self, message: dict, connection_id: str) -> bool:
        """
        发送消息到指定连接

        Args:
            message: 消息内容（字典）
            connection_id: 目标连接ID

        Returns:
            是否发送成功
        """
        if connection_id not in self.active_connections:
            logger.warning(
                f"websocket_send_failed_connection_not_found connection_id={connection_id}"
            )
            return False

        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(
                f"websocket_send_error connection_id={connection_id} error={str(e)}"
            )
            # 连接可能已断开，移除连接
            await self.disconnect(connection_id)
            return False

    async def broadcast(self, message: dict, topic: Optional[str] = None) -> int:
        """
        广播消息

        Args:
            message: 消息内容（字典）
            topic: 可选的主题名称，如果指定则只发送给订阅该主题的连接

        Returns:
            成功发送的连接数
        """
        # 确定目标连接
        if topic:
            # 发送给订阅该主题的连接
            target_connection_ids = self.topic_subscriptions.get(topic, set())
        else:
            # 发送给所有连接
            target_connection_ids = set(self.active_connections.keys())

        # 并发发送消息
        tasks = [
            self.send_personal_message(message, conn_id)
            for conn_id in target_connection_ids
        ]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
        else:
            success_count = 0

        logger.debug(
            f"websocket_broadcast topic={topic or 'all'} target_count={len(target_connection_ids)} success_count={success_count}"
        )

        return success_count

    async def send_log(self, topic: str, level: str, message: str, **extra_data) -> int:
        """
        发送日志消息

        Args:
            topic: 主题名称
            level: 日志级别（info, warning, error, debug）
            message: 日志消息
            **extra_data: 额外的数据

        Returns:
            成功发送的连接数
        """
        log_message = {
            "type": "log",
            "topic": topic,
            "level": level,
            "message": message,
            "timestamp": asyncio.get_event_loop().time(),
            **extra_data,
        }

        return await self.broadcast(log_message, topic=topic)

    async def send_status_update(self, topic: str, status: str, **extra_data) -> int:
        """
        发送状态更新消息

        Args:
            topic: 主题名称
            status: 状态（pending, running, success, failed, cancelled）
            **extra_data: 额外的数据

        Returns:
            成功发送的连接数
        """
        status_message = {
            "type": "status_update",
            "topic": topic,
            "status": status,
            "timestamp": asyncio.get_event_loop().time(),
            **extra_data,
        }

        return await self.broadcast(status_message, topic=topic)

    async def send_progress(self, topic: str, progress: float, total: int, current: int, **extra_data) -> int:
        """
        发送进度更新消息

        Args:
            topic: 主题名称
            progress: 进度百分比（0-100）
            total: 总数
            current: 当前进度
            **extra_data: 额外的数据

        Returns:
            成功发送的连接数
        """
        progress_message = {
            "type": "progress",
            "topic": topic,
            "progress": progress,
            "total": total,
            "current": current,
            "timestamp": asyncio.get_event_loop().time(),
            **extra_data,
        }

        return await self.broadcast(progress_message, topic=topic)

    def get_connection_count(self) -> int:
        """获取当前活动连接数"""
        return len(self.active_connections)

    def get_subscriber_count(self, topic: str) -> int:
        """获取指定主题的订阅者数量"""
        return len(self.topic_subscriptions.get(topic, set()))

    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        return self.connection_metadata.get(connection_id)


# 全局连接管理器实例
manager = ConnectionManager()
