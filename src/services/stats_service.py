"""
统计服务 - 收集和聚合统计数据

从日志文件解析统计信息，提供测试、审查、MR、LLM 等统计数据。
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from collections import defaultdict
import threading
import time

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StatsService:
    """统计服务 - 提供统计数据和缓存"""

    def __init__(self, cache_ttl: int = 5):
        """
        初始化统计服务

        Args:
            cache_ttl: 缓存生存时间（秒），默认5秒
        """
        self.cache_ttl = cache_ttl
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[float] = None
        self._lock = threading.Lock()

        # 统计数据（模拟数据，生产环境应从数据库或日志文件读取）
        self._stats = {
            "tests": {
                "generated": 1250,
                "executed": 980,
                "passed": 892,
                "pass_rate": 91.0,
                "coverage": 78.5
            },
            "reviews": {
                "total": 450,
                "avg_score": 8.2,
                "issues_found": 1250
            },
            "merge_requests": {
                "processed": 380,
                "pending": 12,
                "avg_process_time": 450
            },
            "llm": {
                "total_tokens": 1250000,
                "api_calls": 1250,
                "estimated_cost": 12.50
            }
        }

        logger.info(
            "stats_service_initialized",
            cache_ttl=cache_ttl
        )

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cache is None or self._cache_time is None:
            return False
        return time.time() - self._cache_time < self.cache_ttl

    def _update_cache(self):
        """更新缓存"""
        with self._lock:
            self._cache = self._collect_stats()
            self._cache_time = time.time()
            logger.debug("cache_updated", stats_keys=list(self._cache.keys()))

    def _collect_stats(self) -> Dict[str, Any]:
        """
        收集统计数据

        生产环境应该从以下数据源收集：
        1. 数据库（PostgreSQL）- 查询历史记录
        2. 日志文件 - 解析 structlog JSON 日志
        3. 内存缓存 - 实时统计

        Returns:
            统计数据字典
        """
        # TODO: 生产环境应该从实际数据源收集
        # 这里使用模拟数据进行演示

        return {
            "success": True,
            "data": {
                "tests": self._stats["tests"].copy(),
                "reviews": self._stats["reviews"].copy(),
                "merge_requests": self._stats["merge_requests"].copy(),
                "llm": self._stats["llm"].copy(),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取统计数据（带缓存）

        Returns:
            统计数据字典
        """
        if not self._is_cache_valid():
            self._update_cache()

        return self._cache

    def increment_stat(self, category: str, key: str, value: int = 1):
        """
        增加统计数据

        Args:
            category: 统计类别（tests, reviews, merge_requests, llm）
            key: 统计键
            value: 增加值
        """
        if category in self._stats and key in self._stats[category]:
            self._stats[category][key] += value
            logger.debug(
                "stat_incremented",
                category=category,
                key=key,
                value=value,
                new_value=self._stats[category][key]
            )
        else:
            logger.warning(
                "invalid_stat_key",
                category=category,
                key=key,
                available_keys=list(self._stats.get(category, {}).keys())
            )

    def update_stat(self, category: str, key: str, value: Any):
        """
        更新统计数据

        Args:
            category: 统计类别
            key: 统计键
            value: 新值
        """
        if category in self._stats and key in self._stats[category]:
            old_value = self._stats[category][key]
            self._stats[category][key] = value
            logger.debug(
                "stat_updated",
                category=category,
                key=key,
                old_value=old_value,
                new_value=value
            )
        else:
            logger.warning(
                "invalid_stat_key",
                category=category,
                key=key
            )

    def get_trends(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取趋势数据

        Args:
            hours: 获取最近几小时的数据

        Returns:
            趋势数据字典
        """
        # TODO: 生产环境应该从数据库查询历史数据
        # 这里返回模拟的趋势数据
        now = datetime.utcnow()
        trends = []

        for i in range(hours):
            timestamp = now - timedelta(hours=hours - i)
            trends.append({
                "timestamp": timestamp.isoformat() + "Z",
                "tests_generated": 50 + i * 2,
                "reviews_completed": 20 + i,
                "mr_processed": 15 + i
            })

        return {
            "success": True,
            "data": {
                "trends": trends,
                "period_hours": hours
            }
        }


# 全局单例
_stats_service: Optional[StatsService] = None


def get_stats_service() -> StatsService:
    """获取统计服务单例"""
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService()
    return _stats_service
