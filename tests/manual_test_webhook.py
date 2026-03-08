#!/usr/bin/env python3
"""
手动测试脚本 - 测试 Webhook 端点

这个脚本启动一个临时服务器并测试 Webhook 端点
"""

import asyncio
import json
import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from src.main import app
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def start_server():
    """启动测试服务器"""
    import uvicorn

    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=8765,
        log_level="info",
    )
    server = uvicorn.Server(config)

    # 启动服务器
    task = asyncio.create_task(server.serve())

    # 等待服务器启动
    await asyncio.sleep(2)

    yield server

    # 关闭服务器
    server.should_exit = True
    await task


async def test_webhook_endpoint():
    """测试 Webhook 端点"""

    # 准备测试数据
    webhook_payload = {
        "object_kind": "merge_request",
        "event_type": "merge_request",
        "user": {
            "id": 1,
            "name": "Test User",
            "username": "testuser",
            "email": "test@example.com",
        },
        "project": {
            "id": 456,
            "name": "test-project",
            "path_with_namespace": "group/test-project",
            "default_branch": "main",
            "url": "https://gitlab.example.com/group/test-project.git",
            "web_url": "https://gitlab.example.com/group/test-project",
        },
        "object_attributes": {
            "id": 123,
            "iid": 1,
            "title": "Feature: Add user authentication",
            "description": "This MR adds OAuth2 authentication support",
            "state": "opened",
            "created_at": "2026-03-08T10:00:00.000Z",
            "updated_at": "2026-03-08T11:00:00.000Z",
            "action": "open",
            "source_branch": "feature/auth",
            "target_branch": "main",
            "draft": False,
            "work_in_progress": False,
        },
        "changes": {},
        "labels": [],
        "assignees": [],
        "reviewers": [],
    }

    print("\n" + "=" * 70)
    print("🧪 测试 Webhook 端点")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 测试健康检查
        print("\n📍 测试 1: 健康检查")
        try:
            response = await client.get("http://127.0.0.1:8765/health")
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

        # 2. 测试 Webhook 端点（无签名）
        print("\n📍 测试 2: Webhook 端点（无签名 - 应失败）")
        try:
            response = await client.post(
                "http://127.0.0.1:8765/webhook/gitlab",
                json=webhook_payload,
            )
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.json()}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

        # 3. 测试 Webhook 端点（错误签名 - 应失败）
        print("\n📍 测试 3: Webhook 端点（错误签名 - 应失败）")
        try:
            response = await client.post(
                "http://127.0.0.1:8765/webhook/gitlab",
                json=webhook_payload,
                headers={"X-Gitlab-Token": "wrong_token"},
            )
            print(f"   状态码: {response.status_code}")
            print(f"   响应: {response.json()}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

        # 4. 测试 Webhook 端点（正确签名 - 应成功）
        print("\n📍 测试 4: Webhook 端点（正确签名 - 应成功）")
        try:
            response = await client.post(
                "http://127.0.0.1:8765/webhook/gitlab",
                json=webhook_payload,
                headers={"X-Gitlab-Token": "test_webhook_secret_12345"},
            )
            print(f"   状态码: {response.status_code}")
            result = response.json()
            print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result.get("status") == "queued":
                print("   ✅ Webhook 已成功处理并加入队列")
            elif result.get("status") == "error":
                print("   ⚠️  Webhook 处理遇到错误（可能是 Mock 限制）")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

        # 5. 测试 Dashboard API
        print("\n📍 测试 5: Dashboard 统计 API")
        try:
            response = await client.get("http://127.0.0.1:8765/api/dashboard/stats")
            print(f"   状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Dashboard API 正常工作")
                if result.get("success"):
                    data = result.get("data", {})
                    print(f"   测试生成: {data.get('tests', {})}")
                    print(f"   代码审查: {data.get('reviews', {})}")
            else:
                print(f"   响应: {response.json()}")
        except Exception as e:
            print(f"   ❌ 失败: {e}")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70 + "\n")


async def main():
    """主函数"""
    print("\n🚀 启动测试服务器...")

    async with start_server():
        print("✅ 服务器已启动在 http://127.0.0.1:8765")

        # 运行测试
        await test_webhook_endpoint()

        # 保持服务器运行以便手动测试
        print("\n💡 服务器仍在运行，您可以进行额外的手动测试：")
        print("   健康检查: curl http://127.0.0.1:8765/health")
        print("   Dashboard: http://127.0.0.1:8765/static/index.html")
        print("\n按 Ctrl+C 停止服务器...")

        # 等待用户中断
        try:
            await asyncio.sleep(float("inf"))
        except KeyboardInterrupt:
            print("\n\n👋 服务器已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✨ 测试结束")
