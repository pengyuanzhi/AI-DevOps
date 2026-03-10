"""
变更关联分析器

分析代码变更与失败之间的关联关系
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import re

from ....utils.logger import get_logger
from ....services.ai.test_selection.git_analyzer import GitAnalyzer, FileChange

logger = get_logger(__name__)


@dataclass
class ChangeImpact:
    """变更影响"""
    file_path: str
    change_type: str  # "added", "modified", "deleted"
    lines_added: int = 0
    lines_deleted: int = 0
    functions_changed: Set[str] = field(default_factory=set)
    classes_changed: Set[str] = field(default_factory=set)


@dataclass
class ChangeFailureCorrelation:
    """变更-失败关联"""
    commit_hash: str
    file_path: str
    correlation_score: float  # 0-1

    # 关联证据
    error_in_changed_file: bool = False
    error_in_changed_function: bool = False
    similar_previous_failures: int = 0
    time_correlation: float = 0.0

    # 变更详情
    change_summary: str = ""
    changed_functions: List[str] = field(default_factory=list)


@dataclass
class ChangeCorrelationResult:
    """变更关联分析结果"""
    failure_timestamp: datetime
    total_commits: int
    total_changes: int

    # 高度相关的变更
    high_correlations: List[ChangeFailureCorrelation] = field(default_factory=list)
    medium_correlations: List[ChangeFailureCorrelation] = field(default_factory=list)
    low_correlations: List[ChangeFailureCorrelation] = field(default_factory=list)

    # 汇总
    suspected_commits: Set[str] = field(default_factory=set)
    suspected_files: Set[str] = field(default_factory=set)

    # 统计
    avg_correlation_score: float = 0.0

    def get_top_suspects(self, limit: int = 5) -> List[str]:
        """获取最可疑的提交"""
        suspects = sorted(
            self.high_correlations + self.medium_correlations,
            key=lambda x: x.correlation_score,
            reverse=True,
        )
        return [s.commit_hash for s in suspects[:limit]]


class ChangeCorrelator:
    """
    变更关联分析器

    分析代码变更与失败的关联关系
    """

    def __init__(self):
        self.git_analyzer = GitAnalyzer()

    async def correlate(
        self,
        repo_path: str,
        failure_timestamp: datetime,
        error_location: Optional[str],
        failure_log: str,
        lookback_hours: int = 24,
    ) -> ChangeCorrelationResult:
        """
        关联代码变更和失败

        Args:
            repo_path: 仓库路径
            failure_timestamp: 失败时间
            error_location: 错误位置（文件:行号）
            failure_log: 失败日志
            lookback_hours: 回溯时间（小时）

        Returns:
            关联分析结果
        """
        logger.info(
            "change_correlation_started",
            repo_path=repo_path,
            failure_timestamp=failure_timestamp,
            lookback_hours=lookback_hours,
        )

        # 获取时间窗口内的提交
        since_time = failure_timestamp - timedelta(hours=lookback_hours)
        commits = await self._get_commits_since(repo_path, since_time)

        if not commits:
            logger.info("no_commits_found", since=since_time)
            return ChangeCorrelationResult(
                failure_timestamp=failure_timestamp,
                total_commits=0,
                total_changes=0,
            )

        # 获取变更详情
        file_changes = await self._analyze_commit_changes(repo_path, commits)

        # 分析关联
        correlations = self._calculate_correlations(
            file_changes,
            error_location,
            failure_log,
            failure_timestamp,
        )

        # 分类关联
        high = [c for c in correlations if c.correlation_score >= 0.7]
        medium = [c for c in correlations if 0.4 <= c.correlation_score < 0.7]
        low = [c for c in correlations if c.correlation_score < 0.4]

        # 计算统计
        avg_score = (
            sum(c.correlation_score for c in correlations) / len(correlations)
            if correlations else 0.0
        )

        suspected_commits = {c.commit_hash for c in high + medium}
        suspected_files = {c.file_path for c in high + medium}

        result = ChangeCorrelationResult(
            failure_timestamp=failure_timestamp,
            total_commits=len(commits),
            total_changes=len(file_changes),
            high_correlations=high,
            medium_correlations=medium,
            low_correlations=low,
            suspected_commits=suspected_commits,
            suspected_files=suspected_files,
            avg_correlation_score=avg_score,
        )

        logger.info(
            "change_correlation_completed",
            total_changes=len(file_changes),
            high_correlations=len(high),
            medium_correlations=len(medium),
            avg_score=avg_score,
        )

        return result

    async def _get_commits_since(
        self,
        repo_path: str,
        since: datetime,
    ) -> List[Dict]:
        """获取指定时间之后的提交"""
        try:
            # 使用Git命令获取提交
            import subprocess
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
            cmd = [
                "git", "-C", repo_path, "log",
                f"--since={since_str}",
                "--pretty=format:%H|%an|%ai|%s",
                "--"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning("git_log_failed", error=result.stderr)
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            "hash": parts[0],
                            "author": parts[1],
                            "timestamp": parts[2],
                            "message": parts[3],
                        })

            logger.info("commits_retrieved", count=len(commits))
            return commits

        except Exception as e:
            logger.error(
                "get_commits_failed",
                error=str(e),
                exc_info=True,
            )
            return []

    async def _analyze_commit_changes(
        self,
        repo_path: str,
        commits: List[Dict],
    ) -> List[Dict]:
        """分析提交的变更"""
        all_changes = []

        for commit in commits:
            try:
                import subprocess
                cmd = [
                    "git", "-C", repo_path, "diff-tree",
                    "--no-commit-id", "--name-status", "-r", commit["hash"]
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    continue

                # 解析变更
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            status = parts[0]
                            file_path = parts[1]

                            all_changes.append({
                                "commit_hash": commit["hash"],
                                "file_path": file_path,
                                "change_type": status,
                                "commit_message": commit["message"],
                                "commit_timestamp": commit["timestamp"],
                            })

            except Exception as e:
                logger.warning(
                    "analyze_commit_failed",
                    commit_hash=commit["hash"],
                    error=str(e),
                )
                continue

        return all_changes

    def _calculate_correlations(
        self,
        file_changes: List[Dict],
        error_location: Optional[str],
        failure_log: str,
        failure_timestamp: datetime,
    ) -> List[ChangeFailureCorrelation]:
        """计算变更与失败的关联度"""
        correlations = []

        for change in file_changes:
            correlation = ChangeFailureCorrelation(
                commit_hash=change["commit_hash"],
                file_path=change["file_path"],
                correlation_score=0.0,
                change_summary=f"{change['change_type']}: {change['file_path']}",
            )

            # 1. 文件路径匹配
            if error_location:
                error_file = error_location.split(':')[0]
                if error_file in change["file_path"] or change["file_path"] in error_file:
                    correlation.error_in_changed_file = True
                    correlation.correlation_score += 0.4

            # 2. 日志中提到文件
            if change["file_path"] in failure_log:
                correlation.correlation_score += 0.2

            # 3. 变更类型权重
            change_type = change["change_type"]
            if change_type.startswith('M'):  # Modified
                correlation.correlation_score += 0.1
            elif change_type.startswith('A'):  # Added
                correlation.correlation_score += 0.15
            elif change_type.startswith('D'):  # Deleted
                correlation.correlation_score += 0.25  # 删除影响更大

            # 4. 提取变更的函数
            functions = self._extract_changed_functions(failure_log, change["file_path"])
            if functions:
                correlation.error_in_changed_function = True
                correlation.changed_functions = functions
                correlation.correlation_score += 0.2

            # 5. 时间相关性（越接近失败时间，相关性越高）
            try:
                commit_time = datetime.fromisoformat(change["commit_timestamp"].replace('+00:00', ''))
                time_diff = (failure_timestamp - commit_time).total_seconds()
                if time_diff < 3600:  # 1小时内
                    correlation.time_correlation = 0.15
                elif time_diff < 86400:  # 24小时内
                    correlation.time_correlation = 0.1
                else:
                    correlation.time_correlation = 0.05

                correlation.correlation_score += correlation.time_correlation
            except:
                pass

            # 限制范围
            correlation.correlation_score = min(correlation.correlation_score, 1.0)

            correlations.append(correlation)

        return correlations

    def _extract_changed_functions(
        self,
        failure_log: str,
        file_path: str,
    ) -> List[str]:
        """从失败日志中提取变更的函数"""
        functions = []

        # 尝试匹配常见的错误格式
        patterns = [
            rf"{re.escape(file_path)}:(\d+):(\d+):\s*error:",
            rf"in\s+(\w+)\s+at\s+{re.escape(file_path)}",
            rf"(\w+)\s+at\s+{re.escape(file_path)}:\d+",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, failure_log)
            if matches:
                # 提取函数名（简化处理）
                functions.extend([f"line_{m}" for m in matches[:3]])

        return list(set(functions))

    def find_similar_failures(
        self,
        failure_log: str,
        historical_failures: List[Dict],
        similarity_threshold: float = 0.6,
    ) -> List[Dict]:
        """
        查找类似的历史失败

        Args:
            failure_log: 当前失败日志
            historical_failures: 历史失败列表
            similarity_threshold: 相似度阈值

        Returns:
            相似的历史失败列表
        """
        similar_failures = []

        for historical in historical_failures:
            similarity = self._calculate_log_similarity(
                failure_log,
                historical.get("log", ""),
            )

            if similarity >= similarity_threshold:
                historical["similarity"] = similarity
                similar_failures.append(historical)

        # 按相似度排序
        similar_failures.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        logger.info(
            "similar_failures_found",
            count=len(similar_failures),
            threshold=similarity_threshold,
        )

        return similar_failures

    def _calculate_log_similarity(
        self,
        log1: str,
        log2: str,
    ) -> float:
        """计算日志相似度（简化版）"""
        if not log1 or not log2:
            return 0.0

        # 简化：使用关键词重叠
        words1 = set(re.findall(r'\w+', log1.lower()))
        words2 = set(re.findall(r'\w+', log2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0


# 全局单例
change_correlator = ChangeCorrelator()
