"""QQ commands for managing GitHub webhook subscriptions."""

import secrets
import sys
from argparse import ArgumentTypeError
from typing import Annotated, Any

from nonebot import on_shell_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser, Namespace
from nonebot_plugin_orm import AsyncSession
from sqlalchemy import delete, func, select

from .config import plugin_config
from .filters import REPOSITORY_PATTERN, event_filters
from .models import (
    GithubNotifierDelivery,
    GithubNotifierRepository,
    GithubNotifierSubscription,
    GithubNotifierWebhook,
)


def webhook_url(token: str) -> str:
    """根据 webhook token 生成提供给 GitHub 的完整 URL。"""
    return f"{plugin_config.github_notifier_webhook_payload_url.rstrip('/')}/{token}"


def webhook_settings_url(repository: str) -> str:
    """生成 GitHub 仓库的“新建 Webhook”页面地址。"""
    return f"https://github.com/{repository}/settings/hooks/new"


def repository_name(value: str) -> str:
    """校验并规范化 `owner/repository` 形式的仓库名。"""
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise ArgumentTypeError("仓库格式应为 owner/repo")
    return value.lower()


def target_id(value: str) -> str:
    """校验群号或 QQ 号必须是正整数。"""
    if not value.isdecimal() or int(value) < 1:
        raise ArgumentTypeError("目标 ID 必须是正整数")
    return value


class NoColorArgumentParser(ArgumentParser):
    """为根解析器及所有子解析器统一关闭帮助信息颜色。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """在 Python 3.14 及以上关闭 argparse 的彩色帮助输出。"""
        if sys.version_info >= (3, 14):
            kwargs.setdefault("color", False)
        super().__init__(*args, **kwargs)


parser = ArgumentParser(prog="ghn", description="管理 GitHub Webhook 通知订阅")
subparsers = parser.add_subparsers(dest="command", required=True)
for name in ("subscribe", "unsubscribe", "list"):
    subparser = subparsers.add_parser(name)
    if name != "list":
        subparser.add_argument("repository", type=repository_name, metavar="owner/repo")
    subparser.add_argument("--group", action="append", default=[], type=target_id)
    subparser.add_argument("--private", action="append", default=[], type=target_id)

ghn = on_shell_command("ghn", parser=parser, block=True, priority=5)


@ghn.handle()
async def handle_parse_error(error: Annotated[ParserExit, ShellCommandArgs()]) -> None:
    """把 shell 命令解析错误直接回复给用户。"""
    await ghn.finish(error.message)


async def resolve_targets(
    bot: Bot, event: MessageEvent, args: Namespace
) -> list[tuple[str, str]]:
    """根据消息来源和权限解析本次命令要操作的通知目标。

    普通用户只能操作当前私聊或当前群；超级管理员可以通过显式参数指定
    多个群和用户。返回值中的第一个元素是目标类型，第二个元素是目标 ID。
    """
    explicit = bool(args.group or args.private)
    is_superuser = await SUPERUSER(bot, event)
    if explicit and not is_superuser:
        raise ValueError("只有超级管理员可以使用 --group 或 --private")
    if explicit:
        return list(
            dict.fromkeys(
                [("group", value) for value in args.group]
                + [("private", value) for value in args.private]
            )
        )
    if isinstance(event, GroupMessageEvent):
        if args.command != "list" and not (
            is_superuser or await (GROUP_OWNER | GROUP_ADMIN)(bot, event)
        ):
            raise ValueError("只有群主或群管理员可以管理本群订阅")
        return [("group", str(event.group_id))]
    return [("private", event.get_user_id())]


async def subscribe(
    session: AsyncSession, repository_name_value: str, targets: list[tuple[str, str]]
) -> str:
    """为仓库添加订阅，并返回新的 webhook 配置说明。"""
    webhook_events = event_filters.webhook_events(repository_name_value)
    repository = await session.scalar(
        select(GithubNotifierRepository).where(
            GithubNotifierRepository.full_name == repository_name_value
        )
    )
    if repository is None:
        repository = GithubNotifierRepository(full_name=repository_name_value)
        session.add(repository)
        await session.flush()
    new_targets: list[tuple[str, str]] = []
    for kind, identifier in targets:
        existing = await session.scalar(
            select(GithubNotifierSubscription).where(
                GithubNotifierSubscription.repository_id == repository.id,
                GithubNotifierSubscription.target_type == kind,
                GithubNotifierSubscription.target_id == identifier,
            )
        )
        if existing is None:
            new_targets.append((kind, identifier))
    if not new_targets:
        return f"{repository_name_value} 对所选目标的订阅已存在，无需再添加 webhook。"

    webhook = GithubNotifierWebhook(
        repository_id=repository.id,
        token=secrets.token_urlsafe(24),
        secret=secrets.token_urlsafe(32),
    )
    session.add(webhook)
    await session.flush()
    for kind, identifier in new_targets:
        session.add(
            GithubNotifierSubscription(
                repository_id=repository.id,
                webhook_id=webhook.id,
                target_type=kind,
                target_id=identifier,
            )
        )
    # commit 后 AsyncSession 可能使属性过期，因此先保存凭据再提交。
    webhook_token = webhook.token
    webhook_secret = webhook.secret
    await session.commit()
    skipped = len(targets) - len(new_targets)
    summary = f"{repository_name_value} 已添加 {len(new_targets)} 个订阅目标。"
    if skipped:
        summary += f"另有 {skipped} 个目标已订阅，保持原有 webhook。"
    return (
        f"{summary}\n"
        f"添加 Webhook：{webhook_settings_url(repository_name_value)}\n"
        "请打开上面的链接，在 GitHub 页面填写以下信息：\n"
        f"Payload URL：{webhook_url(webhook_token)}\n"
        "Content type：application/json\n"
        f"Events：{'、'.join(webhook_events)}\n"
        f"Secret：{webhook_secret}\n"
        "填写完成后点击 Add webhook。"
    )


async def unsubscribe(
    session: AsyncSession, repository_name_value: str, targets: list[tuple[str, str]]
) -> str:
    """移除指定目标的订阅，并清理不再使用的 webhook 和投递记录。"""
    repository = await session.scalar(
        select(GithubNotifierRepository).where(
            GithubNotifierRepository.full_name == repository_name_value
        )
    )
    if repository is None:
        return f"{repository_name_value} 尚无订阅。"
    removed = 0
    # 一个批次的多个目标共用 webhook，删除目标后需要检查批次是否为空。
    affected_webhooks: set[int] = set()
    for kind, identifier in targets:
        subscription = await session.scalar(
            select(GithubNotifierSubscription).where(
                GithubNotifierSubscription.repository_id == repository.id,
                GithubNotifierSubscription.target_type == kind,
                GithubNotifierSubscription.target_id == identifier,
            )
        )
        if subscription is None:
            continue
        affected_webhooks.add(subscription.webhook_id)
        await session.execute(
            delete(GithubNotifierDelivery).where(
                GithubNotifierDelivery.webhook_id == subscription.webhook_id,
                GithubNotifierDelivery.target_type == kind,
                GithubNotifierDelivery.target_id == identifier,
            )
        )
        result = await session.execute(
            delete(GithubNotifierSubscription).where(
                GithubNotifierSubscription.id == subscription.id
            )
        )
        removed += result.rowcount or 0  # type: ignore
    deleted_urls: list[str] = []
    for webhook_id in affected_webhooks:
        remaining_on_webhook = await session.scalar(
            select(func.count())
            .select_from(GithubNotifierSubscription)
            .where(GithubNotifierSubscription.webhook_id == webhook_id)
        )
        if not remaining_on_webhook:
            webhook = await session.get(GithubNotifierWebhook, webhook_id)
            if webhook is not None:
                deleted_urls.append(webhook_url(webhook.token))
            await session.execute(
                delete(GithubNotifierWebhook).where(
                    GithubNotifierWebhook.id == webhook_id
                )
            )
    remaining = await session.scalar(
        select(func.count())
        .select_from(GithubNotifierSubscription)
        .where(GithubNotifierSubscription.repository_id == repository.id)
    )
    if not remaining:
        await session.delete(repository)
    await session.commit()
    notice = (
        "\n请在 GitHub 中删除这些 webhook：\n" + "\n".join(deleted_urls)
        if deleted_urls
        else ""
    )
    return f"已取消 {repository_name_value} 的 {removed} 个订阅。{notice}"


async def list_subscriptions(
    session: AsyncSession, targets: list[tuple[str, str]]
) -> str:
    """查询目标当前订阅的仓库并生成文本列表。"""
    lines: list[str] = []
    for kind, identifier in targets:
        names = (
            await session.scalars(
                select(GithubNotifierRepository.full_name)
                .join(GithubNotifierSubscription)
                .where(
                    GithubNotifierSubscription.target_type == kind,
                    GithubNotifierSubscription.target_id == identifier,
                )
                .order_by(GithubNotifierRepository.full_name)
            )
        ).all()
        label = "群" if kind == "group" else "私聊"
        lines.append(
            f"{label} {identifier}：" + ("、".join(names) if names else "无订阅")
        )
    return "\n".join(lines)


@ghn.handle()
async def handle_command(
    bot: Bot,
    event: MessageEvent,
    session: AsyncSession,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    """分派 subscribe、unsubscribe 和 list 三类 QQ 命令。"""
    try:
        targets = await resolve_targets(bot, event, args)
        if args.command == "subscribe":
            result = await subscribe(session, args.repository, targets)
        elif args.command == "unsubscribe":
            result = await unsubscribe(session, args.repository, targets)
        else:
            result = await list_subscriptions(session, targets)
    except ValueError as exc:
        result = str(exc)
    await ghn.finish(result)
