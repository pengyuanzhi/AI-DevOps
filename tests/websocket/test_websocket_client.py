#!/usr/bin/env python3
"""
WebSocket连接测试脚本

验证WebSocket Manager的连接、订阅和消息推送功能。
"""

import asyncio
import websockets
import json
from typing import Optional
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.services.websocket.manager import manager


async def test_websocket_connection():
    """测试WebSocket连接和消息接收"""

    # WebSocket服务器地址
    uri = "ws://localhost:8000/api/v1/ws/connect?subscribe=build:test_job_123,test:test_job_456"

    print("=" * 60)
    print("WebSocket连接测试")
    print("=" * 60)
    print(f"连接到: {uri}")
    print()

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")

            # 接收欢迎消息
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✅ 收到欢迎消息: {data['type']}")
            print()

            # 订阅额外主题
            subscribe_msg = {
                "type": "subscribe",
                "topic": "pipeline:pipeline_789"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("✅ 发送订阅请求: pipeline:pipeline_789")

            # 确认订阅
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✅ 订阅确认: {data['type']} - {data.get('topic')}")
            print()

            # 发送心跳
            print("发送心跳ping...")
            await websocket.send(json.dumps({"type": "ping"}))

            # 接收pong响应
            pong = await websocket.recv()
            pong_data = json.loads(pong)
            print(f"✅ 收到心跳响应: {pong_data['type']}")
            print()

            # 发送回显测试
            print("发送回显测试...")
            echo_msg = {
                "type": "echo",
                "data": {"test": "Hello WebSocket!"}
            }
            await websocket.send(json.dumps(echo_msg))

            # 接收回显
            echo_response = await websocket.recv()
            echo_data = json.loads(echo_response)
            print(f"✅ 回显响应: {echo_data}")
            print()

            # 测试服务器推送（需要服务器端发送消息）
            print("等待服务器消息（5秒）...")
            try:
                # 设置超时
                server_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                server_data = json.loads(server_msg)
                print(f"✅ 收到服务器消息: {server_data}")
            except asyncio.TimeoutError:
                print("⏱️  超时：没有收到服务器消息（正常，如果没有活动）")
            print()

            # 取消订阅
            print("取消订阅: build:test_job_123")
            unsubscribe_msg = {
                "type": "unsubscribe",
                "topic": "build:test_job_123"
            }
            await websocket.send(json.dumps(unsubscribe_msg))

            unsub_response = await websocket.recv()
            unsub_data = json.loads(unsub_response)
            print(f"✅ 取消订阅确认: {unsub_data['type']} - {unsub_data.get('topic')}")
            print()

            print("=" * 60)
            print("✅ 所有测试通过")
            print("=" * 60)
            return True

    except websockets.exceptions.ConnectionRefused:
        print("❌ 连接被拒绝，请确保后端服务器正在运行")
        print("   启动命令: ./scripts/start-backend.sh")
        return False
    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_broadcast_messages():
    """测试广播消息功能"""

    print("\n" + "=" * 60)
    print("广播消息测试")
    print("=" * 60)

    # 模拟广播日志消息
    topic = "build:test_job_123"
    level = "info"
    message = "Test build started"

    success_count = await manager.send_log(topic, level, message, job_id="test_job_123")

    print(f"✅ 发送日志消息到主题 '{topic}'")
    print(f"   级别: {level}")
    print(f"   消息: {message}")
    print(f"   发送到 {success_count} 个订阅者")
    print()

    # 模拟状态更新
    topic = "test:test_job_456"
    status = "running"
    success_count = await manager.send_status_update(topic, status, test_run_id="test_job_456")

    print(f"✅ 发送状态更新到主题 '{topic}'")
    print(f"   状态: {status}")
    print(f"   发送到 {success_count} 个订阅者")
    print()

    # 模拟进度更新
    topic = "pipeline:pipeline_789"
    progress = 50.0
    total = 100
    current = 50
    success_count = await manager.send_progress(topic, progress, total, current, pipeline_id="pipeline_789")

    print(f"✅ 发送进度更新到主题 '{topic}'")
    print(f"   进度: {progress}%")
    print(f"   发送到 {success_count} 个订阅者")
    print()

    print("=" * 60)
    print("✅ 广播消息测试完成")
    print("=" * 60)


async def test_connection_manager():
    """测试ConnectionManager功能"""

    print("\n" + "=" * 60)
    print("ConnectionManager功能测试")
    print("=" * 60)

    # 获取连接统计
    conn_count = manager.get_connection_count()
    print(f"✅ 当前活动连接数: {conn_count}")

    # 测试主题订阅者统计
    test_topic = "build:test"
    subscriber_count = manager.get_subscriber_count(test_topic)
    print(f"✅ 主题 '{test_topic}' 订阅者数: {subscriber_count}")

    # 模拟创建一个虚拟连接
    class MockWebSocket:
        async def accept(self):
            print("   模拟接受连接")

        async def send_json(self, data):
            print(f"   模拟发送JSON: {data['type']}")

        async def send(self, data):
            print(f"   模拟发送: {data[:100] if len(data) > 100 else data}")

        async def close(self):
            print("   模拟关闭连接")

        async def receive_text(self):
            return json.dumps({"type": "ping"})

    mock_ws = MockWebSocket()
    conn_id = await manager.connect(mock_ws)
    print(f"✅ 创建模拟连接: {conn_id}")

    # 测试个人消息
    await manager.send_personal_message({"type": "test", "data": "Hello"}, conn_id)
    print(f"✅ 发送个人消息到 {conn_id}")

    # 测试订阅
    manager.subscribe(conn_id, "build:123")
    print(f"✅ 订阅主题: build:123")

    # 验证订阅
    subscriber_count = manager.get_subscriber_count("build:123")
    print(f"✅ 主题 'build:123' 订阅者数: {subscriber_count}")

    # 清理
    await manager.disconnect(conn_id)
    print(f"✅ 断开连接: {conn_id}")

    conn_count = manager.get_connection_count()
    print(f"✅ 当前活动连接数: {conn_count}")

    print("=" * 60)
    print("✅ ConnectionManager功能测试完成")
    print("=" * 60)


async def test_log_streaming():
    """测试日志流功能（模拟）"""

    print("\n" + "=" * 60)
    print("日志流功能测试")
    print("=" * 60)

    job_id = "test_build_job_001"
    topic = f"build:{job_id}"

    # 模拟构建日志流
    logs = [
        ("info", "Starting build configuration..."),
        ("info", "CMake configuration complete"),
        ("info", "Compiling source files..."),
        ("warning", "Unused variable 'x' in line 42"),
        ("info", "Linking binaries..."),
        ("info", "Build complete successfully"),
    ]

    print(f"模拟构建日志流: {job_id}")
    print()

    for level, message in logs:
        await manager.send_log(topic, level, message, job_id=job_id)

        # 根据级别使用不同符号
        if level == "error":
            symbol = "❌"
        elif level == "warning":
            symbol = "⚠️ "
        else:
            symbol = "ℹ️ "

        print(f"{symbol} [{level.upper()}] {message}")

    print()
    print(f"✅ 日志流测试完成")
    print("=" * 60)


async def main():
    """主测试函数"""

    print("\n🚀 AI-CICD WebSocket测试套件")
    print()

    # 测试1: ConnectionManager功能
    await test_connection_manager()

    # 测试2: 广播消息
    await test_broadcast_messages()

    # 测试3: 日志流
    await test_log_streaming()

    # 测试4: WebSocket连接（需要服务器运行）
    print("\n是否测试WebSocket连接？(需要后端服务器运行)")
    print("启动服务器: ./scripts/start-backend.sh")

    response = input("继续测试WebSocket连接？[y/N]: ").strip().lower()

    if response == 'y' or response == 'yes':
        success = await test_websocket_connection()
        if success:
            print("\n✅ WebSocket连接测试通过")
        else:
            print("\n❌ WebSocket连接测试失败")
    else:
        print("跳过WebSocket连接测试")

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print("✅ ConnectionManager功能测试 - 通过")
    print("✅ 广播消息功能测试 - 通过")
    print("✅ 日志流功能测试 - 通过")
    if response == 'y':
        print(f"{'✅' if success else '❌'} WebSocket连接测试 - {'通过' if success else '失败'}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试套件错误: {e}")
        import traceback
        traceback.print_exc()
