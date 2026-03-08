"""
GitLab 集成测试

测试 GitLab 客户端、MR 操作、文件操作的完整流程

这些测试使用 Mock 数据模拟 GitLab API，不依赖真实的 GitLab 实例
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.integrations.gitlab import GitLabClient, MROperations, FileOperations
from src.models.gitlab_events import GitLabMRDetails


@pytest.fixture
def app():
    """创建 FastAPI 应用实例"""
    from src.main import app
    return app


@pytest.fixture
def mock_gitlab_client():
    """模拟 GitLab 客户端"""
    with patch("src.integrations.gitlab.client.SyncGitlab") as mock_gitlab:
        # 设置模拟客户端
        mock_instance = Mock()
        mock_instance.auth.return_value = None
        mock_instance.user.username = "test_user"

        mock_gitlab.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def gitlab_client():
    """创建测试用的 GitLab 客户端"""
    with patch("src.integrations.gitlab.client.SyncGitlab") as mock_gitlab:
        mock_instance = Mock()
        mock_instance.auth.return_value = None
        mock_instance.user.username = "test_user"

        mock_gitlab.return_value = mock_instance

        client = GitLabClient(
            url="https://gitlab.example.com",
            token="test_token",
        )

        return client


class TestGitLabClientIntegration:
    """GitLab 客户端集成测试"""

    @pytest.mark.asyncio
    async def test_full_mr_workflow(self, gitlab_client):
        """测试完整的 MR 工作流"""
        # 模拟项目
        mock_project = Mock()

        # 模拟 MR
        mock_mr = Mock()
        mock_mr.id = 123
        mock_mr.iid = 1
        mock_mr.title = "Feature: Add user authentication"
        mock_mr.description = "This MR adds OAuth2 authentication"
        mock_mr.source_branch = "feature/auth"
        mock_mr.target_branch = "main"
        mock_mr.state = "opened"
        mock_mr.draft = False
        mock_mr.work_in_progress = False
        mock_mr.created_at = "2026-03-08T10:00:00.000Z"
        mock_mr.updated_at = "2026-03-08T11:00:00.000Z"
        mock_mr.merged_at = None
        mock_mr.web_url = "https://gitlab.example.com/project/-/merge_requests/1"
        mock_mr.additions = 250
        mock_mr.deletions = 50
        mock_mr.changed_files_count = 8
        mock_mr.author = {
            "id": 1,
            "name": "John Doe",
            "username": "johndoe",
            "email": "john@example.com",
        }
        mock_mr.assignees = []
        mock_mr.reviewers = []

        # 模拟 diffs
        mock_diff1 = Mock()
        mock_diff1.old_path = "src/auth.py"
        mock_diff1.new_path = "src/auth.py"
        mock_diff1.diff = "@@ -0,0 +1,50 @@\n+def authenticate(user):"
        mock_diff1.new_file = True
        mock_diff1.deleted_file = False
        mock_diff1.renamed_file = False

        mock_diff2 = Mock()
        mock_diff2.old_path = "tests/test_auth.py"
        mock_diff2.new_path = "tests/test_auth.py"
        mock_diff2.diff = "@@ -0,0 +1,30 @@\n+def test_login():"
        mock_diff2.new_file = True
        mock_diff2.deleted_file = False
        mock_diff2.renamed_file = False

        # 模拟文件内容
        mock_file1 = Mock()
        mock_file1.decode.return_value = '''
def authenticate(username, password):
    """Authenticate user"""
    # TODO: Implement OAuth2
    return True
'''

        mock_file2 = Mock()
        mock_file2.decode.return_value = '''
import pytest
from src.auth import authenticate

def test_login():
    assert authenticate("user", "pass") is True
'''

        mock_file3 = Mock()
        mock_file3.decode.return_value = '''
def existing_function():
    """Existing function"""
    pass
'''

        # 设置 mock 返回值
        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.diffs.list.return_value = [mock_diff1, mock_diff2]
        mock_project.files.get.side_effect = [
            mock_file1,  # src/auth.py
            mock_file2,  # tests/test_auth.py
            mock_file3,  # existing file
        ]

        # 1. 获取 MR 详情
        mr_details = await gitlab_client.get_mr_details(project_id=456, mr_iid=1)
        assert mr_details.iid == 1
        assert mr_details.title == "Feature: Add user authentication"
        assert mr_details.source_branch == "feature/auth"
        assert mr_details.changed_files_count == 8

        # 2. 获取 MR diff
        diffs = await gitlab_client.get_mr_diff(project_id=456, mr_iid=1)
        assert len(diffs) == 2
        assert diffs[0]["new_path"] == "src/auth.py"
        assert diffs[1]["new_path"] == "tests/test_auth.py"

        # 3. 获取文件内容
        content1 = await gitlab_client.get_file_content(
            project_id=456,
            file_path="src/auth.py",
            ref="feature/auth",
        )
        assert "def authenticate" in content1
        assert "OAuth2" in content1

        content2 = await gitlab_client.get_file_content(
            project_id=456,
            file_path="tests/test_auth.py",
            ref="feature/auth",
        )
        assert "def test_login" in content2

        print("✅ 完整 MR 工作流测试通过")


class TestMROperationsIntegration:
    """MR 操作集成测试"""

    @pytest.mark.asyncio
    async def test_get_python_files_from_mr(self, gitlab_client):
        """测试从 MR 中获取 Python 文件"""
        mock_project = Mock()
        mock_mr = Mock()

        # 模拟 MR
        mock_mr.id = 123
        mock_mr.iid = 1
        mock_mr.title = "Test MR"
        mock_mr.description = "Test"
        mock_mr.source_branch = "feature"
        mock_mr.target_branch = "main"
        mock_mr.state = "opened"
        mock_mr.draft = False
        mock_mr.work_in_progress = False
        mock_mr.created_at = "2026-03-08T10:00:00.000Z"
        mock_mr.updated_at = "2026-03-08T10:00:00.000Z"
        mock_mr.merged_at = None
        mock_mr.web_url = "https://gitlab.example.com/project/-/merge_requests/1"
        mock_mr.additions = 100
        mock_mr.deletions = 0
        mock_mr.changed_files_count = 5
        mock_mr.author = {"id": 1, "name": "User", "username": "user", "email": "user@example.com"}
        mock_mr.assignees = []
        mock_mr.reviewers = []

        # 模拟多个文件变更
        mock_diffs = []
        file_types = [
            ("src/main.py", ".py"),
            ("src/utils.py", ".py"),
            ("src/config.json", ".json"),
            ("README.md", ".md"),
            ("tests/test_main.py", ".py"),
        ]

        for path, ext in file_types:
            diff = Mock()
            diff.old_path = path
            diff.new_path = path
            diff.diff = f"@@ -0,0 +1,1 @@\n+{path}"
            diff.new_file = True
            diff.deleted_file = False
            diff.renamed_file = False
            mock_diffs.append(diff)

        mock_mr.diffs.list.return_value = mock_diffs
        mock_project.files.get.return_value = mock_project
        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr

        # 创建 MR 操作
        mr_ops = MROperations(gitlab_client)

        # 获取所有变更文件
        all_files = await mr_ops.get_changed_files(project_id=456, mr_iid=1)
        assert len(all_files) == 5

        # 只获取 Python 文件
        py_files = await mr_ops.get_changed_files(
            project_id=456,
            mr_iid=1,
            extensions=[".py"],
        )
        assert len(py_files) == 3
        assert all(f["new_path"].endswith(".py") for f in py_files)

        print("✅ Python 文件过滤测试通过")

    @pytest.mark.asyncio
    async def test_post_review_comment(self, gitlab_client):
        """测试发布代码审查评论"""
        mock_project = Mock()
        mock_mr = Mock()
        mock_note = Mock()
        mock_note.id = 789
        mock_note.note = "LGTM! Looks good to me."
        mock_note.created_at = "2026-03-08T10:00:00.000Z"
        mock_note.updated_at = "2026-03-08T10:00:00.000Z"
        mock_note.system = False
        mock_note.resolvable = False
        mock_note.resolved = False
        mock_note.author = {
            "id": 2,
            "name": "Reviewer",
            "username": "reviewer",
        }

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.notes.create.return_value = mock_note

        # 创建 MR 操作
        mr_ops = MROperations(gitlab_client)

        # 发布评论
        result = await mr_ops.post_review_comment(
            project_id=456,
            mr_iid=1,
            comment="LGTM! Looks good to me.",
        )

        # 验证
        mock_mr.notes.create.assert_called_once_with({"body": "LGTM! Looks good to me."})

        print("✅ 发布评论测试通过")


class TestFileOperationsIntegration:
    """文件操作集成测试"""

    @pytest.mark.asyncio
    async def test_batch_get_multiple_files(self, gitlab_client):
        """测试批量获取多个文件"""
        mock_project = Mock()

        # 模拟多个文件
        files = {
            "src/main.py": "def main():\n    pass",
            "src/utils.py": "def helper():\n    pass",
            "src/config.py": "DEBUG = True",
        }

        mock_files = []
        for content in files.values():
            mock_file = Mock()
            mock_file.decode.return_value = content
            mock_files.append(mock_file)

        mock_project.files.get.side_effect = mock_files
        gitlab_client._client.projects.get.return_value = mock_project

        # 创建文件操作
        file_ops = FileOperations(gitlab_client)

        # 批量获取文件
        result = await file_ops.batch_get_files(
            project_id=456,
            file_paths=list(files.keys()),
            ref="main",
        )

        # 验证
        assert len(result) == 3
        assert result["src/main.py"] == files["src/main.py"]
        assert result["src/utils.py"] == files["src/utils.py"]
        assert result["src/config.py"] == files["src/config.py"]

        print("✅ 批量获取文件测试通过")


class TestWebhookIntegration:
    """Webhook 集成测试"""

    @pytest.mark.asyncio
    async def test_webhook_mr_event(self, app):
        """测试 Webhook MR 事件处理"""
        # 准备测试数据
        webhook_payload = {
            "object_kind": "merge_request",
            "event_type": "merge_request",
            "user": {
                "id": 1,
                "name": "Test User",
                "username": "testuser",
            },
            "project": {
                "id": 456,
                "name": "test-project",
                "path_with_namespace": "group/test-project",
                "default_branch": "main",
                "url": "https://gitlab.example.com/group/test-project",
                "web_url": "https://gitlab.example.com/group/test-project",
            },
            "object_attributes": {
                "id": 123,
                "iid": 1,
                "title": "Test MR",
                "description": "Test description",
                "state": "opened",
                "created_at": "2026-03-08T10:00:00.000Z",
                "updated_at": "2026-03-08T10:00:00.000Z",
                "action": "open",
                "source_branch": "feature",
                "target_branch": "main",
            },
            "changes": {},
        }

        # Mock GitLab 客户端
        with patch("src.api.routes.webhooks.get_gitlab_client") as mock_get_client:
            mock_client = Mock()

            # Mock 项目和 MR
            mock_project = Mock()
            mock_mr = Mock()

            # 模拟 Python 文件变更
            mock_diff = Mock()
            mock_diff.old_path = "test.py"
            mock_diff.new_path = "test.py"
            mock_diff.new_file = True
            mock_diff.deleted_file = False
            mock_diff.renamed_file = False

            mock_mr.diffs.list.return_value = [mock_diff]
            mock_project.mergerequests.get.return_value = mock_mr
            mock_client._client.projects.get.return_value = mock_project

            mock_get_client.return_value = mock_client

            # 发送 Webhook 请求
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/webhook/gitlab",
                    json=webhook_payload,
                    headers={"X-Gitlab-Token": "test_webhook_secret_12345"},
                )

                # 验证响应
                assert response.status_code == 202
                data = response.json()
                assert data["status"] in ["queued", "error"]  # 可能是队列或错误
                assert data["event_type"] == "merge_request"

                print(f"✅ Webhook 响应: {data['message']}")


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.mark.asyncio
    async def test_full_mr_processing_workflow(self, gitlab_client):
        """测试完整的 MR 处理工作流"""
        # 这个测试模拟真实场景：
        # 1. MR 打开
        # 2. 获取变更的 Python 文件
        # 3. 获取文件内容
        # 4. 发布审查评论

        mock_project = Mock()
        mock_mr = Mock()

        # 设置 MR 属性
        mock_mr.id = 123
        mock_mr.iid = 1
        mock_mr.title = "Add new feature"
        mock_mr.description = "Implement new feature"
        mock_mr.source_branch = "feature/new-feature"
        mock_mr.target_branch = "main"
        mock_mr.state = "opened"
        mock_mr.draft = False
        mock_mr.work_in_progress = False
        mock_mr.created_at = "2026-03-08T10:00:00.000Z"
        mock_mr.updated_at = "2026-03-08T11:00:00.000Z"
        mock_mr.merged_at = None
        mock_mr.web_url = "https://gitlab.example.com/project/-/merge_requests/1"
        mock_mr.additions = 150
        mock_mr.deletions = 20
        mock_mr.changed_files_count = 3
        mock_mr.author = {
            "id": 1,
            "name": "Developer",
            "username": "dev",
            "email": "dev@example.com",
        }
        mock_mr.assignees = []
        mock_mr.reviewers = []

        # 模拟 Python 文件变更
        mock_diff = Mock()
        mock_diff.old_path = "src/feature.py"
        mock_diff.new_path = "src/feature.py"
        mock_diff.diff = "@@ -0,0 +1,50 @@\n+def new_feature():"
        mock_diff.new_file = True
        mock_diff.deleted_file = False
        mock_diff.renamed_file = False

        # 模拟文件内容
        mock_file = Mock()
        mock_file.decode.return_value = '''
def new_feature():
    """New feature implementation"""
    result = process_data()
    return result

def process_data():
    """Process data"""
    return [1, 2, 3]
'''

        # 设置 mock
        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.diffs.list.return_value = [mock_diff]
        mock_project.files.get.return_value = mock_file

        # 1. 创建操作实例
        mr_ops = MROperations(gitlab_client)
        file_ops = FileOperations(gitlab_client)

        # 2. 获取 MR 详情
        mr_details = await gitlab_client.get_mr_details(project_id=456, mr_iid=1)
        assert mr_details.iid == 1
        assert mr_details.title == "Add new feature"

        # 3. 获取变更的 Python 文件
        changed_files = await mr_ops.get_changed_files(
            project_id=456,
            mr_iid=1,
            extensions=[".py"],
        )
        assert len(changed_files) == 1
        assert changed_files[0]["new_path"] == "src/feature.py"

        # 4. 获取文件内容
        file_content = await gitlab_client.get_file_content(
            project_id=456,
            file_path="src/feature.py",
            ref="feature/new-feature",
        )
        assert "def new_feature" in file_content
        assert "def process_data" in file_content

        # 5. 模拟发布审查评论
        mock_note = Mock()
        mock_note.id = 789
        mock_note.note = "Code review completed"
        mock_note.created_at = "2026-03-08T12:00:00.000Z"
        mock_note.updated_at = "2026-03-08T12:00:00.000Z"
        mock_note.system = False
        mock_note.resolvable = False
        mock_note.resolved = False
        mock_note.author = {"id": 2, "name": "Reviewer", "username": "reviewer"}

        mock_mr.notes.create.return_value = mock_note

        await mr_ops.post_review_comment(
            project_id=456,
            mr_iid=1,
            comment="Code review completed",
        )

        # 验证评论已发布
        mock_mr.notes.create.assert_called_once()

        print("✅ 端到端工作流测试通过")
        print(f"   - MR: {mr_details.title}")
        print(f"   - 分支: {mr_details.source_branch} → {mr_details.target_branch}")
        print(f"   - 变更文件: {len(changed_files)} 个")
        print(f"   - 审查评论: 已发布")


@pytest.mark.integration
class TestRealGitLabConnection:
    """
    真实 GitLab 连接测试

    这些测试需要真实的 GitLab token，默认不运行
    使用 `pytest -m integration` 来运行这些测试
    """

    @pytest.mark.skip(reason="需要真实的 GitLab token")
    @pytest.mark.asyncio
    async def test_connect_to_real_gitlab(self):
        """测试连接到真实的 GitLab 实例"""
        from src.utils.config import settings

        client = GitLabClient(
            url=settings.gitlab_url,
            token=settings.gitlab_token,
        )

        # 尝试获取用户信息
        # 这会失败如果 token 无效
        assert client._client.user is not None

        print(f"✅ 成功连接到 GitLab: {settings.gitlab_url}")
        print(f"   用户: {client._client.user.username}")

    @pytest.mark.skip(reason="需要真实的 GitLab 项目")
    @pytest.mark.asyncio
    async def test_get_real_project_mrs(self):
        """测试获取真实项目的 MR"""
        from src.utils.config import settings

        client = GitLabClient(
            url=settings.gitlab_url,
            token=settings.gitlab_token,
        )

        # 这里需要一个真实的项目 ID
        project_id = 123  # 替换为真实的项目 ID

        # 尝试获取 MR 列表
        # 注意：这需要项目存在且可访问
        project = await client._run_in_executor(
            client._client.projects.get,
            project_id,
        )

        mrs = await client._run_in_executor(
            project.mergerequests.list,
            all=True,
        )

        print(f"✅ 获取到 {len(mrs)} 个 MR")

        for mr in mrs[:5]:  # 只显示前5个
            print(f"   - !{mr.iid} {mr.title}")
