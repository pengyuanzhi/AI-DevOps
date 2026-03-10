"""配置管理模块"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # LLM 配置
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-3-5-sonnet-20241022", env="CLAUDE_MODEL")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    zhipu_api_key: Optional[str] = Field(default=None, env="ZHIPU_API_KEY")
    zhipu_model: str = Field(default="glm-4-plus", env="ZHIPU_MODEL")

    # 默认 LLM 提供商（claude, openai, zhipu）
    default_llm_provider: str = Field(default="zhipu", env="DEFAULT_LLM_PROVIDER")

    # GitLab 配置
    gitlab_url: str = Field(default="https://gitlab.com", env="GITLAB_URL")
    gitlab_token: str = Field(..., env="GITLAB_TOKEN")
    gitlab_webhook_secret: str = Field(..., env="GITLAB_WEBHOOK_SECRET")

    # 服务配置
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    workers: int = Field(default=4, env="WORKERS")

    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")

    # 环境配置
    environment: str = Field(default="development", env="ENVIRONMENT")

    # 缓存配置
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")

    # 数据库配置
    database_url: str = Field(default="sqlite:///./data/ai_cicd.db", env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    db_echo: bool = Field(default=False, env="DB_ECHO")

    # Redis 配置
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")

    # RabbitMQ 配置
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", env="RABBITMQ_URL")
    rabbitmq_exchange: str = Field(default="ai_cicd", env="RABBITMQ_EXCHANGE")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")

    # 限流配置
    max_requests_per_minute: int = Field(default=60, env="MAX_REQUESTS_PER_MINUTE")
    max_concurrent_reviews: int = Field(default=5, env="MAX_CONCURRENT_REVIEWS")

    # 成本控制
    daily_token_budget: int = Field(default=1000000, env="DAILY_TOKEN_BUDGET")
    enable_cost_tracking: bool = Field(default=True, env="ENABLE_COST_TRACKING")

    # 功能开关
    enable_test_generation: bool = Field(default=True, env="ENABLE_TEST_GENERATION")
    enable_code_review: bool = Field(default=True, env="ENABLE_CODE_REVIEW")
    enable_pipeline_generation: bool = Field(default=False, env="ENABLE_PIPELINE_GENERATION")

    # 调试模式
    debug: bool = Field(default=False, env="DEBUG")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def project_root(self) -> Path:
        """项目根目录"""
        return Path(__file__).parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """数据目录"""
        return self.project_root / "data"

    @property
    def cache_dir(self) -> Path:
        """缓存目录"""
        return self.data_dir / "cache"

    @property
    def generated_tests_dir(self) -> Path:
        """生成的测试目录"""
        return self.data_dir / "generated" / "tests"

    @property
    def prompts_dir(self) -> Path:
        """Prompt 模板目录"""
        return self.project_root / "prompts"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例

    使用 lru_cache 确保配置只加载一次
    """
    return Settings()


# 导出配置实例
settings = get_settings()
