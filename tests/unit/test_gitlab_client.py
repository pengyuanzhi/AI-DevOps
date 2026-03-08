"""
GitLab 客户端单元测试

测试 GitLab API 客户端的基本功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.integrations.gitlab import (
    GitLabClient,
    GitLabAPIError,
    GitLabAuthenticationError,
)
from src.models.gitlab_events import GitLabMRDetails


@pytest.fixture
def mock_gitlab():
    """模拟 python-gitlab 客户端"""
    with patch("src.integrations.gitlab.client.SyncGitlab") as mock:
        yield mock


@pytest.fixture
def gitlab_client(mock_gitlab):
    """创建测试用的 GitLab 客户端"""
    mock_instance = Mock()
    mock_instance.auth.return_value = None
    mock_instance.user.username = "test_user"

    mock_gitlab.return_value = mock_instance

    client = GitLabClient(
        url="https://gitlab.example.com",
        token="test_token",
    )

    return client


class TestGitLabClient:
    """GitLab 客户端测试"""

    def test_client_initialization(self, mock_gitlab):
        """测试客户端初始化"""
        mock_instance = Mock()
        mock_instance.auth.return_value = None
        mock_instance.user.username = "test_user"

        mock_gitlab.return_value = mock_instance

        client = GitLabClient(
            url="https://gitlab.example.com",
            token="test_token",
        )

        assert client.url == "https://gitlab.example.com"
        assert client.token == "test_token"
        mock_gitlab.assert_called_once()
        mock_instance.auth.assert_called_once()

    def test_client_authentication_error(self, mock_gitlab):
        """测试认证失败"""
        from gitlab.exceptions import GitlabAuthenticationError

        mock_instance = Mock()
        mock_instance.auth.side_effect = GitlabAuthenticationError("Invalid token")

        mock_gitlab.return_value = mock_instance

        with pytest.raises(GitLabAuthenticationError):
            GitLabClient(
                url="https://gitlab.example.com",
                token="invalid_token",
            )

    @pytest.mark.asyncio
    async def test_get_mr_details_success(self, gitlab_client):
        """测试成功获取 MR 详情"""
        # 模拟返回数据
        mock_project = Mock()
        mock_mr = Mock()
        mock_mr.id = 123
        mock_mr.iid = 1
        mock_mr.title = "Test MR"
        mock_mr.description = "Test description"
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
        mock_mr.deletions = 50
        mock_mr.changed_files_count = 5
        mock_mr.author = {
            "id": 1,
            "name": "Test User",
            "username": "testuser",
            "email": "test@example.com",
        }
        mock_mr.assignees = []
        mock_mr.reviewers = []

        # 模拟 API 调用
        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr

        # 执行测试
        result = await gitlab_client.get_mr_details(project_id=456, mr_iid=1)

        # 验证结果
        assert isinstance(result, GitLabMRDetails)
        assert result.iid == 1
        assert result.title == "Test MR"
        assert result.source_branch == "feature"
        assert result.target_branch == "main"
        assert result.state == "opened"

    @pytest.mark.asyncio
    async def test_get_mr_details_not_found(self, gitlab_client):
        """测试 MR 不存在"""
        from gitlab.exceptions import GitlabError

        mock_project = Mock()
        mock_project.mergerequests.get.side_effect = GitlabError("Not found")

        gitlab_client._client.projects.get.return_value = mock_project

        with pytest.raises(GitLabAPIError):
            await gitlab_client.get_mr_details(project_id=456, mr_iid=999)

    @pytest.mark.asyncio
    async def test_get_mr_diff(self, gitlab_client):
        """测试获取 MR diff"""
        mock_project = Mock()
        mock_mr = Mock()

        # 模拟 diff 数据
        mock_diff = Mock()
        mock_diff.old_path = "old/file.py"
        mock_diff.new_path = "new/file.py"
        mock_diff.diff = "@@ -1,1 +1,2 @@\n-old line\n+new line"
        mock_diff.new_file = False
        mock_diff.renamed_file = True
        mock_diff.deleted_file = False
        mock_diff.to_attr.return_value = {
            "old_path": "old/file.py",
            "new_path": "new/file.py",
            "diff": "@@ -1,1 +1,2 @@\n-old line\n+new line",
            "new_file": False,
            "renamed_file": True,
            "deleted_file": False,
        }

        # 模拟 diffs.list() 返回列表
        mock_mr.diffs.list.return_value = [mock_diff]

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr

        # 执行测试
        diffs = await gitlab_client.get_mr_diff(project_id=456, mr_iid=1)

        # 验证结果
        assert len(diffs) == 1
        assert diffs[0]["old_path"] == "old/file.py"
        assert diffs[0]["new_path"] == "new/file.py"
        assert diffs[0]["renamed_file"] is True

    @pytest.mark.asyncio
    async def test_get_file_content(self, gitlab_client):
        """测试获取文件内容"""
        mock_project = Mock()
        mock_file = Mock()
        mock_file.decode.return_value = "def hello():\n    print('world')"

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.files.get.return_value = mock_file

        # 执行测试
        content = await gitlab_client.get_file_content(
            project_id=456,
            file_path="src/hello.py",
            ref="main",
        )

        # 验证结果
        assert content == "def hello():\n    print('world')"
        mock_project.files.get.assert_called_once_with("src/hello.py", ref="main")

    @pytest.mark.asyncio
    async def test_create_mr_note(self, gitlab_client):
        """测试创建 MR 评论"""
        mock_project = Mock()
        mock_mr = Mock()
        mock_note = Mock()
        mock_note.id = 789
        mock_note.note = "Test comment"
        mock_note.created_at = "2026-03-08T10:00:00.000Z"
        mock_note.updated_at = "2026-03-08T10:00:00.000Z"
        mock_note.system = False
        mock_note.resolvable = False
        mock_note.resolved = False
        mock_note.author = {
            "id": 1,
            "name": "Test User",
            "username": "testuser",
        }

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.notes.create.return_value = mock_note

        # 执行测试
        result = await gitlab_client.create_mr_note(
            project_id=456,
            mr_iid=1,
            note="Test comment",
        )

        # 验证结果
        assert result.id == 789
        assert result.note == "Test comment"
        assert result.author.username == "testuser"
        mock_mr.notes.create.assert_called_once_with({"body": "Test comment"})


class TestMROperations:
    """MR 操作测试"""

    @pytest.mark.asyncio
    async def test_get_changed_files(self, gitlab_client):
        """测试获取变更文件"""
        from src.integrations.gitlab.mr_operations import MROperations

        mock_project = Mock()
        mock_mr = Mock()

        # 模拟 diff 数据
        mock_diff1 = Mock()
        mock_diff1.old_path = "test1.py"
        mock_diff1.new_path = "test1.py"
        mock_diff1.new_file = True
        mock_diff1.deleted_file = False
        mock_diff1.renamed_file = False

        mock_diff2 = Mock()
        mock_diff2.old_path = "test.js"
        mock_diff2.new_path = "test.js"
        mock_diff2.new_file = True
        mock_diff2.deleted_file = False
        mock_diff2.renamed_file = False

        # 模拟 diffs.list() 返回列表
        mock_mr.diffs.list.return_value = [mock_diff1, mock_diff2]

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr

        # 创建 MR 操作实例
        mr_ops = MROperations(gitlab_client)

        # 测试不使用过滤器
        all_files = await mr_ops.get_changed_files(project_id=456, mr_iid=1)
        assert len(all_files) == 2

        # 测试使用 .py 扩展名过滤器
        py_files = await mr_ops.get_changed_files(
            project_id=456,
            mr_iid=1,
            extensions=[".py"],
        )
        assert len(py_files) == 1
        assert py_files[0]["new_path"] == "test1.py"

    @pytest.mark.asyncio
    async def test_get_new_files_content(self, gitlab_client):
        """测试获取新文件内容"""
        from src.integrations.gitlab.mr_operations import MROperations

        mock_project = Mock()
        mock_mr = Mock()
        mock_file = Mock()

        # 设置完整的 MR 属性
        mock_mr.id = 123
        mock_mr.iid = 1
        mock_mr.title = "Test MR"
        mock_mr.description = "Test description"
        mock_mr.source_branch = "feature"
        mock_mr.target_branch = "main"
        mock_mr.state = "opened"
        mock_mr.draft = False
        mock_mr.work_in_progress = False
        mock_mr.created_at = "2026-03-08T10:00:00.000Z"
        mock_mr.updated_at = "2026-03-08T10:00:00.000Z"
        mock_mr.merged_at = None
        mock_mr.web_url = "https://gitlab.example.com/project/-/merge_requests/1"
        mock_mr.additions = 10
        mock_mr.deletions = 0
        mock_mr.changed_files_count = 1
        mock_mr.author = {
            "id": 1,
            "name": "Test User",
            "username": "testuser",
            "email": "test@example.com",
        }
        mock_mr.assignees = []
        mock_mr.reviewers = []

        mock_diff = Mock()
        mock_diff.old_path = "test.py"
        mock_diff.new_path = "test.py"
        mock_diff.new_file = True
        mock_diff.deleted_file = False
        mock_diff.renamed_file = False

        mock_file.decode.return_value = "print('hello')"

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.mergerequests.get.return_value = mock_mr
        mock_mr.diffs.list.return_value = [mock_diff]
        mock_project.files.get.return_value = mock_file

        # 创建 MR 操作实例
        mr_ops = MROperations(gitlab_client)

        # 执行测试
        files_content = await mr_ops.get_new_files_content(
            project_id=456,
            mr_iid=1,
            extensions=[".py"],
        )

        # 验证结果
        assert "test.py" in files_content
        assert files_content["test.py"] == "print('hello')"


class TestFileOperations:
    """文件操作测试"""

    @pytest.mark.asyncio
    async def test_batch_get_files(self, gitlab_client):
        """测试批量获取文件"""
        from src.integrations.gitlab.file_operations import FileOperations

        mock_project = Mock()
        mock_file = Mock()
        mock_file.decode.return_value = "content"

        gitlab_client._client.projects.get.return_value = mock_project
        mock_project.files.get.return_value = mock_file

        # 创建文件操作实例
        file_ops = FileOperations(gitlab_client)

        # 执行测试
        files = await file_ops.batch_get_files(
            project_id=456,
            file_paths=["file1.py", "file2.py"],
            ref="main",
        )

        # 验证结果
        assert len(files) == 2
        assert files["file1.py"] == "content"
        assert files["file2.py"] == "content"
