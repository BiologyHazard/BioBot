from bisect import bisect_left
from typing import Any
from pathlib import Path

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .config import plugin_config
from .consts import COMBO_RANK, VERSION_TO_PLATE, combo_rank
from .image import image_to_bytesio
from .music import Mai, Music

# T_project = Literal['plate', 'achievement', 'combo']
# int = int
_COMBO_FILENAME: list[str] = ['', 'FC', 'FCp', 'AP', 'APp']
_COMBO_PIC_PATHS: list[Path] = [plugin_config.pic_path / f'UI_MSS_MBase_Icon_{x}.png' for x in _COMBO_FILENAME]


async def generate_achievement_pic(
        payload: dict[str, Any],
        group: tuple[str | None, str | None, str | None, str | None,
                     str | None, str | None, str | None, str | None, str | None, str],
        queryer: int | None = None
) -> MessageSegment | str:
    (version_han,
     ds,
     level,
     diff_han,
     goals,
     goal_han,
     achievement,
     combo,
     sync,
     user,
     ) = group

    num_per_line: int = 12
    font_size: float = 72.0
    image_pixels: float = 96.0
    color_block_border: float = 0.06
    col_spacing: float = 0.3
    row_spacing: float = 0.4
    row_spacing_between_items: float = 0.5
    x0: float = 3.0
    y0: float = 1.0
    text_x0: float = 1.0

    basic_color = '#45c124'
    advanced_color = '#ffba01'
    expert_color = '#ff5a66'
    master_color = '#9f51dc'
    remaster_color = '#ecd3ff'
    colors: list[str] = [basic_color, advanced_color, expert_color, master_color, remaster_color]

    payload['version'] = list(VERSION_TO_PLATE)
    data: dict[str, list[dict[str, Any]]] | str = await get_player_data('plate', payload, queryer)
    if isinstance(data, str):
        return data

    if version_han is not None:
        all_need_to_play: list[tuple[Music, int]] = []
        version_han = version_han[0]
        for music in Mai.music_list.by_version(version_han):
            diff_num: int = music.diff_num if version_han in '舞霸' else 4
            for diff in range(diff_num):
                all_need_to_play.append((music, diff))
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        max_show_count: int = 256 if version_han in '舞霸' else 64
        if len(all_need_to_play) <= max_show_count:
            show_count: int = len(all_need_to_play)
        else:
            # 下标为`max_show_count`的乐曲一定不显示
            tmp_music, tmp_diff = all_need_to_play[max_show_count - 1]
            dont_show_level: str = tmp_music.level[tmp_diff]
            show_count = bisect_left(all_need_to_play,
                                     True,
                                     0, max_show_count,
                                     key=lambda x: x[0].level[x[1]] == dont_show_level)
    elif ds is not None:
        all_need_to_play = Mai.music_list.by_ds(float(ds))
        show_count = len(all_need_to_play)
    elif level is not None:
        all_need_to_play = Mai.music_list.by_level(level)
        show_count = len(all_need_to_play)
    elif diff_han is not None:
        diff: int = '绿黄红紫白'.index(diff_han)
        all_need_to_play = [(music, diff) for music in Mai.music_list]
        show_count = len(all_need_to_play)
    else:
        raise ValueError

    if goals is None:
        combo = 'FC'
    if goal_han is not None:
        if goal_han in '極极':
            combo = 'FC'
        elif goal_han == '将':
            achievement = 'SSS'
        elif goal_han == '神':
            combo = 'AP'
        elif goal_han in '舞舞':
            sync = 'FSD+'
        elif goal_han == '者':
            achievement = 'A'

    image: Image.Image = Image.new('RGBA', (2048, 2048), 'white')
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
    font: ImageFont.FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path), round(font_size))

    last_level: str | None = None
    col: int = 0
    y: float = -(1 + row_spacing_between_items)
    for music, level_index in all_need_to_play[:show_count]:
        if music.level[level_index] == last_level:
            col += 1
            col %= num_per_line
            if col == 0:
                y += 1 + row_spacing
        else:
            last_level = music.level[level_index]
            col = 0
            y += 1 + row_spacing_between_items
            draw.text((text_x0 * image_pixels, (y0 + y + 1/2) * image_pixels), music.level[level_index], 'black', font, 'lm')

        cover: Image.Image = Image.open(await music.get_cover()).resize((round(image_pixels), round(image_pixels)))
        draw.rectangle((round((x0 + col * (1 + col_spacing) - color_block_border) * image_pixels - 1/2),
                        round((y0 + y - color_block_border) * image_pixels - 1/2),
                        round((x0 + col * (1 + col_spacing) + 1 + color_block_border) * image_pixels - 1/2),
                        round((y0 + y + 1 + color_block_border) * image_pixels - 1/2)),
                       colors[level_index])
        # draw.polygon((round((x0 + col * (1 + col_spacing) - color_block_border) * image_pixels - 1/2),
        #               round((y0 + y - color_block_border) * image_pixels - 1/2),
        #               round((x0 + col * (1 + col_spacing) - color_block_border) * image_pixels - 1/2),
        #               round((y0 + y + 3 * color_block_border) * image_pixels - 1/2),
        #               round((x0 + col * (1 + col_spacing) + 3 * color_block_border) * image_pixels - 1/2),
        #               round((y0 + y - color_block_border) * image_pixels - 1/2)),
        #              colors[level_index])
        image.alpha_composite(cover,
                              (round((x0 + col * (1 + col_spacing)) * image_pixels),
                               round((y0 + y) * image_pixels)))

        for chart_info in data['verlist']:
            if str(chart_info['id']) == music.id and chart_info['level_index'] == level_index:
                chart_info: dict[str, Any] = chart_info
                break
        else:
            raise ValueError

        if combo is not None:
            if combo.upper() in COMBO_RANK:
                combo_goal_index: int = COMBO_RANK.index(combo.upper())
            else:
                combo_goal_index = combo_rank.index(combo.lower())
            music_combo_index: int = combo_rank.index(chart_info['fc'])
            if music_combo_index >= combo_goal_index:
                combo_image: Image.Image = Image.open(_COMBO_PIC_PATHS[music_combo_index])
                w, h = combo_image.size
                image.alpha_composite(combo_image,
                                      (round((x0 + col * (1 + col_spacing) + 1/2) * image_pixels - w/2),
                                       round((y0 + y + 1/2) * image_pixels - h/2)))

    return MessageSegment.image(image_to_bytesio(image))
