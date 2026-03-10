"""
Celery任务队列配置

提供Celery异步任务队列的配置和基础设置。
"""

from celery import Celery
from ..utils.config import settings

# 创建Celery应用
celery_app = Celery(
    "ai_cicd",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.build_tasks",
        "src.tasks.test_tasks",
        "src.tasks.analysis_tasks",
        "src.tasks.notification_tasks",
    ],
)

# Celery配置
celery_app.conf.update(
    # 任务配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # 任务执行配置
    task_acks_late=True,  # 任务执行完后才确认
    worker_prefetch_multiplier=4,  # 每次预取4个任务
    task_time_limit=3600,  # 任务最长运行时间（1小时）
    task_soft_time_limit=3300,  # 任务软超时（55分钟）
    task_track_started=True,  # 跟踪任务开始时间
    task_send_sent_event=True,  # 发送任务开始事件
    # 结果配置
    result_expires=3600,  # 结果保存1小时
    result_extended=True,  # 扩展结果过期时间
    # 路由配置
    task_routes={
        "src.tasks.build_tasks.*": {"queue": "build"},
        "src.tasks.test_tasks.*": {"queue": "test"},
        "src.tasks.analysis_tasks.*": {"queue": "analysis"},
        "src.tasks.notification_tasks.*": {"queue": "notification"},
    },
    # 限流配置
    task_annotations={
        "src.tasks.build_tasks.run_build": {"rate_limit": "10/m"},
        "src.tasks.test_tasks.run_test": {"rate_limit": "20/m"},
    },
    # 重试配置
    task_autoretry_for=(Exception,),  # 所有异常都自动重试
    task_retry_max_delay=300,  # 最大重试延迟5分钟
    task_retry_backoff=True,  # 启用指数退避
    task_retry_backoff_max=600,  # 最大退避时间10分钟
    task_retry_jitter=True,  # 添加随机抖动
    # 监控配置
    worker_send_task_events=True,  # 发送任务事件
    # 安全配置
    worker_hijack_root_logger=False,  # 不劫持根日志记录器
)
