from __future__ import annotations

from datetime import UTC, datetime
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot_plugin_orm import AsyncSession
from sqlalchemy import delete, func, or_, select

from .events import (
    ALL_EVENTS,
    EVENTS,
    Target,
    expand_event_patterns,
    normalize_repository,
)
from .models import (
    GitHubDelivery,
    GitHubEvent,
    GitHubPollCursor,
    GitHubRepository,
    GitHubResourceSnapshot,
    GitHubSubscription,
    GitHubSubscriptionBranch,
    GitHubSubscriptionFilter,
)
from .service import service


HELP = """GitHub 仓库轮询通知（仅超级用户）
/ghp subscribe <owner/repo|URL> [事件...] [--branch 模式...] [目标...]
/ghp unsubscribe <owner/repo> [目标...]
/ghp list [目标...] | show <owner/repo> [目标...]
/ghp event list [类别]
/ghp event add|remove|set <owner/repo> <事件...> [目标...]
/ghp branch add|remove <owner/repo> <模式...> [目标...]
/ghp branch reset <owner/repo> [目标...]
/ghp pause|resume <owner/repo> [目标...]
/ghp poll [owner/repo] | status | help
目标可重复：--group <群号>、--private <QQ号>
预设：default、all；大类如 pr；原子事件如 pr.merged"""


def targets_from(
    event: MessageEvent, groups: list[str], privates: list[str]
) -> list[Target]:
    targets = [Target("group", value) for value in groups]
    targets.extend(Target("private", value) for value in privates)
    if not targets:
        if isinstance(event, GroupMessageEvent):
            targets.append(Target("group", str(event.group_id)))
        else:
            raise ValueError("私聊中必须使用 --group 或 --private 显式指定目标")
    return list({(target.type, target.id): target for target in targets}.values())


async def find_repository(session: AsyncSession, value: str) -> GitHubRepository:
    owner, repo = normalize_repository(value)
    record = await session.scalar(
        select(GitHubRepository).where(
            func.lower(GitHubRepository.full_name) == f"{owner}/{repo}".lower()
        )
    )
    if record is None:
        raise ValueError(f"尚未订阅仓库 {owner}/{repo}")
    return record


async def subscriptions_for(
    session: AsyncSession, repository_id: int, targets: list[Target]
) -> list[GitHubSubscription]:
    result: list[GitHubSubscription] = []
    for target in targets:
        subscription = await session.scalar(
            select(GitHubSubscription).where(
                GitHubSubscription.repository_id == repository_id,
                GitHubSubscription.platform == "onebot_v11",
                GitHubSubscription.target_type == target.type,
                GitHubSubscription.target_id == target.id,
            )
        )
        if subscription is None:
            raise ValueError(f"目标 {target.type}:{target.id} 未订阅该仓库")
        result.append(subscription)
    return result


async def subscribe(
    session: AsyncSession,
    event: MessageEvent,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
    branches: list[str],
) -> str:
    if not tokens:
        raise ValueError("缺少仓库参数")
    owner, repo = normalize_repository(tokens[0])
    patterns = expand_event_patterns(tokens[1:])
    targets = targets_from(event, groups, privates)
    metadata = await service.api.get_repository(owner, repo)
    now = datetime.now(UTC)
    repository = await session.scalar(
        select(GitHubRepository).where(GitHubRepository.github_id == metadata["id"])
    )
    if repository is None:
        repository = GitHubRepository(
            github_id=metadata["id"],
            node_id=metadata.get("node_id") or "",
            full_name=metadata["full_name"],
            html_url=metadata["html_url"],
            default_branch=metadata.get("default_branch") or "main",
            is_private=bool(metadata.get("private")),
            archived=bool(metadata.get("archived")),
            metadata_updated_at=_parse_time(metadata.get("updated_at")),
            created_at=now,
            updated_at=now,
        )
        session.add(repository)
        await session.flush()
    else:
        repository.full_name = metadata["full_name"]
        repository.html_url = metadata["html_url"]
        repository.default_branch = metadata.get("default_branch") or "main"
        repository.is_private = bool(metadata.get("private"))
        repository.archived = bool(metadata.get("archived"))
        repository.updated_at = now

    for target in targets:
        subscription = await session.scalar(
            select(GitHubSubscription).where(
                GitHubSubscription.repository_id == repository.id,
                GitHubSubscription.platform == "onebot_v11",
                GitHubSubscription.target_type == target.type,
                GitHubSubscription.target_id == target.id,
            )
        )
        if subscription is None:
            subscription = GitHubSubscription(
                repository_id=repository.id,
                platform="onebot_v11",
                target_type=target.type,
                target_id=target.id,
                enabled=True,
                created_by=str(event.user_id),
                created_at=now,
                updated_at=now,
            )
            session.add(subscription)
            await session.flush()
        else:
            subscription.enabled = True
            subscription.updated_at = now
        await session.execute(
            delete(GitHubSubscriptionFilter).where(
                GitHubSubscriptionFilter.subscription_id == subscription.id
            )
        )
        await session.execute(
            delete(GitHubSubscriptionBranch).where(
                GitHubSubscriptionBranch.subscription_id == subscription.id
            )
        )
        session.add_all(
            GitHubSubscriptionFilter(
                subscription_id=subscription.id, event_pattern=value
            )
            for value in sorted(patterns)
        )
        session.add_all(
            GitHubSubscriptionBranch(subscription_id=subscription.id, pattern=value)
            for value in sorted(set(branches) or {"@default"})
        )
    await session.commit()
    return format_configuration(
        metadata["full_name"], targets, patterns, set(branches) or {"@default"}
    )


async def unsubscribe(
    session: AsyncSession,
    event: MessageEvent,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
) -> str:
    if not tokens:
        raise ValueError("缺少仓库参数")
    repository = await find_repository(session, tokens[0])
    full_name = repository.full_name
    targets = targets_from(event, groups, privates)
    removed = 0
    for target in targets:
        subscription = await session.scalar(
            select(GitHubSubscription).where(
                GitHubSubscription.repository_id == repository.id,
                GitHubSubscription.platform == "onebot_v11",
                GitHubSubscription.target_type == target.type,
                GitHubSubscription.target_id == target.id,
            )
        )
        if subscription is None:
            continue
        await session.execute(
            delete(GitHubDelivery).where(
                GitHubDelivery.subscription_id == subscription.id
            )
        )
        await session.execute(
            delete(GitHubSubscriptionFilter).where(
                GitHubSubscriptionFilter.subscription_id == subscription.id
            )
        )
        await session.execute(
            delete(GitHubSubscriptionBranch).where(
                GitHubSubscriptionBranch.subscription_id == subscription.id
            )
        )
        await session.delete(subscription)
        removed += 1
    remaining = await session.scalar(
        select(func.count(GitHubSubscription.id)).where(
            GitHubSubscription.repository_id == repository.id
        )
    )
    if not remaining:
        await session.execute(
            delete(GitHubDelivery).where(
                GitHubDelivery.event_id.in_(
                    select(GitHubEvent.id).where(
                        GitHubEvent.repository_id == repository.id
                    )
                )
            )
        )
        await session.execute(
            delete(GitHubEvent).where(GitHubEvent.repository_id == repository.id)
        )
        await session.execute(
            delete(GitHubResourceSnapshot).where(
                GitHubResourceSnapshot.repository_id == repository.id
            )
        )
        await session.execute(
            delete(GitHubPollCursor).where(
                GitHubPollCursor.repository_id == repository.id
            )
        )
        await session.delete(repository)
    await session.commit()
    return f"已取消 {full_name} 的 {removed} 个目标订阅"


async def list_subscriptions(
    session: AsyncSession, event: MessageEvent, groups: list[str], privates: list[str]
) -> str:
    targets = targets_from(event, groups, privates)
    clauses = [
        (GitHubSubscription.target_type == target.type)
        & (GitHubSubscription.target_id == target.id)
        for target in targets
    ]
    rows = (
        await session.execute(
            select(GitHubSubscription, GitHubRepository)
            .join(
                GitHubRepository,
                GitHubRepository.id == GitHubSubscription.repository_id,
            )
            .where(or_(*clauses))
            .order_by(GitHubRepository.full_name)
        )
    ).all()
    if not rows:
        return "指定目标暂无 GitHub 订阅"
    lines = ["GitHub 订阅："]
    for subscription, repository in rows:
        state = "启用" if subscription.enabled else "暂停"
        lines.append(
            f"- {repository.full_name} · {subscription.target_type}:{subscription.target_id} · {state}"
        )
    return "\n".join(lines)


async def show(
    session: AsyncSession,
    event: MessageEvent,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
) -> str:
    if not tokens:
        raise ValueError("缺少仓库参数")
    repository = await find_repository(session, tokens[0])
    targets = targets_from(event, groups, privates)
    subscriptions = await subscriptions_for(session, repository.id, targets)
    lines = [
        f"{repository.full_name}",
        repository.html_url,
        f"默认分支：{repository.default_branch}",
    ]
    for subscription in subscriptions:
        filters = sorted(
            await session.scalars(
                select(GitHubSubscriptionFilter.event_pattern).where(
                    GitHubSubscriptionFilter.subscription_id == subscription.id
                )
            )
        )
        branches = sorted(
            await session.scalars(
                select(GitHubSubscriptionBranch.pattern).where(
                    GitHubSubscriptionBranch.subscription_id == subscription.id
                )
            )
        )
        lines.extend(
            (
                f"{subscription.target_type}:{subscription.target_id} · {'启用' if subscription.enabled else '暂停'}",
                f"事件：{' '.join(filters)}",
                f"分支：{' '.join(branches)}",
            )
        )
    return "\n".join(lines)


async def edit_events(
    session: AsyncSession,
    event: MessageEvent,
    operation: str,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
) -> str:
    if len(tokens) < 2:
        raise ValueError("用法：/ghp event add|remove|set <仓库> <事件...>")
    repository = await find_repository(session, tokens[0])
    values = expand_event_patterns(tokens[1:])
    targets = targets_from(event, groups, privates)
    subscriptions = await subscriptions_for(session, repository.id, targets)
    for subscription in subscriptions:
        current = set(
            await session.scalars(
                select(GitHubSubscriptionFilter.event_pattern).where(
                    GitHubSubscriptionFilter.subscription_id == subscription.id
                )
            )
        )
        final = (
            values
            if operation == "set"
            else current | values
            if operation == "add"
            else current - values
        )
        if not final:
            raise ValueError("订阅事件不能为空；如需取消仓库订阅请使用 unsubscribe")
        await session.execute(
            delete(GitHubSubscriptionFilter).where(
                GitHubSubscriptionFilter.subscription_id == subscription.id
            )
        )
        session.add_all(
            GitHubSubscriptionFilter(
                subscription_id=subscription.id, event_pattern=value
            )
            for value in sorted(final)
        )
        subscription.updated_at = datetime.now(UTC)
    await session.commit()
    return f"已为 {len(subscriptions)} 个目标{ {'add': '添加', 'remove': '移除', 'set': '设置'}[operation] }事件：{' '.join(sorted(values))}"


async def edit_branches(
    session: AsyncSession,
    event: MessageEvent,
    operation: str,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
) -> str:
    minimum = 1 if operation == "reset" else 2
    if len(tokens) < minimum:
        raise ValueError("用法：/ghp branch add|remove <仓库> <分支模式...>")
    repository = await find_repository(session, tokens[0])
    full_name = repository.full_name
    values = {"@default"} if operation == "reset" else set(tokens[1:])
    targets = targets_from(event, groups, privates)
    subscriptions = await subscriptions_for(session, repository.id, targets)
    for subscription in subscriptions:
        current = set(
            await session.scalars(
                select(GitHubSubscriptionBranch.pattern).where(
                    GitHubSubscriptionBranch.subscription_id == subscription.id
                )
            )
        )
        final = (
            values
            if operation == "reset"
            else current | values
            if operation == "add"
            else current - values
        )
        if not final:
            raise ValueError("分支规则不能为空，可使用 branch reset 恢复默认分支")
        await session.execute(
            delete(GitHubSubscriptionBranch).where(
                GitHubSubscriptionBranch.subscription_id == subscription.id
            )
        )
        session.add_all(
            GitHubSubscriptionBranch(subscription_id=subscription.id, pattern=value)
            for value in sorted(final)
        )
        subscription.updated_at = datetime.now(UTC)
    await session.commit()
    return f"已更新 {full_name} 的分支规则：{' '.join(sorted(final))}"


async def set_enabled(
    session: AsyncSession,
    event: MessageEvent,
    enabled: bool,
    tokens: list[str],
    groups: list[str],
    privates: list[str],
) -> str:
    if not tokens:
        raise ValueError("缺少仓库参数")
    repository = await find_repository(session, tokens[0])
    full_name = repository.full_name
    subscriptions = await subscriptions_for(
        session, repository.id, targets_from(event, groups, privates)
    )
    for subscription in subscriptions:
        subscription.enabled = enabled
        subscription.updated_at = datetime.now(UTC)
    await session.commit()
    return (
        f"已{'恢复' if enabled else '暂停'} {full_name} 的 {len(subscriptions)} 个订阅"
    )


async def event_list(tokens: list[str]) -> str:
    if tokens:
        category = tokens[0].lower()
        matching = sorted(
            event for event in ALL_EVENTS if event.startswith(f"{category}.")
        )
        if not matching:
            raise ValueError(f"未知事件类别：{category}")
        return f"{category}：\n" + "\n".join(f"- {event}" for event in matching)
    return (
        "支持的事件类别：\n"
        + "\n".join(f"- {name} ({len(actions)})" for name, actions in EVENTS.items())
        + f"\n共 {len(ALL_EVENTS)} 个原子事件"
    )


async def status() -> str:
    repositories, subscriptions, last_success, failures = await service.counts()
    rate = service.api.rate
    try:
        await service.api.rate_limit()
    except Exception:
        pass
    mode = "已认证" if service.api.authenticated else "未认证（仅公开仓库，额度较低）"
    remaining = "未知" if rate.remaining is None else f"{rate.remaining}/{rate.limit}"
    return "\n".join(
        (
            f"GitHub API：{mode}",
            f"仓库：{repositories}，订阅：{subscriptions}",
            f"最近成功轮询：{last_success.astimezone().isoformat() if last_success else '尚无'}",
            f"累计连续失败：{failures}",
            f"剩余额度：{remaining}",
            f"限制恢复：{rate.paused_until.astimezone().isoformat() if rate.paused_until else '未暂停'}",
        )
    )


def format_configuration(
    full_name: str, targets: list[Target], patterns: set[str], branches: set[str]
) -> str:
    return "\n".join(
        (
            f"已订阅 {full_name}",
            "目标：" + " ".join(f"{target.type}:{target.id}" for target in targets),
            "事件：" + " ".join(sorted(patterns)),
            "分支：" + " ".join(sorted(branches)),
            "首次轮询仅建立基线，不推送历史内容。",
        )
    )


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
