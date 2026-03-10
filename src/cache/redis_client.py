"""
Redis缓存客户端

提供Redis缓存操作的封装，支持同步和异步操作。
"""

from functools import lru_cache
from typing import Optional, Any

import redis.asyncio as aioredis
import redis
import json

from ..utils.config import settings


class RedisClient:
    """Redis同步客户端（用于脚本等同步场景）"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            self._client = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                socket_timeout=settings.redis_socket_timeout,
                socket_connect_timeout=settings.redis_socket_connect_timeout,
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        client = self.get_client()
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> bool:
        """设置缓存"""
        client = self.get_client()
        return await client.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        """删除缓存"""
        client = self.get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        client = self.get_client()
        return await client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        client = self.get_client()
        return await client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        client = self.get_client()
        return await client.ttl(key)

    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()


class AsyncRedisClient:
    """Redis异步客户端"""

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        """获取Redis客户端"""
        if self._client is None:
            self._client = await aioredis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                socket_timeout=settings.redis_socket_timeout,
                socket_connect_timeout=settings.redis_socket_connect_timeout,
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        client = await self.get_client()
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> bool:
        """设置缓存"""
        client = await self.get_client()
        return await client.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        """删除缓存"""
        client = await self.get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        client = await self.get_client()
        return await client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        client = await self.get_client()
        return await client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        client = await self.get_client()
        return await client.ttl(key)

    async def mget(self, keys: list[str]) -> list[Optional[str]]:
        """批量获取"""
        client = await self.get_client()
        return await client.mget(keys)

    async def mset(self, mapping: dict[str, str]) -> bool:
        """批量设置"""
        client = await self.get_client()
        return await client.mset(mapping)

    async def incr(self, key: str, amount: int = 1) -> int:
        """递增"""
        client = await self.get_client()
        return await client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """递减"""
        client = await self.get_client()
        return await client.decrby(key, amount)

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()


class CacheService:
    """缓存服务，提供高级缓存功能"""

    def __init__(self):
        self.redis = AsyncRedisClient()

    async def get_json(self, key: str) -> Optional[Any]:
        """获取JSON对象"""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> bool:
        """设置JSON对象"""
        try:
            json_str = json.dumps(value)
            return await self.redis.set(key, json_str, ex=ex)
        except (TypeError, ValueError):
            return False

    async def get_or_set_json(
        self,
        key: str,
        factory: callable,
        ex: Optional[int] = None,
    ) -> Any:
        """获取或设置JSON对象（缓存穿透保护）"""
        value = await self.get_json(key)
        if value is not None:
            return value

        # 调用工厂函数获取数据
        value = await factory() if callable(factory) else factory
        if value is not None:
            await self.set_json(key, value, ex=ex)

        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """根据模式批量删除缓存"""
        client = await self.redis.get_client()
        keys = await client.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def close(self):
        """关闭连接"""
        await self.redis.close()


# 全局单例
@lru_cache()
def get_cache_service() -> CacheService:
    """获取缓存服务单例"""
    return CacheService()


# 导出
redis_client = RedisClient()
async_redis_client = AsyncRedisClient()
cache_service = get_cache_service()
