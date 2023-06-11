from math import ceil

from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageSegment

from .api_data import get_player_data
from .consts import DIFFICULTY_NAME, combo_rank, COMBO_RANK, sync_rank, SYNC_RANK, PLATE_TO_VERSION
from .image import image_to_bytesio, text_to_image
from .music import Mai, Music


async def player_plate_data(payload: dict, version_han: str, goal_han: str, nickname: str | None, queryer: int) -> MessageSegment | str:
    if goal_han == '舞':
        goal_han = '舞舞'

    if version_han + goal_han == '真将':
        return '真系没有真将哦~'
    payload['version'] = PLATE_TO_VERSION[version_han] if version_han != '霸' else PLATE_TO_VERSION['舞']
    data = await get_player_data('plate', payload, queryer)
    if isinstance(data, str):
        return data

    song_played = []
    song_remain_basic = []
    song_remain_advanced = []
    song_remain_expert = []
    song_remain_master = []
    song_remain_re_master = []
    song_remain_difficult = []

    if goal_han in ['将', '者']:
        for song in data['verlist']:
            if song['diff_index'] == 0 and song['achievements'] < (100.0 if goal_han == '将' else 80.0):
                song_remain_basic.append([song['id'], song['diff_index']])
            if song['diff_index'] == 1 and song['achievements'] < (100.0 if goal_han == '将' else 80.0):
                song_remain_advanced.append([song['id'], song['diff_index']])
            if song['diff_index'] == 2 and song['achievements'] < (100.0 if goal_han == '将' else 80.0):
                song_remain_expert.append([song['id'], song['diff_index']])
            if song['diff_index'] == 3 and song['achievements'] < (100.0 if goal_han == '将' else 80.0):
                song_remain_master.append([song['id'], song['diff_index']])
            if version_han in ['舞', '霸'] and song['diff_index'] == 4 and song['achievements'] < (100.0 if goal_han == '将' else 80.0):
                song_remain_re_master.append([song['id'], song['diff_index']])
            song_played.append([song['id'], song['diff_index']])
    elif goal_han in ['極', '极']:
        for song in data['verlist']:
            if song['diff_index'] == 0 and not song['fc']:
                song_remain_basic.append([song['id'], song['diff_index']])
            if song['diff_index'] == 1 and not song['fc']:
                song_remain_advanced.append([song['id'], song['diff_index']])
            if song['diff_index'] == 2 and not song['fc']:
                song_remain_expert.append([song['id'], song['diff_index']])
            if song['diff_index'] == 3 and not song['fc']:
                song_remain_master.append([song['id'], song['diff_index']])
            if version_han == '舞' and song['diff_index'] == 4 and not song['fc']:
                song_remain_re_master.append([song['id'], song['diff_index']])
            song_played.append([song['id'], song['diff_index']])
    elif goal_han == '舞舞':
        for song in data['verlist']:
            if song['diff_index'] == 0 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_basic.append([song['id'], song['diff_index']])
            if song['diff_index'] == 1 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_advanced.append([song['id'], song['diff_index']])
            if song['diff_index'] == 2 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_expert.append([song['id'], song['diff_index']])
            if song['diff_index'] == 3 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_master.append([song['id'], song['diff_index']])
            if version_han == '舞' and song['diff_index'] == 4 and song['fs'] not in ['fsd', 'fsdp']:
                song_remain_re_master.append([song['id'], song['diff_index']])
            song_played.append([song['id'], song['diff_index']])
    elif goal_han == '神':
        for song in data['verlist']:
            if song['diff_index'] == 0 and song['fc'] not in ['ap', 'app']:
                song_remain_basic.append([song['id'], song['diff_index']])
            if song['diff_index'] == 1 and song['fc'] not in ['ap', 'app']:
                song_remain_advanced.append([song['id'], song['diff_index']])
            if song['diff_index'] == 2 and song['fc'] not in ['ap', 'app']:
                song_remain_expert.append([song['id'], song['diff_index']])
            if song['diff_index'] == 3 and song['fc'] not in ['ap', 'app']:
                song_remain_master.append([song['id'], song['diff_index']])
            if version_han == '舞' and song['diff_index'] == 4 and song['fc'] not in ['ap', 'app']:
                song_remain_re_master.append([song['id'], song['diff_index']])
            song_played.append([song['id'], song['diff_index']])
    for music in Mai.music_list:
        if music.version in payload['version']:
            if [int(music.id), 0] not in song_played:
                song_remain_basic.append([int(music.id), 0])
            if [int(music.id), 1] not in song_played:
                song_remain_advanced.append([int(music.id), 1])
            if [int(music.id), 2] not in song_played:
                song_remain_expert.append([int(music.id), 2])
            if [int(music.id), 3] not in song_played:
                song_remain_master.append([int(music.id), 3])
            if version_han in ['舞', '霸'] and len(music.level) == 5 and [int(music.id), 4] not in song_played:
                song_remain_re_master.append([int(music.id), 4])
    song_remain_basic = sorted(song_remain_basic, key=lambda i: int(i[0]))
    song_remain_advanced = sorted(
        song_remain_advanced, key=lambda i: int(i[0]))
    song_remain_expert = sorted(song_remain_expert, key=lambda i: int(i[0]))
    song_remain_master = sorted(song_remain_master, key=lambda i: int(i[0]))
    song_remain_re_master = sorted(
        song_remain_re_master, key=lambda i: int(i[0]))
    for song in song_remain_basic + song_remain_advanced + song_remain_expert + song_remain_master + song_remain_re_master:
        music: Music | None = Mai.music_list.by_id(str(song[0]))
        assert music is not None
        if music.ds[song[1]] > 13.6:
            song_remain_difficult.append(
                [music.id, music.title, DIFFICULTY_NAME[song[1]], music.ds[song[1]], f'{music.charts[song[1]].stats.fit_diff:.2f}', song[1]])

    appellation = nickname if nickname else '您'

    msg = f'''{appellation}的{version_han}{goal_han}剩余进度如下：
Basic剩余{len(song_remain_basic)}首
Advanced剩余{len(song_remain_advanced)}首
Expert剩余{len(song_remain_expert)}首
Master剩余{len(song_remain_master)}首
'''
    song_remain_count = len(song_remain_basic) + len(song_remain_advanced) + len(
        song_remain_expert) + len(song_remain_master) + len(song_remain_re_master)
    song_remain: list[list] = song_remain_basic + song_remain_advanced + \
        song_remain_expert + song_remain_master + song_remain_re_master
    song_record = [[s['id'], s['diff_index']] for s in data['verlist']]
    if version_han in ['舞', '霸']:
        msg += f'Re:Master剩余{len(song_remain_re_master)}首\n'
    msg += f'总共剩余{song_remain_count}首\n理想状态下共需单刷{ceil(song_remain_count / 3)}局\n约需{song_remain_count * 4 if song_remain_count * 4 < 60 else f"{song_remain_count * 4 // 60}小时{song_remain_count * 4 % 60}"}分钟\n'
    if len(song_remain_difficult) > 0:
        if len(song_remain_difficult) < 60:
            msg += '剩余定数大于13.6的曲目：\n'
            for i, s in enumerate(sorted(song_remain_difficult, key=lambda i: i[3])):
                self_record = ''
                if [int(s[0]), s[-1]] in song_record:
                    record_index = song_record.index([int(s[0]), s[-1]])
                    if goal_han in ['将', '者']:
                        self_record = str(
                            data['verlist'][record_index]['achievements']) + '%'
                    elif goal_han in ['極', '极', '神']:
                        if data['verlist'][record_index]['fc']:
                            self_record = COMBO_RANK[combo_rank.index(
                                data['verlist'][record_index]['fc'])].upper()
                    elif goal_han == '舞舞':
                        if data['verlist'][record_index]['fs']:
                            self_record = SYNC_RANK[sync_rank.index(
                                data['verlist'][record_index]['fs'])].upper()
                # logger.info(repr(s))
                msg += f'No.{i + 1} {s[0]}. {s[1]} {s[2]} {s[3]} {s[4]} {self_record}'.strip() + \
                    '\n'
            if len(song_remain_difficult) > 10:
                msg = MessageSegment.image(image_to_bytesio(text_to_image(msg.strip())))
        else:
            msg += f'还有{len(song_remain_difficult)}大于13.6定数的曲目，加油推分哦！\n'
    elif len(song_remain) > 0:
        for i, s in enumerate(song_remain):
            m: Music = Mai.music_list.by_id(str(s[0]), strict=True)
            ds = m.ds[s[1]]
            song_remain[i].append(ds)
        if len(song_remain) < 60:
            msg += '剩余曲目：\n'
            for i, s in enumerate(sorted(song_remain, key=lambda i: i[2])):
                m = Mai.music_list.by_id(str(s[0]), strict=True)
                self_record = ''
                if [int(s[0]), s[-1]] in song_record:
                    record_index = song_record.index([int(s[0]), s[-1]])
                    if goal_han in ['将', '者']:
                        self_record = str(
                            data['verlist'][record_index]['achievements']) + '%'
                    elif goal_han in ['極', '极', '神']:
                        if data['verlist'][record_index]['fc']:
                            self_record = COMBO_RANK[combo_rank.index(
                                data['verlist'][record_index]['fc'])].upper()
                    elif goal_han == '舞舞':
                        if data['verlist'][record_index]['fs']:
                            self_record = SYNC_RANK[sync_rank.index(
                                data['verlist'][record_index]['fs'])].upper()
                msg += f'No.{i + 1} {m.id}. {m.title} {DIFFICULTY_NAME[s[1]]} {m.ds[s[1]]} {m.charts[s[1]].stats.fit_diff:.2f} {self_record}'.strip(
                ) + '\n'
            if len(song_remain) > 10:
                msg = MessageSegment.image(image_to_bytesio(text_to_image(msg.strip())))
        else:
            msg += '已经没有定数大于13.6的曲目了,加油清谱哦！\n'
    else:
        msg += f'恭喜{appellation}完成{version_han}{goal_han}！'

    return msg
