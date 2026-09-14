"""在机器人运行期间安全地重载 ``arknights-game-model`` 游戏数据。

本模块只负责构建和发布内存快照，不负责拉取上游仓库。外部程序更新解包文件
后，下一次检查会发现文件指纹变化并加载新数据。
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from arknights_game_model._raw_game_data import data_structure
from arknights_game_model.character_model import Character
from arknights_game_model.config import Config as ModelConfig
from arknights_game_model.game_data import GameData, game_data

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

type DataFingerprint = tuple[tuple[str, int, int], ...]
"""数据源指纹；每个元素依次记录文件路径、纳秒级修改时间和文件大小。"""


class DataChangedDuringReloadError(RuntimeError):
    """加载新快照期间源文件再次发生变化。"""


def _iter_model_data_files(
    folder: Path, structure: dict[str, Any] = data_structure
) -> Iterator[Path]:
    """按照模型声明的数据结构，递归生成其实际读取的文件路径。"""
    for name, child in structure.items():
        path = folder / name
        if isinstance(child, dict):
            yield from _iter_model_data_files(path, child)
        else:
            yield path.with_suffix(f".{child}")


class GameDataReloader:
    """构建并原子发布游戏数据快照。

    新数据会先加载到独立的 :class:`GameData` 实例中。只有完整加载成功，且源
    文件在加载前后保持一致时，才会替换包内的全局 ``game_data`` 单例。
    """

    def __init__(self, config: ModelConfig) -> None:
        self._config = config
        # 最近一次成功发布的数据指纹；None 表示尚未加载初始快照。
        self._fingerprint: DataFingerprint | None = None
        # 串行化启动加载、定时检查以及可能的手动刷新。
        self._lock = asyncio.Lock()

    @property
    def source_files(self) -> tuple[Path, ...]:
        """返回构建完整快照所依赖的所有文件。"""
        return (
            *_iter_model_data_files(self._config.gamedata_folder),
            self._config.online_time_path,
            self._config.yituliu_item_value_path,
        )

    def fingerprint(self) -> DataFingerprint:
        """读取数据源指纹，不读取或散列体积较大的文件内容。"""
        result = []
        for path in self.source_files:
            stat = path.stat()
            result.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(result)

    def _build_snapshot(self) -> GameData:
        """在独立实例中同步加载并校验一份完整数据快照。"""
        snapshot = GameData()
        kwargs: dict[str, Any] = {
            name: getattr(self._config, name) for name in ModelConfig.model_fields
        }
        # GameData.load_data 内部会再创建一次 BaseSettings。禁止它隐式读取 .env，
        # 避免把机器人其他配置作为 extra 保留并输出到模型库日志。
        kwargs["_env_file"] = None
        snapshot.load_data(**kwargs)
        return snapshot

    async def reload_if_changed(self, *, force: bool = False) -> bool:
        """在数据变化时重载，并返回是否发布了新快照。

        Args:
            force: 即使文件指纹未变化也强制重载，供首次启动等场景使用。

        Raises:
            DataChangedDuringReloadError: 加载期间源文件发生变化，新快照已丢弃。
            Exception: 文件读取或模型校验失败。调用方可决定是否保留旧快照。
        """
        async with self._lock:
            # JSON 解析与 Pydantic 校验较耗时，放到线程中避免阻塞事件循环。
            before = await asyncio.to_thread(self.fingerprint)
            if not force and before == self._fingerprint:
                return False

            snapshot = await asyncio.to_thread(self._build_snapshot)
            after = await asyncio.to_thread(self.fingerprint)
            # 解包仓库可能正处于更新过程；不发布由新旧文件混合而成的快照。
            if before != after:
                raise DataChangedDuringReloadError(
                    "游戏数据在加载期间仍在变化，已放弃本次快照"
                )

            # 保留模型包原有的单例身份，因为 Character、Item 等模型方法会在内部
            # 再次导入该单例。替换整个属性字典可一次性发布完整快照。
            game_data.__dict__ = snapshot.__dict__
            # 此方法带有 lru_cache；清除缓存，避免旧 Character 对象长期存活，
            # 同时确保模组列表来自刚发布的数据。
            Character.uniequip_ids.cache_clear()
            self._fingerprint = after
            return True
