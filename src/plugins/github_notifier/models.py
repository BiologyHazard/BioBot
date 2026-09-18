from nonebot_plugin_orm import Model
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class GithubNotifierRepository(Model):
    """被订阅的 GitHub 仓库。"""

    __tablename__ = "github_notifier_repository"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)


class GithubNotifierWebhook(Model):
    """一个 webhook 批次及其签名凭据。"""

    __tablename__ = "github_notifier_webhook"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_notifier_repository.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    secret: Mapped[str] = mapped_column(String(128))


class GithubNotifierSubscription(Model):
    """仓库 webhook 与 QQ 群或用户之间的订阅关系。"""

    __tablename__ = "github_notifier_subscription"
    __table_args__ = (
        UniqueConstraint("repository_id", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("github_notifier_repository.id", ondelete="CASCADE"), index=True
    )
    webhook_id: Mapped[int] = mapped_column(
        ForeignKey("github_notifier_webhook.id", ondelete="CASCADE"), index=True
    )
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(64))


class GithubNotifierDelivery(Model):
    """已经成功发送到某个目标的 GitHub delivery 去重记录。"""

    __tablename__ = "github_notifier_delivery"
    __table_args__ = (
        UniqueConstraint("webhook_id", "delivery_id", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    webhook_id: Mapped[int] = mapped_column(
        ForeignKey("github_notifier_webhook.id", ondelete="CASCADE"), index=True
    )
    delivery_id: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(64))
