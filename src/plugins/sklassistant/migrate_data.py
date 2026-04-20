import json
import time
from pathlib import Path

from nonebot import get_driver, logger
from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .config import plugin_config
from .models import SKLToken

driver = get_driver()

# 兼容旧配置路径
# 如果 config.py 中删除了该字段，这里直接硬编码或通过其他方式获取
OLD_TOKENS_FILE = Path("data/sklassistant/tokens.json")


@driver.on_startup
async def migrate_skl_tokens():
    if not OLD_TOKENS_FILE.is_file():
        return

    logger.info("Migrating SKLand tokens from JSON to database...")
    try:
        with OLD_TOKENS_FILE.open("r", encoding="utf-8") as f:
            old_data = json.load(f)

        if not isinstance(old_data, list):
            logger.warning("Old token data format is invalid.")
            return

        async with get_session() as session:
            for item in old_data:
                token_val = item.get("token")
                if not token_val:
                    continue

                # 检查是否已存在
                existing = await session.scalar(
                    select(SKLToken).where(SKLToken.token == token_val)
                )
                if not existing:
                    new_token = SKLToken(
                        qq=item.get("qq"),
                        email=item.get("email"),
                        token=token_val,
                        enabled=item.get("enabled", True),
                        remind=item.get("remind", True),
                        time=item.get("time", time.time()),
                    )
                    session.add(new_token)

            await session.commit()

        # 备份并删除旧文件
        backup_file = OLD_TOKENS_FILE.with_suffix(".json.bak")
        OLD_TOKENS_FILE.rename(backup_file)
        logger.info(
            f"Successfully migrated SKLand tokens. Old file backed up to {backup_file}"
        )
    except Exception as e:
        logger.error(f"Failed to migrate SKLand tokens: {e}")
