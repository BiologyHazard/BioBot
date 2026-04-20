from nonebot_plugin_orm import Model
from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column


class SKLToken(Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    qq: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    remind: Mapped[bool] = mapped_column(Boolean, default=True)
    time: Mapped[float] = mapped_column(Float)
