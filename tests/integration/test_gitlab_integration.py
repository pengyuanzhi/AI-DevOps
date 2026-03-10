"""
GitLab集成测试

测试GitLab客户端和服务的基本功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.integrations.gitlab.client import GitLabClient
from src.services.gitlab_service import GitLabService


@pytest.fixture
def mock_settings():
    """模拟设置"""
    mock = Mock()
    mock.gitlab_url = "https://gitlab.example.com"
    mock.gitlab_token = "test-token"
    mock.gitlab_webhook_secret = None
    return mock


@pytest.fixture
def mock_gitlab_response():
    """模拟GitLab API响应"""
    return {
        "id": 123,
        "name": "test-project",
        "description": "Test project description",
        "web_url": "https://gitlab.example.com/test/project",
        "default_branch": "main",
        "ci_config_path": ".gitlab-ci.yml",
        "created_at": "2024-01-01T00:00:00.000Z",
        "last_activity_at": "2024-03-08T00:00:00.000Z",
    }


@pytest.fixture
def mock_pipeline_response():
    """模拟GitLab流水线API响应"""
    return {
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


@pytest.fixture
def mock_job_response():
    """模拟GitLab作业API响应"""
    return {
        "id": 789,
        "name": "test-job",
        "stage": "test",
        "status": "success",
        "duration": 60,
        "retry_count": 0,
        "created_at": "2024-03-08T00:00:00.000Z",
        "started_at": "2024-03-08T00:00:10.000Z",
        "finished_at": "2024-03-08T00:01:10.000Z",
        "updated_at": "2024-03-08T00:01:10.000Z",
    }


class TestGitLabClient:
    """测试GitLab客户端"""

    @pytest.mark.asyncio
    async def test_get_http_client(self, mock_settings):
        """测试获取HTTP客户端"""
        with patch('src.integrations.gitlab.client.settings', mock_settings):
            client = GitLabClient()
            http_client = await client.get_http_client()

            assert http_client is not None
            assert "gitlab.example.com" in str(http_client.base_url)
            assert http_client.headers["PRIVATE-TOKEN"] == "test-token"

    @pytest.mark.asyncio
    async def test_get_project(self, mock_gitlab_response):
        """测试获取项目"""
        client = GitLabClient()

        # Mock HTTP响应
        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_gitlab_response
            mock_response.raise_for_status = Mock()
            mock_http.get.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.get_project(123)

            assert result["id"] == 123
            assert result["name"] == "test-project"
            mock_http.get.assert_called_once_with("/projects/123")

    @pytest.mark.asyncio
    async def test_get_pipelines(self, mock_pipeline_response):
        """测试获取流水线列表"""
        client = GitLabClient()

        # Mock HTTP响应
        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = [mock_pipeline_response]
            mock_response.raise_for_status = Mock()
            mock_http.get.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.get_pipelines(123)

            assert len(result) == 1
            assert result[0]["id"] == 456
            mock_http.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_pipeline(self):
        """测试触发流水线"""
        client = GitLabClient()

        # Mock HTTP响应
        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {
                "id": 789,
                "ref": "main",
                "sha": "xyz789",
                "status": "pending",
                "created_at": "2024-03-08T00:00:00.000Z",
                "updated_at": "2024-03-08T00:00:00.000Z",
            }
            mock_response.raise_for_status = Mock()
            mock_http.post.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.trigger_pipeline(123, "main")

            assert result["id"] == 789
            assert result["ref"] == "main"
            mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs(self, mock_job_response):
        """测试获取流水线作业列表"""
        client = GitLabClient()

        # Mock HTTP响应
        with patch.object(client, 'get_http_client') as mock_get_client:
            mock_http = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = [mock_job_response]
            mock_response.raise_for_status = Mock()
            mock_http.get.return_value = mock_response
            mock_get_client.return_value = mock_http

            result = await client.get_pipeline_jobs(123, 456)

            assert len(result) == 1
            assert result[0]["id"] == 789
            mock_http.get.assert_called_once_with("/projects/123/pipelines/456/jobs")


class TestGitLabService:
    """测试GitLab服务"""

    @pytest.mark.asyncio
    async def test_sync_project_new(self, mock_gitlab_response):
        """测试同步新项目"""
        service = GitLabService()

        # Mock GitLab客户端
        with patch.object(service.client, 'get_project') as mock_get_project:
            mock_get_project.return_value = mock_gitlab_response

            # Mock数据库会话
            mock_db = Mock()
            mock_project = Mock()
            mock_project.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            # Mock Project model
            with patch('src.services.gitlab_service.Project') as MockProject:
                MockProject.return_value = mock_project

                result = await service.sync_project(mock_db, 123)

                assert result is not None
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
                MockProject.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_project_existing(self, mock_gitlab_response):
        """测试同步现有项目"""
        service = GitLabService()

        # Mock GitLab客户端
        with patch.object(service.client, 'get_project') as mock_get_project:
            mock_get_project.return_value = mock_gitlab_response

            # Mock数据库会话和现有项目
            mock_db = Mock()
            mock_project = Mock()
            mock_project.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = mock_project
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            result = await service.sync_project(mock_db, 123)

            assert result is not None
            mock_db.commit.assert_called_once()
            # 不应该创建新项目
            mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_pipelines_new(self, mock_pipeline_response):
        """测试同步新流水线"""
        service = GitLabService()

        # Mock GitLab客户端
        with patch.object(service.client, 'get_pipelines') as mock_get_pipelines:
            mock_get_pipelines.return_value = [mock_pipeline_response]

            # Mock数据库会话
            mock_db = Mock()
            mock_pipeline = Mock()
            mock_pipeline.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            # Mock Pipeline model
            with patch('src.services.gitlab_service.Pipeline') as MockPipeline:
                MockPipeline.return_value = mock_pipeline

                result = await service.sync_pipelines(mock_db, 123)

                assert len(result) == 1
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
                MockPipeline.assert_called_once()


class TestWebhookProcessing:
    """测试Webhook处理"""

    @pytest.mark.asyncio
    async def test_verify_signature_no_secret(self):
        """测试Webhook签名验证（无secret）"""
        from src.integrations.gitlab.webhook import WebhookProcessor

        processor = WebhookProcessor()

        # 测试无配置secret时返回True
        with patch('src.integrations.gitlab.webhook.settings') as mock_settings:
            mock_settings.gitlab_webhook_secret = None
            result = await processor.verify_signature(b"test payload", "signature")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_signature_with_secret(self):
        """测试Webhook签名验证（有secret）"""
        from src.integrations.gitlab.webhook import WebhookProcessor
        import hmac
        import hashlib

        processor = WebhookProcessor()

        # 测试正确的签名
        with patch('src.integrations.gitlab.webhook.settings') as mock_settings:
            secret = b"test-secret"
            payload = b"test payload"
            expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
            
            mock_settings.gitlab_webhook_secret = secret.decode()
            result = await processor.verify_signature(payload, f"sha256={expected_signature}")
            assert result is True

    @pytest.mark.asyncio
    async def test_handle_push_event(self):
        """测试处理Push事件"""
        from src.integrations.gitlab.webhook import WebhookProcessor

        processor = WebhookProcessor()

        # Mock事件数据
        event_data = {
            "project": {"id": 123},
            "ref": "refs/heads/main",
            "commits": [{"id": "abc123"}],
        }

        # Mock数据库和GitLab服务
        mock_db = Mock()
        with patch('src.integrations.gitlab.webhook.gitlab_service') as mock_service:
            mock_service.sync_project = AsyncMock()

            await processor.handle_push_event(event_data, mock_db)
            mock_service.sync_project.assert_called_once_with(mock_db, 123)

    @pytest.mark.asyncio
    async def test_handle_pipeline_event(self):
        """测试处理Pipeline事件"""
        from src.integrations.gitlab.webhook import WebhookProcessor

        processor = WebhookProcessor()

        # Mock事件数据
        event_data = {
            "object_attributes": {
                "id": 456,
                "status": "success",
            },
            "project": {"id": 123},
        }

        # Mock数据库
        mock_db = Mock()

        # 应该不抛出异常
        await processor.handle_pipeline_event(event_data, mock_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
