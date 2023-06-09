from typing import Any, Literal

from nonebot.adapters.onebot.v11 import MessageSegment

from .api_data import get_player_data
from .consts import PLATE_TO_VERSION
from .music import Mai, Music
from .config import plugin_config

T_project = Literal['plate', 'achievement', 'combo']
T_diff = int


async def generate_achievement_pic(project: T_project, payload: dict[str, Any], goal: str, queryer: int | None = None) -> MessageSegment | str:
    if project == 'plate':
        version_han, goal_han = goal[0], goal[1]
        if goal_han == '舞':
            goal_han = '舞舞'

        if goal == '真将':
            return '真系没有真将哦~'

        payload['version'] = PLATE_TO_VERSION[version_han] if version_han != '霸' else PLATE_TO_VERSION['舞']
        data: dict[str, Any] | str = await get_player_data('plate', payload, queryer)
        if isinstance(data, str):
            return data

        all_need_to_play: list[tuple[Music, T_diff]] = []
        for music in Mai.music_list.filter(version=payload['version']):
            diff_num: int = music.diff_num if version_han == '舞' else 4
            for diff in range(diff_num):
                all_need_to_play.append((music, diff))
        all_need_to_play.sort(key=lambda x: x[0].ds, reverse=True)
        if len(all_need_to_play) <= 128:
            show_num: int = len(all_need_to_play)
        else:
            # 下标为128的乐曲一定不显示
            tmp_music, tmp_diff = all_need_to_play[plugin_config.max_show_count]
            dont_show_level = tmp_music.level
    ...
