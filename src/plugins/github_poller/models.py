"""GitHub Poller 的持久化模型。

游标记录增量位置，快照记录资源上一次状态，事件和投递记录保证重启后可恢复。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from nonebot_plugin_orm import Model
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from datetime import datetime


class GitHubRepository(Model):
    """规范化后的仓库元数据；同一 GitHub 仓库只保留一行。"""

    __tablename__ = "github_repository"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    node_id: Mapped[str] = mapped_column(String(128), default="")
    full_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    html_url: Mapped[str] = mapped_column(String(512))
    default_branch: Mapped[str] = mapped_column(String(256))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GitHubSubscription(Model):
    """一个 QQ 群或私聊目标对仓库的独立订阅开关。"""

    __tablename__ = "github_subscription"
    __table_args__ = (
        UniqueConstraint(
            "repository_id",
            "platform",
            "target_type",
            "target_id",
            name="uq_github_subscription_target",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_repository.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), default="onebot_v11")
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GitHubSubscriptionFilter(Model):
    """订阅的原子事件过滤器。"""

    __tablename__ = "github_subscription_filter"
    __table_args__ = (
        UniqueConstraint("subscription_id", "event_pattern", name="uq_gh_filter"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("github_subscription.id", ondelete="CASCADE"), index=True
    )
    event_pattern: Mapped[str] = mapped_column(String(128))


class GitHubSubscriptionBranch(Model):
    """订阅的分支模式，支持 @default 和 fnmatch 通配符。"""

    __tablename__ = "github_subscription_branch"
    __table_args__ = (
        UniqueConstraint("subscription_id", "pattern", name="uq_gh_branch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("github_subscription.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str] = mapped_column(String(256))


class GitHubPollCursor(Model):
    """每个仓库数据源的业务增量游标和失败重试状态。"""

    __tablename__ = "github_poll_cursor"
    __table_args__ = (
        UniqueConstraint("repository_id", "source", "scope", name="uq_gh_cursor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_repository.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(256), default="")
    watermark_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    watermark_id: Mapped[str | None] = mapped_column(String(256))
    state_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    initialized: Mapped[bool] = mapped_column(Boolean, default=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class GitHubResourceSnapshot(Model):
    """资源上次观察到的状态，用于从 REST 列表推导状态变化事件。"""

    __tablename__ = "github_resource_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "resource_type", "external_id", name="uq_gh_snapshot"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_repository.id", ondelete="CASCADE"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str] = mapped_column(String(256))
    state_hash: Mapped[str] = mapped_column(String(64))
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    github_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GitHubEvent(Model):
    """标准化事件；event_key 是跨重启去重的幂等键。"""

    __tablename__ = "github_event"
    __table_args__ = (Index("ix_gh_event_repo_time", "repository_id", "occurred_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_repository.id", ondelete="CASCADE"), index=True
    )
    event_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(256))
    actor_login: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(Text)
    html_url: Mapped[str] = mapped_column(String(1024))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GitHubDelivery(Model):
    """事件到具体订阅目标的投递任务及重试状态。"""

    __tablename__ = "github_delivery"
    __table_args__ = (
        UniqueConstraint("event_id", "subscription_id", name="uq_gh_delivery"),
        Index("ix_gh_delivery_status_retry", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("github_event.id", ondelete="CASCADE"), index=True
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("github_subscription.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
