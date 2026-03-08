"""结构化日志配置"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """
    配置结构化日志

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 日志格式 (json, console)
    """
    # 设置日志级别
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 配置处理器链
    processors: list[Processor] = [
        # 添加日志名称
        structlog.stdlib.add_logger_name,
        # 添加日志级别
        structlog.stdlib.add_log_level,
        # 添加时间戳
        structlog.processors.TimeStamper(fmt="iso"),
        # 添加调用位置
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
        # 处理异常信息
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # 根据格式选择输出处理器
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        # 控制台格式，带颜色
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    # 配置 structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # 配置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    获取 logger 实例

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        配置好的 logger 实例
    """
    return structlog.get_logger(name)


class LoggerMixin:
    """Logger 混入类，为类提供 logger 属性"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """获取该类的 logger"""
        return get_logger(self.__class__.__name__)


def filter_secrets(event_dict: EventDict) -> EventDict:
    """
    过滤日志中的敏感信息

    Args:
        event_dict: 日志事件字典

    Returns:
        过滤后的日志事件字典
    """
    # 敏感字段列表
    sensitive_keys = [
        "password",
        "token",
        "api_key",
        "secret",
        "authorization",
        "credential",
    ]

    # 递归过滤字典中的敏感信息
    def filter_dict(d: Any) -> Any:
        if isinstance(d, dict):
            return {
                k: "***" if any(sk in k.lower() for sk in sensitive_keys) else filter_dict(v)
                for k, v in d.items()
            }
        elif isinstance(d, list):
            return [filter_dict(item) for item in d]
        return d

    # 过滤事件字典
    if "event" in event_dict:
        event_dict = filter_dict(event_dict)

    return event_dict
