"""
测试注册中心

管理项目中的所有测试用例，支持测试元数据、标签、优先级等。
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .base import TestSuite, TestCase, TestStatus
from ....core.logging.logger import get_logger

logger = get_logger(__name__)


class TestPriority(str, Enum):
    """测试优先级"""
    CRITICAL = "critical"  # 关键测试，必须通过
    HIGH = "high"  # 高优先级
    MEDIUM = "medium"  # 中等优先级
    LOW = "low"  # 低优先级


@dataclass
class TestMetadata:
    """测试元数据"""
    test_id: str  # 唯一ID
    name: str  # 测试名称
    suite: str  # 测试套件
    file: str  # 文件路径
    line: int  # 行号

    # 执行信息
    last_status: TestStatus = TestStatus.PENDING
    last_run: Optional[datetime] = None
    avg_duration_ms: float = 0  # 平均执行时间（毫秒）

    # 优先级和标签
    priority: TestPriority = TestPriority.MEDIUM
    tags: List[str] = field(default_factory=list)

    # 依赖关系
    depends_on: List[str] = field(default_factory=list)  # 依赖的测试ID列表

    # 统计信息
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    flaky_count: int = 0  # 不稳定次数（成功后又失败）

    # 覆盖率信息
    source_files: List[str] = field(default_factory=list)  # 覆盖的源文件

    def __post_init__(self):
        """生成测试ID"""
        if not self.test_id:
            # 基于套件名和测试名生成唯一ID
            unique_str = f"{self.suite}:{self.name}"
            hash_obj = hashlib.md5(unique_str.encode())
            self.test_id = f"test_{hash_obj.hexdigest()[:12]}"

    @property
    def pass_rate(self) -> float:
        """通过率"""
        if self.total_runs == 0:
            return 0.0
        return (self.passed_runs / self.total_runs) * 100

    @property
    def is_flaky(self) -> bool:
        """是否是不稳定测试"""
        return self.flaky_count >= 3

    @property
    def is_slow(self) -> bool:
        """是否是慢速测试（>1秒）"""
        return self.avg_duration_ms > 1000


class TestRegistry:
    """
    测试注册中心

    管理项目中的所有测试用例及其元数据。
    """

    def __init__(self, project_id: int, storage_path: Optional[str] = None):
        """
        初始化测试注册中心

        Args:
            project_id: 项目ID
            storage_path: 存储路径（可选）
        """
        self.project_id = project_id
        self.storage_path = storage_path or f"/tmp/ai-cicd/test_registry/{project_id}"
        self.metadata_file = Path(self.storage_path) / "metadata.json"

        # 测试元数据：test_id -> TestMetadata
        self.tests: Dict[str, TestMetadata] = {}

        # 索引
        self._by_suite: Dict[str, Set[str]] = {}  # suite -> test_ids
        self._by_tag: Dict[str, Set[str]] = {}  # tag -> test_ids
        self._by_priority: Dict[TestPriority, Set[str]] = {
            priority: set() for priority in TestPriority
        }
        self._by_source: Dict[str, Set[str]] = {}  # source_file -> test_ids

        # 加载已有数据
        self._load()

    def register_test(self, test: TestCase, metadata: Optional[Dict] = None) -> TestMetadata:
        """
        注册测试用例

        Args:
            test: 测试用例
            metadata: 额外的元数据

        Returns:
            测试元数据
        """
        # 创建测试元数据
        test_meta = TestMetadata(
            test_id="",  # 会在__post_init__中生成
            name=test.name,
            suite=test.suite,
            file=test.file,
            line=test.line,
            tags=test.tags,
        )

        # 应用额外的元数据
        if metadata:
            if "priority" in metadata:
                test_meta.priority = TestPriority(metadata["priority"])
            if "source_files" in metadata:
                test_meta.source_files = metadata["source_files"]
            if "depends_on" in metadata:
                test_meta.depends_on = metadata["depends_on"]

        # 检查是否已存在
        existing = self.tests.get(test_meta.test_id)
        if existing:
            # 保留统计信息，更新其他字段
            test_meta.total_runs = existing.total_runs
            test_meta.passed_runs = existing.passed_runs
            test_meta.failed_runs = existing.failed_runs
            test_meta.flaky_count = existing.flaky_count
            test_meta.avg_duration_ms = existing.avg_duration_ms
            test_meta.last_run = existing.last_run
            test_meta.last_status = existing.last_status

        # 注册
        self.tests[test_meta.test_id] = test_meta
        self._update_indexes(test_meta)

        # 持久化
        self._save()

        logger.debug(
            "test_registered",
            test_id=test_meta.test_id,
            test_name=test_meta.name,
            suite=test_meta.suite,
        )

        return test_meta

    def register_suite(self, suite: TestSuite, metadata: Optional[Dict] = None) -> List[TestMetadata]:
        """
        注册测试套件

        Args:
            suite: 测试套件
            metadata: 额外的元数据

        Returns:
            测试元数据列表
        """
        test_metas = []

        for test in suite.tests:
            # 合并元数据
            test_metadata = (metadata or {}).copy()
            if suite.name:
                test_metadata["suite"] = suite.name

            test_meta = self.register_test(test, test_metadata)
            test_metas.append(test_meta)

        logger.info(
            "test_suite_registered",
            suite_name=suite.name,
            test_count=len(test_metas),
        )

        return test_metas

    def get_test(self, test_id: str) -> Optional[TestMetadata]:
        """获取测试元数据"""
        return self.tests.get(test_id)

    def get_tests_by_suite(self, suite_name: str) -> List[TestMetadata]:
        """获取套件中的所有测试"""
        test_ids = self._by_suite.get(suite_name, set())
        return [self.tests[tid] for tid in test_ids if tid in self.tests]

    def get_tests_by_tag(self, tag: str) -> List[TestMetadata]:
        """获取带有指定标签的所有测试"""
        test_ids = self._by_tag.get(tag, set())
        return [self.tests[tid] for tid in test_ids if tid in self.tests]

    def get_tests_by_priority(self, priority: TestPriority) -> List[TestMetadata]:
        """获取指定优先级的所有测试"""
        test_ids = self._by_priority.get(priority, set())
        return [self.tests[tid] for tid in test_ids if tid in self.tests]

    def get_tests_by_source(self, source_file: str) -> List[TestMetadata]:
        """获取覆盖指定源文件的所有测试"""
        source_file = str(source_file)  # 标准化路径
        test_ids = self._by_source.get(source_file, set())
        return [self.tests[tid] for tid in test_ids if tid in self.tests]

    def get_all_tests(self) -> List[TestMetadata]:
        """获取所有测试"""
        return list(self.tests.values())

    def update_test_result(
        self,
        test_id: str,
        status: TestStatus,
        duration_ms: float,
        timestamp: Optional[datetime] = None,
    ):
        """
        更新测试结果

        Args:
            test_id: 测试ID
            status: 测试状态
            duration_ms: 执行时间（毫秒）
            timestamp: 时间戳
        """
        test = self.tests.get(test_id)
        if not test:
            logger.warning("test_not_found_for_update", test_id=test_id)
            return

        timestamp = timestamp or datetime.now()

        # 更新统计信息
        test.total_runs += 1
        test.last_run = timestamp
        test.last_status = status

        if status == TestStatus.PASSED:
            test.passed_runs += 1
            # 检查是否从失败变为成功（不稳定）
            if test.last_status == TestStatus.FAILED:
                test.flaky_count += 1
        elif status == TestStatus.FAILED:
            test.failed_runs += 1

        # 更新平均执行时间（移动平均）
        if test.avg_duration_ms == 0:
            test.avg_duration_ms = duration_ms
        else:
            # 使用EMA（指数移动平均），alpha=0.2
            alpha = 0.2
            test.avg_duration_ms = alpha * duration_ms + (1 - alpha) * test.avg_duration_ms

        # 持久化
        self._save()

        logger.debug(
            "test_result_updated",
            test_id=test_id,
            status=status.value,
            duration_ms=duration_ms,
            pass_rate=test.pass_rate,
        )

    def get_statistics(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        total_tests = len(self.tests)
        if total_tests == 0:
            return {
                "total_tests": 0,
                "by_priority": {},
                "by_status": {},
                "flaky_tests": 0,
                "slow_tests": 0,
                "avg_pass_rate": 0.0,
            }

        # 按优先级统计
        by_priority = {
            priority.value: len(self._by_priority[priority])
            for priority in TestPriority
        }

        # 按状态统计
        by_status = {}
        for test in self.tests.values():
            status = test.last_status.value
            by_status[status] = by_status.get(status, 0) + 1

        # 不稳定测试
        flaky_tests = sum(1 for test in self.tests.values() if test.is_flaky)

        # 慢速测试
        slow_tests = sum(1 for test in self.tests.values() if test.is_slow)

        # 平均通过率
        avg_pass_rate = sum(test.pass_rate for test in self.tests.values()) / total_tests

        return {
            "total_tests": total_tests,
            "by_priority": by_priority,
            "by_status": by_status,
            "flaky_tests": flaky_tests,
            "slow_tests": slow_tests,
            "avg_pass_rate": round(avg_pass_rate, 2),
        }

    def find_tests_to_run(
        self,
        changed_files: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[TestPriority] = None,
        exclude_tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[TestMetadata]:
        """
        查找需要运行的测试

        Args:
            changed_files: 变更的源文件列表（用于影响分析）
            tags: 标签过滤
            priority: 优先级过滤
            exclude_tags: 排除的标签
            limit: 最多返回数量

        Returns:
            测试元数据列表
        """
        tests = set(self.tests.values())

        # 按变更文件过滤
        if changed_files:
            affected = set()
            for file in changed_files:
                affected.update(self.get_tests_by_source(file))
            tests = tests.intersection(affected)

        # 按标签过滤
        if tags:
            tagged = set()
            for tag in tags:
                tagged.update(self.get_tests_by_tag(tag))
            tests = tests.intersection(tagged)

        # 排除标签
        if exclude_tags:
            for tag in exclude_tags:
                tests.difference_update(self.get_tests_by_tag(tag))

        # 按优先级过滤
        if priority:
            tests = tests.intersection(self.get_tests_by_priority(priority))

        # 排序：按优先级和平均执行时间
        priority_order = {
            TestPriority.CRITICAL: 0,
            TestPriority.HIGH: 1,
            TestPriority.MEDIUM: 2,
            TestPriority.LOW: 3,
        }

        tests = sorted(
            tests,
            key=lambda t: (priority_order[t.priority], t.avg_duration_ms),
        )

        # 限制数量
        if limit:
            tests = list(tests)[:limit]

        return list(tests)

    def _update_indexes(self, test: TestMetadata):
        """更新索引"""
        # 套件索引
        if test.suite not in self._by_suite:
            self._by_suite[test.suite] = set()
        self._by_suite[test.suite].add(test.test_id)

        # 标签索引
        for tag in test.tags:
            if tag not in self._by_tag:
                self._by_tag[tag] = set()
            self._by_tag[tag].add(test.test_id)

        # 优先级索引
        self._by_priority[test.priority].add(test.test_id)

        # 源文件索引
        for source_file in test.source_files:
            if source_file not in self._by_source:
                self._by_source[source_file] = set()
            self._by_source[source_file].add(test.test_id)

    def _load(self):
        """从文件加载数据"""
        if not self.metadata_file.exists():
            logger.debug("registry_file_not_found", path=self.metadata_file)
            return

        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)

            for test_data in data.get("tests", []):
                test = TestMetadata(**test_data)
                self.tests[test.test_id] = test
                self._update_indexes(test)

            logger.info(
                "registry_loaded",
                test_count=len(self.tests),
                path=self.metadata_file,
            )

        except Exception as e:
            logger.error(
                "registry_load_failed",
                path=self.metadata_file,
                error=str(e),
            )

    def _save(self):
        """保存数据到文件"""
        try:
            # 创建目录
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

            # 准备数据
            data = {
                "project_id": self.project_id,
                "updated_at": datetime.now().isoformat(),
                "tests": [
                    {**asdict(test), "last_run": test.last_run.isoformat() if test.last_run else None}
                    for test in self.tests.values()
                ],
            }

            # 写入文件
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(
                "registry_saved",
                test_count=len(self.tests),
                path=self.metadata_file,
            )

        except Exception as e:
            logger.error(
                "registry_save_failed",
                path=self.metadata_file,
                error=str(e),
            )

    def clear(self):
        """清空注册中心"""
        self.tests.clear()
        self._by_suite.clear()
        self._by_tag.clear()
        self._by_source.clear()
        for priority in TestPriority:
            self._by_priority[priority].clear()

        # 删除文件
        if self.metadata_file.exists():
            self.metadata_file.unlink()

        logger.info("registry_cleared", project_id=self.project_id)


class TestRegistryManager:
    """
    测试注册中心管理器

    管理多个项目的测试注册中心。
    """

    def __init__(self):
        self.registries: Dict[int, TestRegistry] = {}

    def get_registry(self, project_id: int, create: bool = True) -> Optional[TestRegistry]:
        """
        获取项目的测试注册中心

        Args:
            project_id: 项目ID
            create: 如果不存在是否创建

        Returns:
            测试注册中心或None
        """
        if project_id not in self.registries:
            if not create:
                return None
            self.registries[project_id] = TestRegistry(project_id)

        return self.registries[project_id]

    def remove_registry(self, project_id: int):
        """移除项目的测试注册中心"""
        if project_id in self.registries:
            registry = self.registries[project_id]
            registry.clear()
            del self.registries[project_id]

            logger.info("registry_removed", project_id=project_id)


# 全局单例
test_registry_manager = TestRegistryManager()
