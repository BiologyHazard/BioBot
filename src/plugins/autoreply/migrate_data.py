import json
from pathlib import Path

from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .models import AutoReply

# 注意：此脚本需要在 nonebot 环境下运行，或者手动配置 orm
# 这里建议通过调用插件内函数或直接操作 session


async def migrate():
    data_dir = Path("data/autoreply")
    if not data_dir.exists():
        print("Data directory not found.")
        return

    async with get_session() as session:
        for path in data_dir.glob("*.json"):
            try:
                group_id = int(path.stem)
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

                print(f"Migrating Group: {group_id}")
                for trigger, replies in data.items():
                    for reply_content, info in replies.items():
                        # 检查是否已存在
                        stmt = select(AutoReply).where(
                            AutoReply.group_id == group_id,
                            AutoReply.trigger == trigger,
                            AutoReply.reply == reply_content,
                        )
                        existing = await session.scalar(stmt)
                        if existing:
                            continue

                        new_entry = AutoReply(
                            group_id=group_id,
                            trigger=trigger,
                            reply=reply_content,
                            user_id=info.get("qqid"),
                            nickname=info.get("nickname"),
                            card=info.get("card"),
                            role=info.get("role"),
                            created_at=info.get("time", 0),
                        )
                        session.add(new_entry)
                await session.commit()
            except Exception as e:
                print(f"Error migrating {path}: {e}")


if __name__ == "__main__":
    # 迁移脚本通常需要加载 NoneBot 环境
    # 简单的做法是让用户通过 nb-cli 运行或在插件加载时执行一次
    print("Please run this migration logic inside a NoneBot context.")
