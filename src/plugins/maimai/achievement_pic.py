from .consts import achievementList
from .consts import score_rank
from bisect import bisect_left, bisect_right
from typing import Any
from pathlib import Path

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .config import plugin_config
from .consts import COMBO_RANK, SCORE_RANK, VERSION_TO_PLATE, combo_rank, SYNC_RANK, sync_rank
from .image import image_to_bytesio
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
    cover_pixels: float = 96.0
    color_block_border: float = 0.06
    col_spacing: float = 0.3
    row_spacing: float = 0.4
    row_spacing_between_items: float = 0.5
    border_left: float = 3.5
    border_up: float = 1.5
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
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        show_count = len(all_need_to_play)
    elif level is not None:
        all_need_to_play = Mai.music_list.by_level(level)
        all_need_to_play.sort(key=lambda x: x[0].ds[x[1]], reverse=True)
        show_count = len(all_need_to_play)
    elif diff_han is not None:
        diff: int = '绿黄红紫白'.index(diff_han)
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

    if goals is None:
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
    top_image: Image.Image = Image.open(plugin_config.pic_path / 'BioBot/biobot_process_pic_top.png')
    w, h = top_image.size
    top_image = top_image.resize((round(image_width * cover_pixels),
                                  round(image_width * cover_pixels * h / w)))
    _, top_image_height = top_image.size
    bottom_image: Image.Image = Image.open(plugin_config.pic_path / 'BioBot/biobot_process_pic_bottom.png')
    w, h = bottom_image.size
    bottom_image = bottom_image.resize((round(image_width * cover_pixels),
                                        round(image_width * cover_pixels * h / w)))
    _, bottom_image_height = bottom_image.size
    middle_image: Image.Image = Image.open(plugin_config.pic_path / 'BioBot/biobot_process_pic_middle.png')
    w, h = middle_image.size
    # middle_image = middle_image.resize((round(image_width * cover_pixels), max(0, image_height *  - )))
    image: Image.Image = Image.new('RGBA', (round(image_width * cover_pixels),
                                            round(image_height * cover_pixels)), 'white')
    mask: Image.Image = Image.new('RGBA', (round((1 + 2 * color_block_border) * cover_pixels),
                                           round((1 + 2 * color_block_border) * cover_pixels)), '#00000080')
    dx_image: Image.Image = Image.open(plugin_config.pic_path / 'UI_UPE_Infoicon_DeluxeMode.png')
    w, h = dx_image.size
    dx_image = dx_image.resize((round(w*0.5), round(h*0.5)))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)
    font: ImageFont.FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path), round(font_size))

    for x, y, text in texts:
        draw.text((x * cover_pixels, y * cover_pixels), text, 'black', font, 'lm')

    for (music, diff_index), (x, y) in zip(all_need_to_play[:show_count], coordinates):
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

        chart_info: dict[str, Any] | None = None
        for _chart_info in data['verlist']:
            if str(_chart_info['id']) == music.id and _chart_info['level_index'] == diff_index:
                chart_info = _chart_info
                break

        if chart_info is not None:
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
