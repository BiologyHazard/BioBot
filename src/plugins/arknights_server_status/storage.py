"""设备标识的持久化。

设备标识必须跨次运行保持一致，否则每次登录都像新设备，更容易触发账号风控。
服务器状态只保存在内存中，不落盘。
"""

import json
import secrets
from pathlib import Path
from typing import Any

from nonebot.log import logger

from .config import plugin_config

_device_id: str | None = None


def data_dir() -> Path:
    """插件数据目录；可用 `ARKNIGHTS_SERVER_DATA_DIR` 覆盖。"""
    return plugin_config.arknights_server_data_dir


def device_id_file() -> Path:
    return data_dir() / "device-id.json"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, value: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        logger.warning("写入 {} 失败，本次运行将只保留内存中的值", path)


def get_device_id() -> str:
    """取稳定的设备标识（40 位十六进制）。"""
    global _device_id
    if _device_id:
        return _device_id

    if plugin_config.arknights_device_id:
        _device_id = plugin_config.arknights_device_id
        return _device_id

    stored = _read_json(device_id_file())
    if isinstance(stored, str) and stored:
        _device_id = stored
        return _device_id

    _device_id = secrets.token_hex(20)
    _write_json(device_id_file(), _device_id)
    return _device_id
