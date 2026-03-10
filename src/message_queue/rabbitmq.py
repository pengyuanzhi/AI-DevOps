"""
RabbitMQ消息队列客户端

提供RabbitMQ消息队列操作的封装。
"""

from functools import lru_cache
from typing import Optional, Callable
import json

import pika

from ..utils.config import settings


class RabbitMQClient:
    """RabbitMQ同步客户端"""

    def __init__(self):
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def connect(self) -> pika.BlockingConnection:
        """建立连接"""
        if self._connection is None or self._connection.is_closed:
            parameters = pika.URLParameters(settings.rabbitmq_url)
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
        return self._connection

    def get_channel(self) -> pika.adapters.blocking_connection.BlockingChannel:
        """获取通道"""
        if self._channel is None or self._channel.is_closed:
            self.connect()
        return self._channel

    def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "direct",
        durable: bool = True,
    ) -> None:
        """声明交换机"""
        channel = self.get_channel()
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=durable,
        )

    def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        arguments: Optional[dict] = None,
    ) -> None:
        """声明队列"""
        channel = self.get_channel()
        channel.queue_declare(
            queue=queue_name,
            durable=durable,
            arguments=arguments,
        )

    def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str,
    ) -> None:
        """绑定队列到交换机"""
        channel = self.get_channel()
        channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key,
        )

    def publish(
        self,
        exchange_name: str,
        routing_key: str,
        message: dict,
        persistent: bool = True,
    ) -> None:
        """发布消息"""
        channel = self.get_channel()
        properties = pika.BasicProperties(
            delivery_mode=2 if persistent else 1,
        )
        channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=json.dumps(message),
            properties=properties,
        )

    def consume(
        self,
        queue_name: str,
        callback: Callable,
        auto_ack: bool = False,
    ) -> None:
        """消费消息"""
        channel = self.get_channel()

        def wrapper(ch, method, properties, body):
            try:
                message = json.loads(body)
                callback(message, method.routing_key)
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"Error processing message: {e}")
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=wrapper,
            auto_ack=auto_ack,
        )
        channel.start_consuming()

    def close(self) -> None:
        """关闭连接"""
        if self._channel and not self._channel.is_closed:
            self._channel.close()
        if self._connection and not self._connection.is_closed:
            self._connection.close()


class MessageQueueService:
    """消息队列服务"""

    def __init__(self):
        self.rabbitmq = RabbitMQClient()
        self._initialized = False

    def initialize(self) -> None:
        """初始化消息队列（声明交换机和队列）"""
        if self._initialized:
            return

        # 声明主交换机
        self.rabbitmq.declare_exchange(
            exchange_name=settings.rabbitmq_exchange,
            exchange_type="topic",
            durable=True,
        )

        # 声明CI/CD相关队列
        self.rabbitmq.declare_queue("cicd.pipeline.created", durable=True)
        self.rabbitmq.declare_queue("cicd.pipeline.updated", durable=True)
        self.rabbitmq.declare_queue("cicd.job.created", durable=True)
        self.rabbitmq.declare_queue("cicd.job.updated", durable=True)
        self.rabbitmq.declare_queue("cicd.test.completed", durable=True)
        self.rabbitmq.declare_queue("cicd.build.completed", durable=True)

        # 绑定队列到交换机
        self.rabbitmq.bind_queue(
            queue_name="cicd.pipeline.created",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="pipeline.created",
        )
        self.rabbitmq.bind_queue(
            queue_name="cicd.pipeline.updated",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="pipeline.updated",
        )
        self.rabbitmq.bind_queue(
            queue_name="cicd.job.created",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="job.created",
        )
        self.rabbitmq.bind_queue(
            queue_name="cicd.job.updated",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="job.updated",
        )
        self.rabbitmq.bind_queue(
            queue_name="cicd.test.completed",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="test.completed",
        )
        self.rabbitmq.bind_queue(
            queue_name="cicd.build.completed",
            exchange_name=settings.rabbitmq_exchange,
            routing_key="build.completed",
        )

        self._initialized = True

    def publish_pipeline_event(
        self,
        event_type: str,
        pipeline_data: dict,
    ) -> None:
        """发布Pipeline事件"""
        routing_key = f"pipeline.{event_type}"
        self.rabbitmq.publish(
            exchange_name=settings.rabbitmq_exchange,
            routing_key=routing_key,
            message=pipeline_data,
            persistent=True,
        )

    def publish_job_event(
        self,
        event_type: str,
        job_data: dict,
    ) -> None:
        """发布Job事件"""
        routing_key = f"job.{event_type}"
        self.rabbitmq.publish(
            exchange_name=settings.rabbitmq_exchange,
            routing_key=routing_key,
            message=job_data,
            persistent=True,
        )

    def publish_test_event(
        self,
        test_data: dict,
    ) -> None:
        """发布测试完成事件"""
        self.rabbitmq.publish(
            exchange_name=settings.rabbitmq_exchange,
            routing_key="test.completed",
            message=test_data,
            persistent=True,
        )

    def publish_build_event(
        self,
        build_data: dict,
    ) -> None:
        """发布构建完成事件"""
        self.rabbitmq.publish(
            exchange_name=settings.rabbitmq_exchange,
            routing_key="build.completed",
            message=build_data,
            persistent=True,
        )

    def close(self) -> None:
        """关闭连接"""
        self.rabbitmq.close()


# 全局单例
@lru_cache()
def get_message_queue_service() -> MessageQueueService:
    """获取消息队列服务单例"""
    return MessageQueueService()


# 导出
rabbitmq_client = RabbitMQClient()
message_queue_service = get_message_queue_service()
