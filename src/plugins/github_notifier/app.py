"""HTTP endpoint for repository webhooks."""

import asyncio
from urllib.parse import urlsplit

from githubkit.webhooks import parse
from nonebot import get_bots, logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.drivers import URL, ASGIMixin, Driver, HTTPServerSetup, Request, Response
from nonebot_plugin_orm import get_session
from pydantic import ValidationError
from sqlalchemy import select

from .config import plugin_config
from .formatting import WebhookEnvelope, format_event
from .models import (
    GithubNotifierDelivery,
    GithubNotifierRepository,
    GithubNotifierSubscription,
    GithubNotifierWebhook,
)
from .signature import verify_signature

_delivery_lock = asyncio.Lock()


async def _send(target_type: str, target_id: str, message: str) -> bool:
    for bot in get_bots().values():
        try:
            if target_type == "group":
                await bot.send_group_msg(
                    group_id=int(target_id), message=MessageSegment.text(message)
                )
            else:
                await bot.send_private_msg(
                    user_id=int(target_id), message=MessageSegment.text(message)
                )
            return True
        except Exception:
            logger.exception("GitHub 通知发送失败：{} {}", target_type, target_id)
    return False


async def receive_webhook(request: Request) -> Response:
    token = request.url.path.rsplit("/", 1)[-1]
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
        if kind not in {"push", "pull_request", "issues"}:
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

        async with _delivery_lock:
            subscriptions = (
                await session.scalars(
                    select(GithubNotifierSubscription).where(
                        GithubNotifierSubscription.webhook_id == webhook.id
                    )
                )
            ).all()
            failed = False
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
                if not await _send(
                    subscription.target_type, subscription.target_id, message
                ):
                    failed = True
                    continue
                session.add(
                    GithubNotifierDelivery(
                        webhook_id=webhook.id,
                        delivery_id=delivery_id,
                        target_type=subscription.target_type,
                        target_id=subscription.target_id,
                    )
                )
                await session.commit()
            return Response(
                503 if failed else 200,
                content="Some notifications failed" if failed else "OK",
            )


def add_routes(driver: Driver) -> None:
    if not isinstance(driver, ASGIMixin):
        raise RuntimeError("github_notifier 需要支持 HTTP 服务的驱动器")
    base_path = urlsplit(plugin_config.github_notifier_webhook_payload_url).path
    path = f"{base_path.rstrip('/')}/{{token}}"
    driver.setup_http_server(
        HTTPServerSetup(
            path=URL(path, encoded=True),
            method="POST",
            name="github-notifier-webhook",
            handle_func=receive_webhook,
        )
    )
