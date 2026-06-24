"""Celery 应用配置 — Redis 作为消息代理和结果后端

架构:
- Broker: redis://127.0.0.1:6379/0 (事件队列)
- Result Backend: redis://127.0.0.1:6379/1 (任务结果)
- 自动从 FastAPI app 的配置加载
"""
import logging
from celery import Celery
from kombu import Exchange, Queue

logger = logging.getLogger(__name__)

# ── Redis 连接配置 ──
BROKER_URL = "redis://127.0.0.1:6379/0"
RESULT_BACKEND = "redis://127.0.0.1:6379/1"

celery_app = Celery(
    "ros_worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.workers.plan_worker"],
)

# ── 队列定义 ──
# 根据事件优先级分队列:
# - critical: approval/release 等高优先级事件
# - default: 普通业务事件
# - side_effect: 通知/审计等可延迟事件
celery_app.conf.task_queues = [
    Queue("critical", Exchange("critical"), routing_key="critical"),
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("side_effect", Exchange("side_effect"), routing_key="side_effect"),
]

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# ── 任务配置 ──
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    # 重试配置
    task_acks_late=True,           # worker 崩溃后重新投递
    task_reject_on_worker_lost=True,
    task_default_retry_delay=5,    # 默认重试延迟 5 秒
    task_max_retries=3,            # 最大重试 3 次
    # Worker 配置
    worker_concurrency=2,          # 2 个并行 worker（小内存服务器）
    worker_prefetch_multiplier=1,  # 每次只取一个任务
    # Beat 配置（定时任务）
    beat_schedule={},
)

logger.info("Celery app initialized: broker=%s, backend=%s", BROKER_URL, RESULT_BACKEND)
