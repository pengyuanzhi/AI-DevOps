"""
消息队列模块

提供RabbitMQ消息队列功能。
"""

from .rabbitmq import (
    rabbitmq_client,
    message_queue_service,
    get_message_queue_service,
    MessageQueueService,
    RabbitMQClient,
)

__all__ = [
    "rabbitmq_client",
    "message_queue_service",
    "get_message_queue_service",
    "MessageQueueService",
    "RabbitMQClient",
]
