"""
智能测试选择服务

分析代码变更，智能选择需要运行的测试
"""

from typing import List, Set, Optional, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

from .git_analyzer import GitAnalyzer, FileChange, ChangeType
from .dependency_graph import DependencyGraphBuilder, DependencyGraph
from ....services.test.base import TestSuite, TestCase
from ....utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestSelectionResult:
    """测试选择结果"""
    selected_tests: List[TestCase]
    skipped_tests: List[TestCase]
    
    # 影响域分析
    affected_files: Set[str]
    affected_functions: Set[str]
    
    # 原因
    reasons: Dict[str, str]  # test_name -> reason
    
    # 统计
    total_tests: int
    selected_count: int
    skip_count: int
    estimated_time_saved_percent: float
    
    # 置信度
    confidence: float  # 0.0 - 1.0


class TestSelectionService:
    """智能测试选择服务"""
    
    def __init__(self):
        self.git_analyzer = GitAnalyzer()
        self.graph_builder = DependencyGraphBuilder()
        self.dependency_graph: Optional[DependencyGraph] = None
    
    async def select_tests_for_mr(
        self,
        repo_path: str,
        source_branch: str,
        target_branch: str,
        all_tests: List[TestSuite],
        dependency_graph: Optional[DependencyGraph] = None,
        conservative: bool = False,
    ) -> TestSelectionResult:
        """
        为MR选择测试
        
        Args:
            repo_path: 仓库路径
            source_branch: 源分支
            target_branch: 目标分支
            all_tests: 所有可用的测试套件
            dependency_graph: 预构建的依赖图
            conservative: 是否使用保守模式（选择更多测试）
            
        Returns:
            测试选择结果
        """
        logger.info(
            "test_selection_started",
            repo_path=repo_path,
            source_branch=source_branch,
            target_branch=target_branch,
            total_tests=sum(len(s.tests) for s in all_tests),
        )
        
        # 分析MR变更
        file_changes = self.git_analyzer.analyze_mr_changes(
            repo_path,
            source_branch,
            target_branch,
        )
        
        if not file_changes:
            # 没有代码变更，返回空结果
            return self._create_empty_result(all_tests)
        
        # 构建或使用依赖图
        if dependency_graph:
            self.dependency_graph = dependency_graph
        else:
            self.dependency_graph = self.graph_builder.build_from_source(repo_path)
        
        # 分析影响域
        affected_files, affected_functions = self._analyze_impact(
            file_changes,
            conservative,
        )
        
        # 选择测试
        selected_tests = []
        skipped_tests = []
        reasons = {}
        
        all_test_cases = []
        for suite in all_tests:
            all_test_cases.extend(suite.tests)
        
        for test in all_test_cases:
            should_run, reason = self._should_run_test(
                test,
                file_changes,
                affected_files,
                affected_functions,
                conservative,
            )
            
            if should_run:
                selected_tests.append(test)
                reasons[test.name] = reason
            else:
                skipped_tests.append(test)
        
        # 计算统计信息
        total_tests = len(all_test_cases)
        selected_count = len(selected_tests)
        skip_count = len(skipped_tests)
        estimated_time_saved = (skip_count / total_tests * 100) if total_tests > 0 else 0
        
        # 计算置信度
        confidence = self._calculate_confidence(
            file_changes,
            affected_files,
            selected_count,
        )
        
        logger.info(
            "test_selection_completed",
            total_tests=total_tests,
            selected_count=selected_count,
            skip_count=skip_count,
            time_saved_percent=estimated_time_saved,
            confidence=confidence,
        )
        
        return TestSelectionResult(
            selected_tests=selected_tests,
            skipped_tests=skipped_tests,
            affected_files=affected_files,
            affected_functions=affected_functions,
            reasons=reasons,
            total_tests=total_tests,
            selected_count=selected_count,
            skip_count=skip_count,
            estimated_time_saved_percent=estimated_time_saved,
            confidence=confidence,
        )
    
    def _analyze_impact(
        self,
        file_changes: List[FileChange],
        conservative: bool,
    ) -> Tuple[Set[str], Set[str]]:
        """
        分析变更的影响域
        
        Args:
            file_changes: 文件变更列表
            conservative: 是否保守模式
            
        Returns:
            (受影响的文件集合, 受影响的函数集合)
        """
        affected_files = set()
        affected_functions = set()
        
        for file_change in file_changes:
            # 直接变更的文件
            affected_files.add(file_change.path)
            
            # 函数级变更
            if file_change.modified_functions:
                affected_functions.update(file_change.modified_functions)
            if file_change.added_functions:
                affected_functions.update(file_change.added_functions)
            if file_change.deleted_functions:
                affected_functions.update(file_change.deleted_functions)
        
        # 使用依赖图分析下游影响
        if self.dependency_graph:
            for file_path in affected_files:
                file_id = f"file:{file_path}"
                
                # 获取下游依赖（依赖此文件的文件）
                downstream = self.dependency_graph.get_downstream(
                    file_id,
                    max_depth=3 if conservative else 2,
                )
                
                for dep_id in downstream:
                    if dep_id.startswith("file:"):
                        affected_files.add(dep_id.replace("file:", ""))
                    elif dep_id.startswith("function:"):
                        # 提取函数名
                        parts = dep_id.split(":")
                        if len(parts) >= 3:
                            affected_functions.add(parts[2])
        
        return affected_files, affected_functions
    
    def _should_run_test(
        self,
        test: TestCase,
        file_changes: List[FileChange],
        affected_files: Set[str],
        affected_functions: Set[str],
        conservative: bool,
    ) -> Tuple[bool, str]:
        """
        判断是否应该运行测试
        
        Args:
            test: 测试用例
            file_changes: 文件变更列表
            affected_files: 受影响的文件集合
            affected_functions: 受影响的函数集合
            conservative: 是否保守模式
            
        Returns:
            (是否运行, 原因)
        """
        # 规则1: 测试文件本身被修改 -> 运行
        for file_change in file_changes:
            if "test" in file_change.path.lower():
                if test.name in file_change.path or test.suite in file_change.path:
                    return True, "测试文件被修改"
        
        # 规则2: 测试名称与受影响的函数匹配 -> 运行
        for func in affected_functions:
            if func.lower() in test.name.lower():
                return True, f"测试函数与变更函数匹配: {func}"
        
        # 规则3: 测试套件名称与受影响的文件匹配 -> 运行
        for file_path in affected_files:
            file_name = Path(file_path).stem
            if file_name.lower() in test.suite.lower():
                return True, f"测试套件与变更文件匹配: {file_name}"
        
        # 规则4: 保守模式下，运行更多测试
        if conservative:
            # 如果任何相关头文件被修改，运行相关测试
            for file_path in affected_files:
                if file_path.endswith(".h") or file_path.endswith(".hpp"):
                    # 检查测试是否可能与这个头文件相关
                    if self._is_test_related_to_header(test, file_path):
                        return True, f"保守模式: 头文件变更 {file_path}"
        
        # 默认: 跳过
        return False, "未检测到与变更的相关性"
    
    def _is_test_related_to_header(self, test: TestCase, header_path: str) -> bool:
        """
        判断测试是否与头文件相关
        
        Args:
            test: 测试用例
            header_path: 头文件路径
            
        Returns:
            是否相关
        """
        header_name = Path(header_path).stem.lower()
        test_name = test.name.lower()
        suite_name = test.suite.lower()
        
        # 简单的名称匹配
        return header_name in test_name or header_name in suite_name
    
    def _calculate_confidence(
        self,
        file_changes: List[FileChange],
        affected_files: Set[str],
        selected_count: int,
    ) -> float:
        """
        计算选择置信度
        
        Args:
            file_changes: 文件变更
            affected_files: 受影响的文件
            selected_count: 选择的测试数量
            
        Returns:
            置信度 (0.0 - 1.0)
        """
        confidence = 0.5  # 基础置信度
        
        # 变更文件越少，置信度越高
        if len(file_changes) <= 5:
            confidence += 0.2
        elif len(file_changes) <= 10:
            confidence += 0.1
        
        # 如果有依赖图，置信度增加
        if self.dependency_graph:
            confidence += 0.2
        
        # 影响域越明确，置信度越高
        if len(affected_files) < len(file_changes) * 3:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _create_empty_result(self, all_tests: List[TestSuite]) -> TestSelectionResult:
        """创建空结果（无变更时）"""
        all_test_cases = []
        for suite in all_tests:
            all_test_cases.extend(suite.tests)
        
        return TestSelectionResult(
            selected_tests=[],
            skipped_tests=all_test_cases,
            affected_files=set(),
            affected_functions=set(),
            reasons={},
            total_tests=len(all_test_cases),
            selected_count=0,
            skip_count=len(all_test_cases),
            estimated_time_saved_percent=100.0,
            confidence=1.0,
        )


# 全局单例
test_selection_service = TestSelectionService()
