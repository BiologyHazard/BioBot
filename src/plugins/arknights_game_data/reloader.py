from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from arknights_game_model._raw_game_data import data_structure
from arknights_game_model.character_model import Character
from arknights_game_model.config import Config as ModelConfig
from arknights_game_model.game_data import GameData, game_data

type DataFingerprint = tuple[tuple[str, int, int], ...]


class DataChangedDuringReloadError(RuntimeError):
    """The source files changed while a new snapshot was being built."""


def _iter_model_data_files(
    folder: Path, structure: dict[str, Any] = data_structure
) -> Iterator[Path]:
    for name, child in structure.items():
        path = folder / name
        if isinstance(child, dict):
            yield from _iter_model_data_files(path, child)
        else:
            yield path.with_suffix(f".{child}")


class GameDataReloader:
    """Build and atomically publish immutable game-data snapshots."""

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        self._fingerprint: DataFingerprint | None = None
        self._lock = asyncio.Lock()

    @property
    def source_files(self) -> tuple[Path, ...]:
        return (
            *_iter_model_data_files(self._config.gamedata_folder),
            self._config.online_time_path,
            self._config.yituliu_item_value_path,
        )

    def fingerprint(self) -> DataFingerprint:
        result = []
        for path in self.source_files:
            stat = path.stat()
            result.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(result)

    def _build_snapshot(self) -> GameData:
        snapshot = GameData()
        kwargs: dict[str, Any] = {
            name: getattr(self._config, name) for name in ModelConfig.model_fields
        }
        # GameData.load_data creates another BaseSettings instance.  Disable its
        # implicit .env read so unrelated application settings are neither retained
        # as extras nor printed in the model library's config log.
        kwargs["_env_file"] = None
        snapshot.load_data(**kwargs)
        return snapshot

    async def reload_if_changed(self, *, force: bool = False) -> bool:
        """Reload changed data, returning whether a new snapshot was published."""
        async with self._lock:
            before = await asyncio.to_thread(self.fingerprint)
            if not force and before == self._fingerprint:
                return False

            snapshot = await asyncio.to_thread(self._build_snapshot)
            after = await asyncio.to_thread(self.fingerprint)
            if before != after:
                raise DataChangedDuringReloadError(
                    "游戏数据在加载期间仍在变化，已放弃本次快照"
                )

            # Attribute lookup sees either the complete old dict or the complete new
            # dict.  Keeping the package singleton is important because model methods
            # import it internally when resolving items and modules.
            game_data.__dict__ = snapshot.__dict__
            Character.uniequip_ids.cache_clear()
            self._fingerprint = after
            return True
