import math
import random
from bisect import bisect_left, bisect_right
from pathlib import Path
from typing import Any

from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot import logger
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .config import plugin_config
from .consts import (COMBO_RANK, SCORE_RANK, SYNC_RANK, VERSION_TO_PLATE,
                     achievementList, combo_rank, score_rank, sync_rank)
from .image import image_to_bytesio, image_resize_by
from .music import Mai, Music

# T_project = Literal['plate', 'achievement', 'combo']
# int = int
_COMBO_FILENAME: list[str] = ['', 'FC', 'FCp', 'AP', 'APp']
_COMBO_PIC_PATHS: list[Path] = [plugin_config.pic_path / f'UI_MSS_MBase_Icon_{x}.png' for x in _COMBO_FILENAME]
_ACHIEVEMENT_FILENAME: list[str] = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'Sp', 'SS', 'SSp', 'SSS', 'SSSp']
_ACHIEVEMENT_PIC_PATHS: list[Path] = [plugin_config.pic_path / f'UI_TTR_Rank_{x}.png' for x in _ACHIEVEMENT_FILENAME]
_SYNC_FILENAME: list[str] = ['', 'FS', 'FSp', 'FSD', 'FSDp']
_SYNC_PIC_PATHS: list[Path] = [plugin_config.pic_path / f'UI_MSS_MBase_Icon_{x}.png' for x in _SYNC_FILENAME]


async def generate_achievement_pic(
        payload: dict[str, Any],
        group: tuple[str, str | None, str | None, str | None, str | None,
                     str, str | None, str | None, str | None, str | None, str],
        queryer: int | None = None
) -> MessageSegment | str:
    (music_range,
     version_han,
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
    header_font_size: float = 1.4
    font_size: float = 0.75
    cover_pixels: float = 96.0
    color_block_border: float = 0.06
    col_spacing: float = 0.3
    row_spacing: float = 0.4
    row_spacing_between_items: float = 0.5
    border_left: float = 3.5
    border_up: float = 5.0
    border_right: float = 1.5
    border_down: float = 1.5
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
        if version_han[0] not in '舞霸' and '代' not in version_han and goal_han is not None:
            diff_num: int = 4
        else:
            diff_num = 5
        all_need_to_play: list[tuple[Music, int]] = [(music, diff)
                                                     for music in Mai.music_list.by_version(version_han[0])
                                                     for diff in range(min(diff_num, music.diff_num))]
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        max_show_count: int = 256 if version_han[0] in '舞霸' else 64
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
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        show_count = len(all_need_to_play)
    elif level is not None:
        all_need_to_play = Mai.music_list.by_level(level)
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        show_count = len(all_need_to_play)
    elif diff_han is not None:
        diff: int = '绿黄红紫白'.index(diff_han[0])
        all_need_to_play = [(music, diff) for music in Mai.music_list if diff < music.diff_num]
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        max_show_count: int = 256
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
    else:
        raise ValueError

    if not goals:
        achievement = 'A'
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

    coordinates: list[tuple[float, float]] = []
    texts: list[tuple[float, float, str]] = []
    last_level: str | None = None
    col: int = 0
    y: float = border_up - (1 + row_spacing_between_items)
    for music, diff_index in all_need_to_play[:show_count]:
        if music.level[diff_index] == last_level:
            col += 1
            col %= num_per_line
            if col == 0:
                y += 1 + row_spacing
        else:
            last_level = music.level[diff_index]
            col = 0
            y += 1 + row_spacing_between_items
            # draw.text((text_x0 * image_pixels, y * image_pixels), music.level[diff_index], 'black', font, 'lm')
            texts.append((text_x0, y, music.level[diff_index]))
        x: float = border_left + col * (1 + col_spacing)
        coordinates.append((x, y))

    image_width: float = border_left + (1 + col_spacing) * (num_per_line - 1) + border_right
    image_height: float = y + border_down
    # 绘制背景图
    image: Image.Image = (
        Image.open(plugin_config.pic_path / 'BioBot/background.png')
        .resize((round(image_width * cover_pixels),
                 round(image_height * cover_pixels)))
    )
    top_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/top.png'),
                                             0.0009 * image_width * cover_pixels)
    bottom_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/bottom.png'),
                                                0.0009 * image_width * cover_pixels)
    left_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/left.png'),
                                              0.018 * cover_pixels)
    right_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/right.png'),
                                               0.018 * cover_pixels)
    ground_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/bubbles.png'),
                                                0.0008 * image_width * cover_pixels)
    for i in range(math.ceil(image.height / ground_image.height)):
        # 反正最大容许偏移量就是这么多，我也解释不明白
        image.alpha_composite(ground_image,
                              (round(-(0.0008 * 1693 - 1) * random.random() * image_width * cover_pixels),
                               i * ground_image.height))
    for i in range(math.ceil(image.height / left_image.height)):
        image.alpha_composite(left_image, (0, i * left_image.height))
    for i in range(math.ceil(image.height / right_image.height)):
        image.alpha_composite(right_image, (image.width - right_image.width, i * right_image.height))
    image.alpha_composite(top_image, (round(-0.15 * image_width * cover_pixels), 0))
    image.alpha_composite(bottom_image, (round(-0.15 * image_width * cover_pixels),
                                         image.height - bottom_image.height))
    # 画logo和写字
    logo_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path / 'BioBot/logo.png'),
                                              0.01 * cover_pixels)
    image.alpha_composite(logo_image, (round(-1.3 * cover_pixels),
                                       round(0.7 * cover_pixels)))
    header_font: ImageFont.FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path),
                                                             round(header_font_size * cover_pixels))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
    header_text: str = ''.join(x for x in group[:5] if x is not None) + '完成表'
    draw.text((round((image_width - 2.0) * cover_pixels),
               round(2.3 * cover_pixels)), music_range + goals + '完成表', 'black', header_font, 'rm')
    # 加载其他公用资源
    mask: Image.Image = Image.new('RGBA', (round((1 + 2 * color_block_border) * cover_pixels),
                                           round((1 + 2 * color_block_border) * cover_pixels)), '#00000080')
    dx_image: Image.Image = image_resize_by(Image.open(plugin_config.pic_path /
                                                       'UI_UPE_Infoicon_DeluxeMode.png'),
                                            0.0052 * cover_pixels)
    font: ImageFont.FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path),
                                                      round(font_size * cover_pixels))
    # 写字
    for x, y, text in texts:
        draw.text((x * cover_pixels, y * cover_pixels), text, 'black', font, 'lm')

    for (music, diff_index), (x, y) in zip(all_need_to_play[:show_count], coordinates):
        # 画封面背景、封面和DX标识
        cover: Image.Image = Image.open(await music.get_cover()).resize((round(cover_pixels), round(cover_pixels)))
        draw.rectangle((round((x - 1/2 - color_block_border) * cover_pixels - 1/2),
                        round((y - 1/2 - color_block_border) * cover_pixels - 1/2),
                        round((x + 1/2 + color_block_border) * cover_pixels - 1/2),
                        round((y + 1/2 + color_block_border) * cover_pixels - 1/2)),
                       colors[diff_index])
        # draw.polygon((round((x0 + col * (1 + col_spacing) - color_block_border) * image_pixels - 1/2),
        #               round((y0 + y - color_block_border) * image_pixels - 1/2),
        #               round((x0 + col * (1 + col_spacing) - color_block_border) * image_pixels - 1/2),
        #               round((y0 + y + 3 * color_block_border) * image_pixels - 1/2),
        #               round((x0 + col * (1 + col_spacing) + 3 * color_block_border) * image_pixels - 1/2),
        #               round((y0 + y - color_block_border) * image_pixels - 1/2)),
        #              colors[level_index])
        image.alpha_composite(cover, (round((x - 1/2) * cover_pixels), round((y - 1/2) * cover_pixels)))
        if music.type == 'DX':
            w, h = dx_image.size
            image.alpha_composite(dx_image, (round((x + 1/2) * cover_pixels - w),
                                             round((y - 1/2) * cover_pixels)))
        # 寻找成绩
        chart_info: dict[str, Any] | None = None
        for _chart_info in data['verlist']:
            if str(_chart_info['id']) == music.id and _chart_info['level_index'] == diff_index:
                chart_info = _chart_info
                break

        if chart_info is not None:  # 如果游玩过
            if combo is not None:
                if combo.upper() in COMBO_RANK:
                    combo_goal_index: int = COMBO_RANK.index(combo.upper())
                else:
                    combo_goal_index = combo_rank.index(combo.lower())
                music_combo_index: int = combo_rank.index(chart_info['fc'])
                if music_combo_index >= combo_goal_index:
                    image.alpha_composite(mask, (round((x - 1/2 - color_block_border) * cover_pixels),
                                                 round((y - 1/2 - color_block_border) * cover_pixels)))
                    combo_image: Image.Image = Image.open(_COMBO_PIC_PATHS[music_combo_index])
                    w, h = combo_image.size
                    combo_image: Image.Image = combo_image.resize((round(0.7 * cover_pixels),
                                                                   round(0.7 * cover_pixels * h / w)))
                    w, h = combo_image.size
                    image.alpha_composite(combo_image, (round(x * cover_pixels - w/2),
                                                        round(y * cover_pixels - h/2)))
            elif achievement is not None:
                if achievement.upper() in SCORE_RANK:
                    achievement_goal_index: int = SCORE_RANK.index(achievement.upper())
                else:
                    achievement_goal_index = score_rank.index(achievement.lower())
                music_achievement_index: int = bisect_right(achievementList, chart_info['achievements'])
                if music_achievement_index >= achievement_goal_index:
                    image.alpha_composite(mask, (round((x - 1/2 - color_block_border) * cover_pixels),
                                                 round((y - 1/2 - color_block_border) * cover_pixels)))
                    achievement_image: Image.Image = Image.open(_ACHIEVEMENT_PIC_PATHS[music_achievement_index])
                    w, h = achievement_image.size
                    achievement_image: Image.Image = achievement_image.resize((round(1.3 * cover_pixels),
                                                                               round(1.3 * cover_pixels * h / w)))
                    w, h = achievement_image.size
                    image.alpha_composite(achievement_image, (round(x * cover_pixels - w/2),
                                                              round(y * cover_pixels - h/2)))
            elif sync is not None:
                if sync.upper() in SYNC_RANK:
                    sync_goal_index: int = SYNC_RANK.index(sync.upper())
                else:
                    sync_goal_index = sync_rank.index(sync.lower())
                music_sync_index: int = sync_rank.index(chart_info['fs'])
                if music_sync_index >= sync_goal_index:
                    image.alpha_composite(mask, (round((x - 1/2 - color_block_border) * cover_pixels),
                                                 round((y - 1/2 - color_block_border) * cover_pixels)))
                    sync_image: Image.Image = Image.open(_SYNC_PIC_PATHS[music_sync_index])
                    w, h = sync_image.size
                    sync_image: Image.Image = sync_image.resize((round(0.7 * cover_pixels),
                                                                 round(0.7 * cover_pixels * h / w)))
                    w, h = sync_image.size
                    image.alpha_composite(sync_image, (round(x * cover_pixels - w/2),
                                                       round(y * cover_pixels - h/2)))
            else:
                raise ValueError

    return MessageSegment.image(image_to_bytesio(image))
