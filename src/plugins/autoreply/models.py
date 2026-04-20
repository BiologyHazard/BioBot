from nonebot_plugin_orm import Model
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class AutoReply(Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(String)
    trigger: Mapped[str] = mapped_column(String)
    reply: Mapped[str] = mapped_column(String)
    # 设置者信息
    user_id: Mapped[str] = mapped_column(String)
    nickname: Mapped[str] = mapped_column(String, nullable=True)
    card: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer)

    __table_args__ = (Index("idx_group_trigger", "group_id", "trigger"),)
