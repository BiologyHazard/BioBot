from bisect import bisect_left
from typing import Any, Literal

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .config import plugin_config
from .consts import PLATE_TO_VERSION
from .image import image_to_bytesio
from .music import Mai, Music

# T_project = Literal['plate', 'achievement', 'combo']
# int = int


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

    if project == 'plate':
        version_han, goal_han = goal[0], goal[1]
        if goal_han == '舞':
            goal_han = '舞舞'

        if goal == '真将':
            return '真系没有真将哦~'

        payload['version'] = PLATE_TO_VERSION[version_han] if version_han != '霸' else PLATE_TO_VERSION['舞']
        data: dict[str, list[dict[str, Any]]] | str = await get_player_data('plate', payload, queryer)
        if isinstance(data, str):
            return data

        all_need_to_play: list[tuple[Music, int]] = []
        for music in Mai.music_list.filter(version=payload['version']):
            diff_num: int = music.diff_num if version_han in '舞霸' else 4
            for diff in range(diff_num):
                all_need_to_play.append((music, diff))
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        if len(all_need_to_play) <= plugin_config.max_show_count:
            show_count: int = len(all_need_to_play)
        else:
            # 下标为128的乐曲一定不显示
            tmp_music, tmp_diff = all_need_to_play[plugin_config.max_show_count - 1]
            dont_show_level: str = tmp_music.level[tmp_diff]
            show_count = bisect_left(all_need_to_play,
                                     True,
                                     0, plugin_config.max_show_count,
                                     key=lambda x: x[0].level[x[1]] == dont_show_level)

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
            # print(col, y, music.id, music.level, music.ds, music.title)
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
                    if goal_han == '极' and chart_info['fc']:
                        pass
                    break

        return MessageSegment.image(image_to_bytesio(image))

    raise NotImplementedError
