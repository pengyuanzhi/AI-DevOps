"""
GitLab Webhook 集成测试（C++ 项目支持）
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.api.routes.webhooks import (
    _detect_project_type,
    _handle_cpp_mr,
    _handle_python_mr,
    handle_merge_request_event,
)


@pytest.mark.asyncio
class TestWebhookProjectDetection:
    """Webhook 项目类型检测测试"""

    async def test_detect_cpp_project(self):
        """测试检测 C++ 项目"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "src/main.cpp", "deleted_file": False},
                {"new_path": "include/calculator.h", "deleted_file": False},
                {"new_path": "tests/test_calculator.cpp", "deleted_file": False},
            ]
        )

        # 检测项目类型
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=123,
            mr_iid=1,
        )

        assert project_type == "cpp"
        mr_ops.get_changed_files.assert_called_once()

    async def test_detect_python_project(self):
        """测试检测 Python 项目"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "src/main.py", "deleted_file": False},
                {"new_path": "tests/test_main.py", "deleted_file": False},
            ]
        )

        # 检测项目类型
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=123,
            mr_iid=1,
        )

        assert project_type == "python"

    async def test_detect_mixed_project(self):
        """测试检测混合项目（优先 C++）"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "src/main.cpp", "deleted_file": False},
                {"new_path": "src/utils.py", "deleted_file": False},
            ]
        )

        # 检测项目类型（应该优先检测到 C++）
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=123,
            mr_iid=1,
        )

        assert project_type == "cpp"

    async def test_detect_unknown_project(self):
        """测试检测未知项目"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "README.md", "deleted_file": False},
                {"new_path": "docs/api.txt", "deleted_file": False},
            ]
        )

        # 检测项目类型
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=123,
            mr_iid=1,
        )

        assert project_type == "unknown"

    async def test_detect_cpp_with_header_files(self):
        """测试检测 C++ 项目（只有头文件）"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "include/calculator.h", "deleted_file": False},
                {"new_path": "include/utils.hpp", "deleted_file": False},
            ]
        )

        # 检测项目类型
        project_type = await _detect_project_type(
            mr_ops=mr_ops,
            project_id=123,
            mr_iid=1,
        )

        assert project_type == "cpp"


@pytest.mark.asyncio
class TestWebhookCppHandling:
    """Webhook C++ MR 处理测试"""

    async def test_handle_cpp_mr_success(self):
        """测试成功处理 C++ MR"""
        # Mock MROperations
        mr_ops = Mock()

        # Mock CppGitLabService
        mock_result = Mock()
        mock_result.success = True
        mock_result.total_tests_generated = 5
        mock_result.total_reviews_done = 2

        with patch(
            "src.services.cpp_gitlab_service.get_cpp_gitlab_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.mr_operations = None
            mock_service.process_merge_request = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            # 处理 C++ MR
            event_data = {
                "object_attributes": {
                    "action": "open",
                    "title": "Add new feature",
                },
                "project": {"id": 123},
                "object_attributes": {"iid": 1, "title": "Test MR"},
            }

            response = await _handle_cpp_mr(
                mr_ops=mr_ops,
                event_data=event_data,
                project_id=123,
                mr_iid=1,
                mr_title="Test MR",
            )

            assert response.status == "completed"
            assert "5 个测试" in response.message
            assert "2 个文件" in response.message
            assert response.event_type == "merge_request"

            # 验证服务被正确调用
            assert mock_service.mr_operations == mr_ops
            mock_service.process_merge_request.assert_called_once_with(
                project_id=123,
                mr_iid=1,
                options={
                    "generate_tests": True,
                    "run_review": True,
                    "post_comments": True,
                },
            )

    async def test_handle_cpp_mr_partial_success(self):
        """测试部分成功处理 C++ MR"""
        # Mock MROperations
        mr_ops = Mock()

        # Mock CppGitLabService with errors
        mock_result = Mock()
        mock_result.success = False
        mock_result.errors = ["Error 1", "Error 2"]

        with patch(
            "src.services.cpp_gitlab_service.get_cpp_gitlab_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.mr_operations = None
            mock_service.process_merge_request = AsyncMock(return_value=mock_result)
            mock_get_service.return_value = mock_service

            # 处理 C++ MR
            event_data = {}
            response = await _handle_cpp_mr(
                mr_ops=mr_ops,
                event_data=event_data,
                project_id=123,
                mr_iid=1,
                mr_title="Test MR",
            )

            assert response.status == "partial_success"
            assert "2 个错误" in response.message

    async def test_handle_cpp_mr_exception(self):
        """测试处理 C++ MR 异常"""
        # Mock MROperations
        mr_ops = Mock()

        with patch(
            "src.services.cpp_gitlab_service.get_cpp_gitlab_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_service.mr_operations = None
            mock_service.process_merge_request = AsyncMock(
                side_effect=Exception("Service error")
            )
            mock_get_service.return_value = mock_service

            # 处理 C++ MR 应该抛出异常
            event_data = {}
            with pytest.raises(Exception, match="Service error"):
                await _handle_cpp_mr(
                    mr_ops=mr_ops,
                    event_data=event_data,
                    project_id=123,
                    mr_iid=1,
                    mr_title="Test MR",
                )


@pytest.mark.asyncio
class TestWebhookPythonHandling:
    """Webhook Python MR 处理测试"""

    async def test_handle_python_mr(self):
        """测试处理 Python MR"""
        # Mock MROperations
        mr_ops = Mock()
        mr_ops.get_changed_files = AsyncMock(
            return_value=[
                {"new_path": "src/main.py", "deleted_file": False},
            ]
        )

        # 处理 Python MR
        event_data = {}
        response = await _handle_python_mr(
            mr_ops=mr_ops,
            event_data=event_data,
            project_id=123,
            mr_iid=1,
            mr_title="Test MR",
        )

        assert response.status == "queued"
        assert "Python MR" in response.message
        assert "1 个 Python 文件" in response.message
        assert response.event_type == "merge_request"


@pytest.mark.asyncio
class TestWebhookMREvent:
    """Webhook MR 事件处理测试"""

    async def test_handle_cpp_mr_event(self):
        """测试处理 C++ MR 事件"""
        event_data = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "iid": 1,
                "title": "Add C++ feature",
            },
            "project": {"id": 123},
        }

        with patch("src.api.routes.webhooks.get_gitlab_client") as mock_get_client:
            # Mock GitLab client
            mock_client = Mock()

            with patch("src.integrations.gitlab.MROperations") as mock_mr_ops_class:
                # Mock MROperations instance
                mock_mr_ops = Mock()
                mock_mr_ops.get_changed_files = AsyncMock(
                    return_value=[
                        {"new_path": "src/main.cpp", "deleted_file": False},
                    ]
                )
                mock_mr_ops_class.return_value = mock_mr_ops
                mock_get_client.return_value = mock_client

                with patch(
                    "src.api.routes.webhooks._handle_cpp_mr"
                ) as mock_handle_cpp:
                    mock_handle_cpp.return_value = Mock(
                        status="completed",
                        message="Success",
                        event_type="merge_request",
                    )

                    # 处理事件
                    response = await handle_merge_request_event(event_data)

                    assert response.status == "completed"
                    mock_handle_cpp.assert_called_once()

    async def test_handle_python_mr_event(self):
        """测试处理 Python MR 事件"""
        event_data = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "iid": 1,
                "title": "Add Python feature",
            },
            "project": {"id": 123},
        }

        with patch("src.api.routes.webhooks.get_gitlab_client") as mock_get_client:
            mock_client = Mock()

            with patch("src.integrations.gitlab.MROperations") as mock_mr_ops_class:
                mock_mr_ops = Mock()
                mock_mr_ops.get_changed_files = AsyncMock(
                    return_value=[
                        {"new_path": "src/main.py", "deleted_file": False},
                    ]
                )
                mock_mr_ops_class.return_value = mock_mr_ops
                mock_get_client.return_value = mock_client

                with patch(
                    "src.api.routes.webhooks._handle_python_mr"
                ) as mock_handle_py:
                    mock_handle_py.return_value = Mock(
                        status="queued",
                        message="Queued",
                        event_type="merge_request",
                    )

                    # 处理事件
                    response = await handle_merge_request_event(event_data)

                    assert response.status == "queued"

    async def test_handle_unknown_mr_event(self):
        """测试处理未知项目类型的 MR 事件"""
        event_data = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "iid": 1,
                "title": "Add documentation",
            },
            "project": {"id": 123},
        }

        with patch("src.api.routes.webhooks.get_gitlab_client") as mock_get_client:
            mock_client = Mock()

            with patch("src.integrations.gitlab.MROperations") as mock_mr_ops_class:
                mock_mr_ops = Mock()
                mock_mr_ops.get_changed_files = AsyncMock(
                    return_value=[
                        {"new_path": "README.md", "deleted_file": False},
                    ]
                )
                mock_mr_ops_class.return_value = mock_mr_ops
                mock_get_client.return_value = mock_client

                # 处理事件
                response = await handle_merge_request_event(event_data)

                assert response.status == "ignored"
                assert "未检测到支持的代码文件" in response.message

    async def test_handle_ignored_mr_action(self):
        """测试忽略不需要的 MR 动作"""
        event_data = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "close",  # 不需要处理的动作
                "iid": 1,
                "title": "Test",
            },
            "project": {"id": 123},
        }

        # 处理事件
        response = await handle_merge_request_event(event_data)

        assert response.status == "ignored"
        assert "不需要处理" in response.message

    async def test_handle_mr_event_with_error(self):
        """测试处理 MR 事件时发生错误"""
        event_data = {
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "iid": 1,
                "title": "Test",
            },
            "project": {"id": 123},
        }

        with patch("src.api.routes.webhooks.get_gitlab_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection error")

            # 处理事件
            response = await handle_merge_request_event(event_data)

            assert response.status == "error"
            assert "处理 MR 失败" in response.message
