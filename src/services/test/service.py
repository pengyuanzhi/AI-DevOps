"""
测试服务

提供高级测试API，协调各种测试执行器
"""

from typing import Optional, List
from datetime import datetime

from .base import TestConfig, TestResult, TestStatus, BaseTestExecutor
from .qttest_executor import QtTestExecutor
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TestService:
    """测试服务"""
    
    def __init__(self):
        self.executors = {
            "qttest": QtTestExecutor(),
        }
        self.active_tests = {}
    
    def get_executor(self, test_type: str) -> BaseTestExecutor:
        """
        获取测试执行器
        
        Args:
            test_type: 测试类型
            
        Returns:
            测试执行器
        """
        executor = self.executors.get(test_type)
        if not executor:
            raise ValueError(f"Unsupported test type: {test_type}")
        return executor
    
    async def run_tests(
        self,
        config: TestConfig,
        test_type: str = "qttest",
    ) -> TestResult:
        """
        运行测试
        
        Args:
            config: 测试配置
            test_type: 测试类型
            
        Returns:
            测试结果
        """
        logger.info(
            "test_started",
            project_id=config.project_id,
            pipeline_id=config.pipeline_id,
            job_id=config.job_id,
            test_type=test_type,
        )
        
        # 获取执行器
        executor = self.get_executor(test_type)
        
        # 添加到活跃测试列表
        test_key = f"{config.project_id}-{config.pipeline_id}-{config.job_id}"
        self.active_tests[test_key] = {
            "config": config,
            "executor": executor,
            "started_at": datetime.now(),
        }
        
        try:
            # 运行测试
            result = await executor.run(config)
            
            logger.info(
                "test_completed",
                project_id=config.project_id,
                pipeline_id=config.pipeline_id,
                job_id=config.job_id,
                status=result.status.value,
                total_tests=result.total_tests,
                passed_tests=result.passed_tests,
                failed_tests=result.failed_tests,
                duration=result.duration_seconds,
            )
            
            return result
            
        finally:
            # 从活跃测试列表中移除
            if test_key in self.active_tests:
                del self.active_tests[test_key]
    
    async def discover_tests(
        self,
        config: TestConfig,
        test_type: str = "qttest",
    ):
        """
        发现测试用例
        
        Args:
            config: 测试配置
            test_type: 测试类型
            
        Returns:
            测试套件列表
        """
        executor = self.get_executor(test_type)
        executor.config = config
        
        return await executor.discover()
    
    async def get_test_status(
        self,
        project_id: int,
        pipeline_id: int,
        job_id: int,
    ) -> Optional[TestStatus]:
        """
        获取测试状态
        
        Args:
            project_id: 项目ID
            pipeline_id: 流水线ID
            job_id: 作业ID
            
        Returns:
            测试状态或None
        """
        test_key = f"{project_id}-{pipeline_id}-{job_id}"
        
        if test_key not in self.active_tests:
            return None
        
        return self.active_tests[test_key]["executor"].status


# 全局单例
test_service = TestService()
