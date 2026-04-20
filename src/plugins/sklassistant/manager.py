import time
from collections.abc import Sequence
from typing import Any, Literal

from nonebot_plugin_orm import get_session
from sqlalchemy import delete, select, update

from .models import SKLToken


class Manager:
    async def load_all(self) -> Sequence[SKLToken]:
        async with get_session() as session:
            result = await session.scalars(select(SKLToken))
            return result.all()

    async def has_token(self, token: str) -> bool:
        async with get_session() as session:
            result = await session.scalar(
                select(SKLToken).where(SKLToken.token == token)
            )
            return result is not None

    async def add_item(
        self, qq: int, email: str, token: str, strict: bool = False
    ) -> bool:
        if await self.has_token(token):
            if strict:
                raise ValueError("Token already exists.")
            return False

        async with get_session() as session:
            item = SKLToken(
                qq=qq,
                email=email,
                token=token,
                enabled=True,
                remind=True,
                time=time.time(),
            )
            session.add(item)
            await session.commit()
            return True

    async def remove_item(
        self, key: Literal["qq", "email", "token"], value: Any
    ) -> int:
        async with get_session() as session:
            stmt = delete(SKLToken).where(getattr(SKLToken, key) == value)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount  # type: ignore

    async def set_enable_state(
        self, key: Literal["qq", "email", "token"], value: Any, enable: bool = True
    ) -> int:
        async with get_session() as session:
            stmt = (
                update(SKLToken)
                .where(getattr(SKLToken, key) == value)
                .values(enabled=enable)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount  # type: ignore

    async def set_remind_state(
        self, key: Literal["qq", "email", "token"], value: Any, remind: bool = True
    ) -> int:
        async with get_session() as session:
            stmt = (
                update(SKLToken)
                .where(getattr(SKLToken, key) == value)
                .values(remind=remind)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount  # type: ignore

    async def filter(
        self,
        qq: int | None = None,
        email: str | None = None,
        token: str | None = None,
        enabled: bool | None = None,
    ) -> Sequence[SKLToken]:
        async with get_session() as session:
            stmt = select(SKLToken)
            if qq is not None:
                stmt = stmt.where(SKLToken.qq == qq)
            if email is not None:
                stmt = stmt.where(SKLToken.email == email)
            if token is not None:
                stmt = stmt.where(SKLToken.token == token)
            if enabled is not None:
                stmt = stmt.where(SKLToken.enabled == enabled)
            result = await session.scalars(stmt)
            return result.all()


tokens: Manager = Manager()
