"""
GitLab集成端到端测试

测试完整的GitLab集成流程
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from src.integrations.gitlab.client import GitLabClient
from src.services.gitlab_service import GitLabService


class TestGitLabIntegration:
    """GitLab集成测试"""

    @pytest.mark.asyncio
    async def test_full_sync_workflow(self):
        """测试完整的同步工作流"""
        # 模拟GitLab项目数据
        project_data = {
            "id": 123,
            "name": "test-project",
            "description": "Test project for CI/CD",
            "web_url": "https://gitlab.example.com/test/project",
            "default_branch": "main",
            "ci_config_path": ".gitlab-ci.yml",
            "created_at": "2024-01-01T00:00:00.000Z",
            "last_activity_at": "2024-03-08T00:00:00.000Z",
        }

        # 模拟GitLab流水线数据
        pipelines_data = [
            {
                "id": 456,
                "project_id": 123,
                "status": "success",
                "ref": "main",
                "sha": "abc123def456",
                "source": "push",
                "duration": 300,
                "created_at": "2024-03-08T00:00:00.000Z",
                "updated_at": "2024-03-08T00:05:00.000Z",
                "started_at": "2024-03-08T00:00:05.000Z",
                "finished_at": "2024-03-08T00:05:00.000Z",
            }
        ]

        # 模拟流水线作业数据
        jobs_data = [
            {
                "id": 789,
                "name": "build",
                "stage": "build",
                "status": "success",
                "duration": 120,
                "retry_count": 0,
                "created_at": "2024-03-08T00:00:00.000Z",
                "started_at": "2024-03-08T00:00:10.000Z",
                "finished_at": "2024-03-08T00:02:10.000Z",
                "updated_at": "2024-03-08T00:02:10.000Z",
            }
        ]

        client = GitLabClient()
        service = GitLabService()

        # Mock数据库会话
        mock_db = AsyncMock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        # 创建模拟对象
        mock_project = Mock()
        mock_project.id = 1
        mock_project.gitlab_project_id = 123
        
        mock_pipeline = Mock()
        mock_pipeline.id = 1
        mock_pipeline.gitlab_pipeline_id = 456
        
        mock_job = Mock()
        mock_job.id = 1
        mock_job.gitlab_job_id = 789

        # Mock HTTP client
        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_get_client.return_value = mock_http

            # 测试1: 同步项目
            print("\n=== 测试项目同步 ===")
            mock_http.get.return_value = Mock(
                json=Mock(return_value=project_data),
                raise_for_status=Mock(),
            )

            project = await service.sync_project(mock_db, 123)
            assert project is not None
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
            print("✓ 项目同步成功")

            # 测试2: 同步流水线
            print("\n=== 测试流水线同步 ===")
            mock_query.filter.return_value.first.return_value = None
            mock_http.get.return_value = Mock(
                json=Mock(return_value=[pipelines_data[0]]),
                raise_for_status=Mock(),
            )

            pipelines = await service.sync_pipelines(mock_db, 123)
            assert len(pipelines) == 1
            assert pipelines[0].gitlab_pipeline_id == 456
            print("✓ 流水线同步成功")

            # 测试3: 同步流水线作业
            print("\n=== 测试作业同步 ===")
            mock_http.get.return_value = Mock(
                json=Mock(return_value=[jobs_data[0]]),
                raise_for_status=Mock(),
            )

            jobs = await service.sync_pipeline_jobs(mock_db, pipelines[0])
            assert len(jobs) == 1
            assert jobs[0].gitlab_job_id == 789
            print("✓ 作业同步成功")

            print("\n=== 端到端测试通过 ===")

    @pytest.mark.asyncio
    async def test_trigger_pipeline(self):
        """测试触发流水线"""
        client = GitLabClient()

        # 模拟触发流水线响应
        trigger_response = {
            "id": 999,
            "ref": "feature-branch",
            "sha": "xyz789",
            "status": "pending",
            "created_at": "2024-03-08T12:00:00.000Z",
            "updated_at": "2024-03-08T12:00:00.000Z",
        }

        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_get_client.return_value = mock_http
            mock_http.post.return_value = Mock(
                json=Mock(return_value=trigger_response),
                raise_for_status=Mock(),
            )

            result = await client.trigger_pipeline(123, "feature-branch")
            assert result["id"] == 999
            assert result["ref"] == "feature-branch"
            assert result["status"] == "pending"

            # 验证POST请求
            assert mock_http.post.called
            call_args = mock_http.post.call_args
            assert call_args[0][0] == "/projects/123/pipeline"

            print("✓ 流水线触发测试通过")

    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self):
        """测试Webhook签名验证"""
        from src.integrations.gitlab.webhook import WebhookProcessor
        import hmac
        import hashlib

        processor = WebhookProcessor()

        # 测试1: 无secret配置
        with patch('src.integrations.gitlab.webhook.settings') as mock_settings:
            mock_settings.gitlab_webhook_secret = None
            result = await processor.verify_signature(b"test payload", "any")
            assert result is True
            print("✓ 无secret配置验证通过")

        # 测试2: 正确签名
        with patch('src.integrations.gitlab.webhook.settings') as mock_settings:
            secret = b"test-secret"
            payload = b"test payload"
            expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
            
            mock_settings.gitlab_webhook_secret = secret.decode()
            result = await processor.verify_signature(
                payload, 
                f"sha256={expected_signature}"
            )
            assert result is True
            print("✓ 正确签名验证通过")

        # 测试3: 错误签名
        with patch('src.integrations.gitlab.webhook.settings') as mock_settings:
            secret = b"test-secret"
            payload = b"test payload"
            
            mock_settings.gitlab_webhook_secret = secret.decode()
            result = await processor.verify_signature(
                payload, 
                "sha256=wrong_signature"
            )
            assert result is False
            print("✓ 错误签名被拒绝")

        print("✓ Webhook签名验证测试通过")

    @pytest.mark.asyncio
    async def test_webhook_event_processing(self):
        """测试Webhook事件处理"""
        from src.integrations.gitlab.webhook import WebhookProcessor

        processor = WebhookProcessor()

        # 模拟Push事件
        push_event = {
            "object_kind": "push",
            "project": {"id": 123},
            "ref": "refs/heads/main",
            "commits": [
                {"id": "abc123", "message": "Test commit"}
            ],
        }

        # 模拟数据库和GitLab服务
        mock_db = AsyncMock()
        with patch('src.integrations.gitlab.webhook.gitlab_service') as mock_service:
            mock_service.sync_project = AsyncMock()

            await processor.handle_push_event(push_event, mock_db)
            assert mock_service.sync_project.called
            assert mock_service.sync_project.call_args[0][1] == 123

        print("✓ Push事件处理测试通过")

        # 模拟Pipeline事件
        pipeline_event = {
            "object_kind": "pipeline",
            "object_attributes": {
                "id": 456,
                "status": "success",
            },
            "project": {"id": 123},
        }

        mock_db = AsyncMock()
        await processor.handle_pipeline_event(pipeline_event, mock_db)

        print("✓ Pipeline事件处理测试通过")
        print("✓ Webhook事件处理测试通过")


@pytest.mark.asyncio
async def test_concurrent_sync_performance():
    """测试并发同步性能"""
    service = GitLabService()

    # 模拟多个项目
    projects = [
        {"id": i, "name": f"project-{i}", "web_url": f"https://gitlab.example.com/p{i}"}
        for i in range(1, 11)
    ]

    with patch.object(service.client, 'get_projects') as mock_get_projects:
        mock_get_projects.return_value = projects

        # 创建模拟数据库
        mock_db = AsyncMock()
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 测试并发同步
        import time
        start = time.time()
        
        synced = await service.sync_projects(mock_db)
        
        duration = time.time() - start

        assert len(synced) == 10
        print(f"✓ 并发同步10个项目耗时: {duration:.2f}秒")
        print(f"✓ 平均每个项目: {duration/10:.2f}秒")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
