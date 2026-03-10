"""
测试执行器基类

定义所有测试执行器的通用接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class TestStatus(str, Enum):
    """测试状态"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class TestCase:
    """测试用例"""
    name: str
    suite: str
    file: str
    line: int
    
    # 执行信息
    status: TestStatus = TestStatus.PENDING
    duration_ms: float = 0
    output: str = ""
    error_message: str = ""
    
    # 标记
    is_flaky: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """测试套件"""
    name: str
    tests: List[TestCase] = field(default_factory=list)
    
    # 统计
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    
    def calculate_stats(self):
        """计算统计数据"""
        self.total = len(self.tests)
        self.passed = sum(1 for t in self.tests if t.status == TestStatus.PASSED)
        self.failed = sum(1 for t in self.tests if t.status == TestStatus.FAILED)
        self.skipped = sum(1 for t in self.tests if t.status == TestStatus.SKIPPED)


@dataclass
class TestConfig:
    """测试配置"""
    project_id: int
    pipeline_id: int
    job_id: int
    
    # 构建目录
    build_dir: str
    source_dir: str
    
    # 测试选项
    test_filter: Optional[str] = None  # 测试过滤（例如：只运行匹配的测试）
    parallel_jobs: int = 4
    timeout: int = 300  # 单个测试超时时间（秒）
    
    # 覆盖率选项
    enable_coverage: bool = True
    coverage_format: str = "xml"  # xml, html, json
    
    # 环境变量
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class TestResult:
    """测试结果"""
    status: TestStatus
    
    # 测试套件
    suites: List[TestSuite]
    
    # 统计
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    
    # 覆盖率
    coverage_percent: Optional[float] = None
    coverage_lines: Optional[int] = None
    coverage_lines_covered: Optional[int] = None
    
    # 时间
    duration_seconds: float = 0
    
    # 输出
    stdout: str = ""
    stderr: str = ""
    
    # 元数据
    started_at: datetime = None
    finished_at: datetime = None
    
    # 失败的测试
    failed_test_cases: List[TestCase] = field(default_factory=list)


class BaseTestExecutor(ABC):
    """测试执行器基类"""
    
    def __init__(self):
        self.config: Optional[TestConfig] = None
        self.status: TestStatus = TestStatus.PENDING
    
    @abstractmethod
    async def discover(self) -> List[TestSuite]:
        """
        发现测试用例
        
        Returns:
            测试套件列表
        """
        pass
    
    @abstractmethod
    async def run(self, config: TestConfig) -> TestResult:
        """
        运行测试
        
        Args:
            config: 测试配置
            
        Returns:
            测试结果
        """
        pass
    
    @abstractmethod
    def get_test_type(self) -> str:
        """
        获取测试类型
        
        Returns:
            测试类型（qttest, googletest等）
        """
        pass
    
    def parse_test_output(self, output: str) -> List[TestSuite]:
        """
        解析测试输出
        
        Args:
            output: 测试输出
            
        Returns:
            测试套件列表
        """
        # 子类实现
        return []
