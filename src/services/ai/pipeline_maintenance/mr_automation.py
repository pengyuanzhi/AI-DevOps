"""
MR自动化模块

自动创建和管理GitLab MR以应用修复
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import requests

from ....utils.logger import get_logger
from .fix_generator import FixSuggestion
from .fix_executor import ExecutionResult

logger = get_logger(__name__)


class MRStatus(str, Enum):
    """MR状态"""
    PENDING = "pending"
    CREATED = "created"
    MERGED = "merged"
    CLOSED = "closed"
    FAILED = "failed"


@dataclass
class MRAutomationResult:
    """MR自动化结果"""
    status: MRStatus
    mr_url: Optional[str] = None
    mr_id: Optional[int] = None
    suggestion_id: str = ""

    # 执行详情
    created_at: datetime = field(default_factory=datetime.now)
    error_message: str = ""

    # MR信息
    title: str = ""
    source_branch: str = ""
    target_branch: str = ""
    description: str = ""

    # 关联信息
    pipeline_id: str = ""
    job_id: str = ""


class GitLabMRAutomator:
    """
    GitLab MR自动化

    自动创建MR以应用修复
    """

    def __init__(self, gitlab_url: str, gitlab_token: str):
        self.gitlab_url = gitlab_url.rstrip('/')
        self.gitlab_token = gitlab_token
        self.headers = {
            "PRIVATE-TOKEN": gitlab_token,
            "Content-Type": "application/json",
        }

    async def create_fix_mr(
        self,
        project_id: int,
        suggestion: FixSuggestion,
        execution_result: ExecutionResult,
        pipeline_id: str,
        job_id: str,
        source_branch: str,
        target_branch: str = "main",
    ) -> MRAutomationResult:
        """
        创建修复MR

        Args:
            project_id: GitLab项目ID
            suggestion: 修复建议
            execution_result: 执行结果
            pipeline_id: 流水线ID
            job_id: 作业ID
            source_branch: 源分支名
            target_branch: 目标分支名

        Returns:
            MR自动化结果
        """
        logger.info(
            "creating_fix_mr",
            project_id=project_id,
            suggestion_id=suggestion.suggestion_id,
            source_branch=source_branch,
        )

        result = MRAutomationResult(
            status=MRStatus.PENDING,
            suggestion_id=suggestion.suggestion_id,
            pipeline_id=pipeline_id,
            job_id=job_id,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        try:
            # 1. 生成MR标题和描述
            title = self._generate_mr_title(suggestion)
            description = self._generate_mr_description(
                suggestion,
                execution_result,
                pipeline_id,
                job_id,
            )

            # 2. 创建MR
            mr_data = {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
                "remove_source_branch": False,
                "labels": self._generate_labels(suggestion),
            }

            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests"

            logger.info("calling_gitlab_api", url=url)

            response = requests.post(
                url,
                json=mr_data,
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 201:
                mr_info = response.json()

                result.status = MRStatus.CREATED
                result.mr_id = mr_info.get("iid")
                result.mr_url = mr_info.get("web_url")
                result.title = mr_info.get("title")
                result.description = mr_info.get("description")

                logger.info(
                    "mr_created_successfully",
                    mr_id=result.mr_id,
                    mr_url=result.mr_url,
                )
            else:
                result.status = MRStatus.FAILED
                result.error_message = f"GitLab API错误: {response.status_code} - {response.text}"

                logger.error(
                    "mr_creation_failed",
                    status_code=response.status_code,
                    response=response.text,
                )

            return result

        except Exception as e:
            logger.error(
                "mr_creation_exception",
                error=str(e),
                exc_info=True,
            )

            result.status = MRStatus.FAILED
            result.error_message = str(e)
            return result

    def _generate_mr_title(self, suggestion: FixSuggestion) -> str:
        """生成MR标题"""
        prefix = "[AI修复] "
        return f"{prefix}{suggestion.title}"

    def _generate_mr_description(
        self,
        suggestion: FixSuggestion,
        execution_result: ExecutionResult,
        pipeline_id: str,
        job_id: str,
    ) -> str:
        """生成MR描述"""
        description = f"""## 自动修复

此MR由AI-CICD系统自动创建。

### 修复建议

**标题**: {suggestion.title}
**类型**: {suggestion.fix_type.value}
**复杂度**: {suggestion.complexity.value}
**置信度**: {suggestion.confidence:.2f}

### 描述

{suggestion.description}

### 理由

{suggestion.rationale}

### 风险评估

**风险等级**: {suggestion.risk_level}
**预估时间**: {suggestion.estimated_time}

### 执行详情

**状态**: {execution_result.status.value}
**开始时间**: {execution_result.started_at.isoformat()}
**完成时间**: {execution_result.completed_at.isoformat() if execution_result.completed_at else 'N/A'}
**耗时**: {execution_result.duration_seconds:.2f}秒

**修改文件**: {len(execution_result.modified_files)}个
{chr(10).join(f'- {f}' for f in execution_result.modified_files[:10])}

### 验证步骤

{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(suggestion.verification_steps))}

### 预期结果

{suggestion.expected_outcome}

### 副作用

{chr(10).join(f'- {effect}' for effect in suggestion.side_effects) if suggestion.side_effects else '无'}

---

### 关联信息

- **流水线ID**: {pipeline_id}
- **作业ID**: {job_id}
- **建议ID**: {suggestion.suggestion_id}

### 注意事项

1. **请仔细审查代码变更** - 虽然AI生成了此修复，但仍需人工确认
2. **运行测试** - 确保所有测试通过
3. **检查副作用** - 验证修复没有引入新问题
4. **更新文档** - 如有必要，更新相关文档

### 审查者

请至少一名团队成员审查并批准此MR。
"""
        return description

    def _generate_labels(self, suggestion: FixSuggestion) -> List[str]:
        """生成MR标签"""
        labels = ["AI修复", "自动创建"]

        # 根据风险等级添加标签
        risk_labels = {
            "low": "低风险",
            "medium": "中风险",
            "high": "高风险",
        }
        if suggestion.risk_level in risk_labels:
            labels.append(risk_labels[suggestion.risk_level])

        # 根据修复类型添加标签
        type_labels = {
            "code_change": "代码变更",
            "config_change": "配置变更",
            "dependency_update": "依赖更新",
        }
        if suggestion.fix_type.value in type_labels:
            labels.append(type_labels[suggestion.fix_type.value])

        return labels

    async def update_mr_status(
        self,
        project_id: int,
        mr_iid: int,
        status: MRStatus,
        comment: Optional[str] = None,
    ) -> bool:
        """
        更新MR状态

        Args:
            project_id: GitLab项目ID
            mr_iid: MR IID
            status: 新状态
            comment: 可选评论

        Returns:
            是否成功
        """
        logger.info(
            "updating_mr_status",
            project_id=project_id,
            mr_iid=mr_iid,
            status=status.value,
        )

        try:
            # 添加评论
            if comment:
                url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"

                response = requests.post(
                    url,
                    json={"body": comment},
                    headers=self.headers,
                    timeout=30,
                )

                if response.status_code != 201:
                    logger.warning(
                        "comment_add_failed",
                        status_code=response.status_code,
                    )

            # 如果需要关闭MR
            if status in [MRStatus.MERGED, MRStatus.CLOSED]:
                url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"

                state_event = "merge" if status == MRStatus.MERGED else "close"

                response = requests.put(
                    url,
                    json={"state_event": state_event},
                    headers=self.headers,
                    timeout=30,
                )

                if response.status_code == 200:
                    logger.info("mr_status_updated", status=status.value)
                    return True
                else:
                    logger.error(
                        "mr_status_update_failed",
                        status_code=response.status_code,
                    )
                    return False

            return True

        except Exception as e:
            logger.error(
                "mr_status_update_exception",
                error=str(e),
                exc_info=True,
            )
            return False

    async def get_mr_status(
        self,
        project_id: int,
        mr_iid: int,
    ) -> Optional[Dict]:
        """
        获取MR状态

        Args:
            project_id: GitLab项目ID
            mr_iid: MR IID

        Returns:
            MR信息字典
        """
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"

            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    "get_mr_status_failed",
                    status_code=response.status_code,
                )
                return None

        except Exception as e:
            logger.error(
                "get_mr_status_exception",
                error=str(e),
                exc_info=True,
            )
            return None


# 全局单例（需要配置）
_mr_automator: Optional[GitLabMRAutomator] = None


def get_mr_automator() -> Optional[GitLabMRAutomator]:
    """获取MR自动化器实例"""
    return _mr_automator


def initialize_mr_automator(gitlab_url: str, gitlab_token: str) -> None:
    """初始化MR自动化器"""
    global _mr_automator
    _mr_automator = GitLabMRAutomator(gitlab_url, gitlab_token)
    logger.info("mr_automator_initialized", gitlab_url=gitlab_url)
