"""
WebSocket实时通信集成测试

验证WebSocket连接管理、日志流、实时更新等功能
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock
import json
import asyncio

from src.services.websocket.manager import ConnectionManager, manager


@pytest.mark.asyncio
class WebSocketIntegrationTest:
    """WebSocket集成测试套件"""

    async def test_websocket_connection_lifecycle(
        self,
        mock_websocket,
    ):
        """测试WebSocket连接生命周期"""
        # 1. 连接
        conn_id = await manager.connect(mock_websocket)
        assert conn_id is not None
        assert conn_id in manager.active_connections
        assert conn_id in manager.connection_metadata

        # 2. 验证连接信息
        conn_info = manager.get_connection_info(conn_id)
        assert conn_info is not None
        assert "connected_at" in conn_info
        assert "subscriptions" in conn_info

        # 3. 断开连接
        await manager.disconnect(conn_id)
        assert conn_id not in manager.active_connections
        assert conn_id not in manager.connection_metadata

    async def test_websocket_topic_subscription(
        self,
        mock_websocket,
    ):
        """测试主题订阅功能"""
        # 连接
        conn_id = await manager.connect(mock_websocket)

        # 订阅主题
        topic1 = "build:123"
        topic2 = "test:456"

        manager.subscribe(conn_id, topic1)
        manager.subscribe(conn_id, topic2)

        # 验证订阅
        assert manager.get_subscriber_count(topic1) == 1
        assert manager.get_subscriber_count(topic2) == 1

        conn_info = manager.get_connection_info(conn_id)
        assert topic1 in conn_info["subscriptions"]
        assert topic2 in conn_info["subscriptions"]

        # 取消订阅
        manager.unsubscribe(topic1, conn_id)
        assert manager.get_subscriber_count(topic1) == 0
        assert topic1 not in conn_info["subscriptions"]

        # 清理
        await manager.disconnect(conn_id)

    async def test_websocket_personal_message(
        self,
        mock_websocket,
    ):
        """测试个人消息发送"""
        conn_id = await manager.connect(mock_websocket)

        message = {
            "type": "test",
            "data": "Hello",
        }

        success = await manager.send_personal_message(message, conn_id)
        assert success is True

        # 验证send_json被调用
        mock_websocket.send_json.assert_called_once_with(message)

        # 清理
        await manager.disconnect(conn_id)

    async def test_websocket_broadcast_to_all(
        self,
        mock_websocket,
    ):
        """测试广播到所有连接"""
        # 创建多个连接
        connections = []
        for i in range(3):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            conn_id = await manager.connect(ws)
            connections.append((conn_id, ws))

        # 广播消息
        message = {"type": "broadcast", "data": "test"}
        success_count = await manager.broadcast(message)

        # 应该发送到所有3个连接
        assert success_count == 3

        # 验证每个连接都收到消息
        for conn_id, ws in connections:
            ws.send_json.assert_called_once_with(message)

        # 清理
        for conn_id, _ in connections:
            await manager.disconnect(conn_id)

    async def test_websocket_broadcast_to_topic(
        self,
        mock_websocket,
    ):
        """测试广播到特定主题"""
        # 创建连接并订阅不同主题
        conn1 = await manager.connect(mock_websocket)
        manager.subscribe(conn1, "build:123")

        # 创建第二个连接
        ws2 = Mock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        conn2 = await manager.connect(ws2)
        manager.subscribe(conn2, "build:123")  # 订阅相同主题

        # 创建第三个连接（订阅不同主题）
        ws3 = Mock()
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()
        conn3 = await manager.connect(ws3)
        manager.subscribe(conn3, "test:456")  # 不同主题

        # 广播到build:123主题
        message = {"type": "log", "data": "build log"}
        success_count = await manager.broadcast(message, topic="build:123")

        # 应该只发送到conn1和conn2
        assert success_count == 2
        mock_websocket.send_json.assert_called()
        ws2.send_json.assert_called()
        ws3.send_json.assert_not_called()  # conn3没有订阅这个主题

        # 清理
        await manager.disconnect(conn1)
        await manager.disconnect(conn2)
        await manager.disconnect(conn3)

    async def test_websocket_send_log(
        self,
        mock_websocket,
    ):
        """测试发送日志消息"""
        conn_id = await manager.connect(mock_websocket)
        manager.subscribe(conn_id, "build:123")

        # 发送日志
        success_count = await manager.send_log(
            topic="build:123",
            level="info",
            message="Building...",
            job_id="123",
        )

        assert success_count == 1

        # 验证消息格式
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "log"
        assert sent_message["topic"] == "build:123"
        assert sent_message["level"] == "info"
        assert sent_message["message"] == "Building..."
        assert sent_message["job_id"] == "123"

        # 清理
        await manager.disconnect(conn_id)

    async def test_websocket_send_status_update(
        self,
        mock_websocket,
    ):
        """测试发送状态更新"""
        conn_id = await manager.connect(mock_websocket)
        manager.subscribe(conn_id, "pipeline:789")

        # 发送状态更新
        success_count = await manager.send_status_update(
            topic="pipeline:789",
            status="running",
            pipeline_id="789",
        )

        assert success_count == 1

        # 验证消息格式
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "status_update"
        assert sent_message["status"] == "running"
        assert sent_message["pipeline_id"] == "789"

        # 清理
        await manager.disconnect(conn_id)

    async def test_websocket_send_progress(
        self,
        mock_websocket,
    ):
        """测试发送进度更新"""
        conn_id = await manager.connect(mock_websocket)
        manager.subscribe(conn_id, "build:123")

        # 发送进度
        success_count = await manager.send_progress(
            topic="build:123",
            progress=50.0,
            total=100,
            current=50,
            job_id="123",
        )

        assert success_count == 1

        # 验证消息格式
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "progress"
        assert sent_message["progress"] == 50.0
        assert sent_message["total"] == 100
        assert sent_message["current"] == 50

        # 清理
        await manager.disconnect(conn_id)

    async def test_websocket_multiple_subscriptions(
        self,
        mock_websocket,
    ):
        """测试一个连接订阅多个主题"""
        conn_id = await manager.connect(mock_websocket)

        # 订阅多个主题
        topics = ["build:123", "test:456", "pipeline:789"]
        for topic in topics:
            manager.subscribe(conn_id, topic)

        # 验证订阅
        for topic in topics:
            assert manager.get_subscriber_count(topic) == 1

        # 取消所有订阅（通过disconnect）
        await manager.disconnect(conn_id)

        # 验证所有订阅都已清除
        for topic in topics:
            assert manager.get_subscriber_count(topic) == 0

    async def test_websocket_concurrent_broadcasts(
        self,
    ):
        """测试并发广播"""
        # 创建多个连接
        connections = []
        for i in range(5):
            ws = Mock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            conn_id = await manager.connect(ws)
            manager.subscribe(conn_id, "broadcast_test")
            connections.append(conn_id)

        # 并发发送多条广播
        tasks = []
        for i in range(10):
            message = {"type": "test", "index": i}
            task = manager.broadcast(message, topic="broadcast_test")
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # 验证所有广播都成功
        assert all(r == 5 for r in results)  # 每条广播都发送到5个连接

        # 验证每个连接收到10条消息
        for conn_id, ws in zip(connections, [manager.active_connections[c] for c in connections]):
            assert ws.send_json.call_count == 10

        # 清理
        for conn_id in connections:
            await manager.disconnect(conn_id)

    async def test_websocket_get_statistics(
        self,
        mock_websocket,
    ):
        """测试获取统计信息"""
        # 创建几个连接
        for i in range(3):
            conn_id = await manager.connect(mock_websocket)
            manager.subscribe(conn_id, f"topic:{i}")

        # 获取连接数
        conn_count = manager.get_connection_count()
        assert conn_count >= 3

        # 获取主题订阅数
        for i in range(3):
            count = manager.get_subscriber_count(f"topic:{i}")
            assert count == 1

        # 清理
        for i in range(3):
            await manager.disconnect(f"conn_{i+1}")  # conn_id从1开始

    async def test_websocket_log_stream_simulation(
        self,
        mock_websocket,
    ):
        """测试模拟日志流"""
        job_id = "test-build-001"
        topic = f"build:{job_id}"

        conn_id = await manager.connect(mock_websocket)
        manager.subscribe(conn_id, topic)

        # 模拟构建日志流
        logs = [
            ("info", "Starting build configuration..."),
            ("info", "CMake configuration complete"),
            ("warning", "Unused variable 'x'"),
            ("info", "Compiling..."),
            ("info", "Linking..."),
            ("info", "Build complete"),
        ]

        for level, message in logs:
            await manager.send_log(topic, level, message, job_id=job_id)

        # 验证收到所有日志
        assert mock_websocket.send_json.call_count == len(logs)

        # 验证最后一条是成功消息
        last_call = mock_websocket.send_json.call_args_list[-1]
        last_message = last_call[0][0]
        assert "Build complete" in last_message["message"]

        # 清理
        await manager.disconnect(conn_id)


@pytest.mark.asyncio
async def test_websocket_manager_isolation():
    """测试多个WebSocket管理器实例隔离"""
    # 创建第二个管理器
    manager2 = ConnectionManager()

    # 在两个管理器中创建连接
    ws1 = Mock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()

    ws2 = Mock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()

    conn1 = await manager.connect(ws1)
    conn2 = await manager2.connect(ws2)

    # 验证隔离 - 每个管理器有自己的连接集合
    assert conn1 in manager.active_connections
    assert len(manager.active_connections) == 1
    assert conn1 in manager.connection_metadata

    assert conn2 in manager2.active_connections
    assert len(manager2.active_connections) == 1
    assert conn2 in manager2.connection_metadata

    # 验证跨管理器状态隔离
    assert manager.get_connection_count() == 1
    assert manager2.get_connection_count() == 1
    assert manager.get_connection_count() == manager2.get_connection_count()

    # 清理
    await manager.disconnect(conn1)
    await manager2.disconnect(conn2)

    # 验证清理后状态
    assert len(manager.active_connections) == 0
    assert len(manager2.active_connections) == 0


@pytest.mark.asyncio
async def test_websocket_error_handling(
    mock_websocket,
):
    """测试WebSocket错误处理"""
    conn_id = await manager.connect(mock_websocket)

    # 测试发送到不存在的连接
    success = await manager.send_personal_message(
        {"type": "test"},
        "non-existent-conn-id"
    )
    assert success is False

    # 测试取消不存在的订阅
    manager.unsubscribe("random:topic", "non-existent-conn-id")
    # 应该不抛出错误

    # 清理
    await manager.disconnect(conn_id)


@pytest.mark.asyncio
async def test_websocket_disconnect_with_subscriptions(
    mock_websocket,
):
    """测试断开连接时自动清理订阅"""
    conn_id = await manager.connect(mock_websocket)

    # 订阅多个主题
    manager.subscribe(conn_id, "build:123")
    manager.subscribe(conn_id, "test:456")
    manager.subscribe(conn_id, "pipeline:789")

    # 验证订阅
    assert manager.get_subscriber_count("build:123") == 1
    assert manager.get_subscriber_count("test:456") == 1
    assert manager.get_subscriber_count("pipeline:789") == 1

    # 断开连接
    await manager.disconnect(conn_id)

    # 验证所有订阅都已清理
    assert manager.get_subscriber_count("build:123") == 0
    assert manager.get_subscriber_count("test:456") == 0
    assert manager.get_subscriber_count("pipeline:789") == 0
    assert conn_id not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_connection_id_generation(
    mock_websocket,
):
    """测试连接ID生成唯一性"""
    conn_ids = set()

    # 创建多个连接
    for _ in range(10):
        conn_id = await manager.connect(mock_websocket)
        conn_ids.add(conn_id)
        # 重置mock以便下次调用
        mock_websocket.accept.reset()

    # 验证所有ID唯一
    assert len(conn_ids) == 10

    # 清理
    for conn_id in conn_ids:
        await manager.disconnect(conn_id)
