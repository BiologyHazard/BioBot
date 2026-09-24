"""HTTP endpoint for repository webhooks."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from githubkit.webhooks import parse
from nonebot import get_bots, logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.drivers import URL, ASGIMixin, Driver, HTTPServerSetup, Request, Response
from nonebot_plugin_orm import get_session
from pydantic import ValidationError
from sqlalchemy import select

from .config import plugin_config
from .events import SUPPORTED_WEBHOOK_EVENTS
from .formatting import WebhookEnvelope, format_event
from .models import (
    GithubNotifierDelivery,
    GithubNotifierRepository,
    GithubNotifierSubscription,
    GithubNotifierWebhook,
)
from .signature import verify_signature

# 同一个 webhook 可能同时收到重复投递，串行处理可以避免去重记录竞争。
_delivery_lock = asyncio.Lock()

DeliveryKey = tuple[int, str, str, str]
Target = tuple[str, str]


@dataclass(frozen=True, slots=True)
class _QueuedNotification:
    """一条待发送消息及其原始 delivery 去重键。"""

    message: str
    delivery_key: DeliveryKey
    target: Target


@dataclass(slots=True)
class _PendingBatch:
    """同一仓库时间窗内收集到的待发送消息。"""

    notifications: list[_QueuedNotification] = field(default_factory=list)
    task: asyncio.Task[None] | None = None


# 时间窗按仓库隔离；不同仓库的 webhook 不会互相延迟。
_batch_lock = asyncio.Lock()
_pending_batches: dict[int, _PendingBatch] = {}
_pending_delivery_keys: set[DeliveryKey] = set()


async def _flush_batch(repository_id: int, batch: _PendingBatch) -> None:
    """等待时间窗结束后，按目标发送一个仓库的合并通知。"""
    try:
        await asyncio.sleep(plugin_config.github_notifier_batch_window_seconds)

        # 先摘出当前批次，让窗口结束后到达的新事件进入下一批次。
        async with _batch_lock:
            if _pending_batches.get(repository_id) is not batch:
                return
            del _pending_batches[repository_id]
            notifications = list(batch.notifications)

        grouped: dict[Target, list[_QueuedNotification]] = defaultdict(list)
        for notification in notifications:
            grouped[notification.target].append(notification)

        async with _delivery_lock:
            async with get_session() as session:
                for target, target_notifications in grouped.items():
                    messages = [
                        notification.message for notification in target_notifications
                    ]
                    delivered = await _send_forward(target[0], target[1], messages)
                    if not delivered:
                        logger.error(
                            "GitHub 合并通知发送失败：仓库 {}，目标 {} {}",
                            repository_id,
                            target[0],
                            target[1],
                        )
                        continue

                    for notification in target_notifications:
                        webhook_id, delivery_id, target_type, target_id = (
                            notification.delivery_key
                        )
                        session.add(
                            GithubNotifierDelivery(
                                webhook_id=webhook_id,
                                delivery_id=delivery_id,
                                target_type=target_type,
                                target_id=target_id,
                            )
                        )
                    await session.commit()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("GitHub 合并通知处理失败：仓库 {}", repository_id)
    finally:
        # 发送完成后才允许同一 delivery 再次进入队列；发送失败时也释放它，
        # 便于 GitHub 重试或后续相同 delivery 被重新接收。
        async with _batch_lock:
            for notification in batch.notifications:
                _pending_delivery_keys.discard(notification.delivery_key)


async def _queue_notifications(
    repository_id: int, notifications: list[_QueuedNotification]
) -> None:
    """把一批 webhook 通知放入对应仓库的时间窗。"""
    if not notifications:
        return

    async with _batch_lock:
        new_notifications: list[_QueuedNotification] = []
        for notification in notifications:
            if notification.delivery_key in _pending_delivery_keys:
                continue
            _pending_delivery_keys.add(notification.delivery_key)
            new_notifications.append(notification)
        if not new_notifications:
            return

        batch = _pending_batches.get(repository_id)
        if batch is None:
            batch = _PendingBatch()
            _pending_batches[repository_id] = batch
            batch.task = asyncio.create_task(_flush_batch(repository_id, batch))
        batch.notifications.extend(new_notifications)


async def _send_forward(
    target_type: str, target_id: str, messages: list[str]
) -> bool:
    """通过 OneBot 扩展 API 发送真正的合并转发消息。"""
    for bot in get_bots().values():
        try:
            nodes = Message(
                MessageSegment.node_custom(
                    int(bot.self_id), "GitHub", Message(MessageSegment.text(message))
                )
                for message in messages
            )
            if target_type == "group":
                await bot.send_group_forward_msg(
                    group_id=int(target_id), messages=nodes
                )
            else:
                await bot.send_private_forward_msg(
                    user_id=int(target_id), messages=nodes
                )
            return True
        except Exception:
            logger.exception("GitHub 合并转发发送失败：{} {}", target_type, target_id)
    return False


async def receive_webhook(request: Request) -> Response:
    """校验、解析并分发一条 GitHub webhook 投递。

    请求体必须保持原始字节形式，因为 GitHub 的 HMAC 签名覆盖的就是这段
    原始内容。通过 token 找到 webhook 后，再校验仓库、事件类型和投递 ID，
    最后按订阅目标把通知放入时间窗，并在后台记录已成功处理的投递。
    """
    token = request.url.path.rsplit("/", 1)[-1]
    # 验签必须使用 request.content，不能使用已经反序列化的 JSON 对象。
    body = request.content
    logger.debug(
        "收到 GitHub webhook：headers={!r}, payload={!r}", dict(request.headers), body
    )
    if not isinstance(body, bytes):
        return Response(400, content="Expected a JSON request body")

    async with get_session() as session:
        record = await session.execute(
            select(GithubNotifierWebhook, GithubNotifierRepository)
            .join(
                GithubNotifierRepository,
                GithubNotifierRepository.id == GithubNotifierWebhook.repository_id,
            )
            .where(GithubNotifierWebhook.token == token)
        )
        row = record.one_or_none()
        if row is None:
            return Response(404, content="Webhook is not registered")
        webhook, repository = row
        if not verify_signature(
            body, webhook.secret, request.headers.get("X-Hub-Signature-256")
        ):
            return Response(403, content="Invalid webhook signature")
        try:
            envelope = WebhookEnvelope.model_validate_json(body)
        except ValidationError:
            return Response(400, content="Missing repository name")
        if envelope.repository.full_name.lower() != repository.full_name:
            return Response(403, content="Webhook repository mismatch")

        kind = request.headers.get("X-GitHub-Event", "")
        # 未支持的事件直接确认收件，避免 GitHub 因无关事件反复重试。
        if kind not in SUPPORTED_WEBHOOK_EVENTS:
            return Response(200, content="Event ignored")
        try:
            event = parse(kind, body)
        except (ValidationError, ValueError):
            return Response(400, content="Invalid GitHub webhook payload")
        message = format_event(kind, event)
        if message is None:
            return Response(200, content="Event ignored")
        delivery_id = request.headers.get("X-GitHub-Delivery")
        if not delivery_id or len(delivery_id) > 128:
            return Response(400, content="Missing or invalid delivery ID")

        # 记录按 webhook、delivery 和目标三者联合去重，允许同一事件发送给多个目标。
        # 消息先进入同仓库的时间窗，后台任务在窗口结束后再发送，避免阻塞 GitHub
        # webhook 请求，也避免相邻事件分别产生多条 QQ 消息。
        async with _delivery_lock:
            subscriptions = (
                await session.scalars(
                    select(GithubNotifierSubscription).where(
                        GithubNotifierSubscription.webhook_id == webhook.id
                    )
                )
            ).all()
            notifications: list[_QueuedNotification] = []
            for subscription in subscriptions:
                delivered = await session.scalar(
                    select(GithubNotifierDelivery.id).where(
                        GithubNotifierDelivery.webhook_id == webhook.id,
                        GithubNotifierDelivery.delivery_id == delivery_id,
                        GithubNotifierDelivery.target_type == subscription.target_type,
                        GithubNotifierDelivery.target_id == subscription.target_id,
                    )
                )
                if delivered is not None:
                    continue
                notifications.append(
                    _QueuedNotification(
                        message=message,
                        delivery_key=(
                            webhook.id,
                            delivery_id,
                            subscription.target_type,
                            subscription.target_id,
                        ),
                        target=(subscription.target_type, subscription.target_id),
                    )
                )
            await _queue_notifications(repository.id, notifications)
            return Response(200, content="Queued")


def add_routes(driver: Driver) -> None:
    """根据配置中的 URL 路径注册带 token 的 POST webhook 路由。"""
    if not isinstance(driver, ASGIMixin):
        raise RuntimeError("github_notifier 需要支持 HTTP 服务的驱动器")
    base_path = urlsplit(plugin_config.github_notifier_webhook_payload_url).path
    # token 是每个 webhook 批次的独立凭据，因此路由末尾必须保留动态参数。
    path = f"{base_path.rstrip('/')}/{{token}}"
    driver.setup_http_server(
        HTTPServerSetup(
            path=URL(path, encoded=True),
            method="POST",
            name="github-notifier-webhook",
            handle_func=receive_webhook,
        )
    )
