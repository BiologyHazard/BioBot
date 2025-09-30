from argparse import Namespace
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from arknights_game_model.game_data import game_data
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_info import (BaseRoom, Control,
                                                                                        Dormitory, Hire)
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_info import \
    HttpsZonaiSklandComApiV1GamePlayerInfo as PlayerInfo
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_info import (Manufacture, Meeting,
                                                                                        Power, Trading, Training)
from arknights_game_model.skland.https_zonai_skland_com_api_v1_search_user import \
    HttpsZonaiSklandComApiV1SearchUser as SearchUser

from .skland import SKLand, SKLandError, api_v1_search_user_url, login_headers


async def 森空岛获取信息(token: str, uid: str | None = None) -> dict[str, Any]:
    skland = SKLand()
    await skland.login_by_token(token)
    characters = await skland.get_binding_list()
    if not characters:
        raise SKLandError('该账号未绑定任何角色。')
    if uid is None:
        uid = characters['defaultUid']  # TODO: 如果没设置默认角色，就没有 defaultUid 这个字段
    elif not any(character['uid'] == uid for character in characters["bindingList"]):
        raise SKLandError('该账号未绑定该角色。')

    return await skland.get_player_info(uid)


async def 森空岛实时数据分析(token: str, uid: str | None = None) -> str:
    门牌号: dict[str, str] = {
        'slot_3': 'B401',
        'slot_5': 'B301',
        'slot_6': 'B302',
        'slot_7': 'B303',
        'slot_9': 'B304',
        'slot_13': 'B305',
        'slot_14': 'B201',
        'slot_15': 'B202',
        'slot_16': 'B203',
        'slot_20': 'B204',
        'slot_23': 'B205',
        'slot_24': 'B101',
        'slot_25': 'B102',
        'slot_26': 'B103',
        'slot_28': 'B104',
        'slot_32': 'B105',
        'slot_34': '控制中枢',
        'slot_36': '1F02',
    }
    obj = await 森空岛获取信息(token, uid)
    # json.dump(obj, open('森空岛数据.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)

    数据: dict[str, Any] = obj['data']
    信息内容: str = (f"Dr. {数据['status']['name'].split('#')[0]}，\n"
                 "根据森空岛的目前采集到的信息推算，罗德岛需要注意的情况向您汇报如下：\n")

    # 理智
    当前理智: float = 数据['status']['ap']['current'] + (数据['currentTs'] - 数据['status']['ap']['lastApAddTime']) / 360
    理智回满剩余时间: float = 数据['status']['ap']['completeRecoveryTime'] - 数据['currentTs']  # 秒
    if 理智回满剩余时间 < 0:
        当前理智 = 数据['status']['ap']['max']
        理智回满剩余时间 = 0
    信息内容 += f"当前理智 {int(当前理智)}"
    if 理智回满剩余时间 == 0:
        信息内容 += "，理智已满。"
    else:
        # 信息内容 += f"，距离理智回满还有 {理智回满剩余时间 // 3600} 小时 {理智回满剩余时间 % 3600 // 60} 分钟。"
        信息内容 += f"，将在 {datetime.fromtimestamp(数据['status']['ap']['completeRecoveryTime']).strftime("%H:%M")}（{理智回满剩余时间 // 3600} 小时 {理智回满剩余时间 % 3600 // 60} 分钟后） 回满"
    信息内容 += "\n"

    # 公开招募刷新
    公开招募刷新次数: int = 数据['building']['hire']['refreshCount']
    公开招募刷新次数填充时间: float = 数据['building']['hire']['completeWorkTime'] - 数据['currentTs']  # 秒
    if 公开招募刷新次数填充时间 < 0:
        公开招募刷新次数 += 1
    if 公开招募刷新次数 > 3:
        公开招募刷新次数 = 3
    信息内容 += f"当前公开招募可刷新 {公开招募刷新次数} 次"
    if 公开招募刷新次数 < 3:
        信息内容 += f"，{公开招募刷新次数填充时间 // 3600} 小时 {公开招募刷新次数填充时间 % 3600 // 60} 分钟后会填充次数"
    信息内容 += "\n"

    # 无人机
    当前无人机: float = (数据['building']['labor']['value']
                    + (数据['building']['labor']['maxValue'] - 数据['building']['labor']['value'])
                    * (数据['currentTs'] - 数据['building']['labor']['lastUpdateTime'])
                    / 数据['building']['labor']['remainSecs'])
    无人机充满剩余时间: float = (数据['building']['labor']['lastUpdateTime']
                        + 数据['building']['labor']['remainSecs'] - 数据['currentTs'])
    if 无人机充满剩余时间 < 0:
        当前无人机 = 数据['building']['labor']['maxValue']
        无人机充满剩余时间 = 0
    信息内容 += f"当前无人机 {int(当前无人机)} 个，{无人机充满剩余时间 // 3600} 小时 {无人机充满剩余时间 % 3600 // 60} 分钟后充满\n"

    # 线索交流
    可赠线索 = 数据['building']['meeting']['clue']['own']
    线索交流剩余时间 = max(0, 数据['building']['meeting']['clue']['shareCompleteTime'] - 数据['currentTs'])
    if 可赠线索 > 5:
        信息内容 += f"可赠线索 {可赠线索} 个\n"
    if 线索交流剩余时间 == 0:
        信息内容 += f"线索交流已完成\n"
    else:
        信息内容 += f"距线索交流结束还有 {线索交流剩余时间 // 3600} 小时 {线索交流剩余时间 % 3600 // 60} 分钟\n"

    # 贸易站缺人
    for 贸易站 in 数据['building']['tradings']:
        if len(贸易站['chars']) < 贸易站['level']:
            信息内容 += f"贸易站 {门牌号[贸易站['slotId']]} 缺人\n"

    # 制造站缺人
    for 制造站 in 数据['building']['manufactures']:
        if len(制造站['chars']) < 制造站['level']:
            信息内容 += f"制造站 {门牌号[制造站['slotId']]} 缺人\n"

    # 干员心情
    疲劳干员名单 = []
    for 疲劳干员 in 数据['building']['tiredChars']:
        if 疲劳干员['charId'] == 'char_285_medic2':
            承曦格雷伊在发电站: bool = any(干员['charId'] == 'char_1027_greyy2' for 房间 in 数据['building']['powers'] for 干员 in 房间['chars'])
            Lancet_2在发电站: bool = any(干员['charId'] == 'char_285_medic2' for 房间 in 数据['building']['powers'] for 干员 in 房间['chars'])
            if 承曦格雷伊在发电站 or not Lancet_2在发电站:
                continue
        疲劳干员名单.append(数据['charInfoMap'][疲劳干员['charId']]['name'])
    if 疲劳干员名单:
        信息内容 += f"疲劳干员：{'、'.join(疲劳干员名单)}\n"

    感知信息 = False
    人间烟火 = False
    for 基建类目 in 数据['building']:
        if 基建类目 in ['powers', 'manufactures', 'tradings', 'dormitories']:
            for 房间 in 数据['building'][基建类目]:
                for 干员 in 房间['chars']:
                    # 跳过心情意义不大的干员
                    if 数据['charInfoMap'][干员['charId']]['name'] in [
                        '纯烬艾雅法拉', '杜林', '夜莺', '凛冬', '刺玫', '流明', '波登可', '桃金娘', '爱丽丝', '四月', '闪灵', '车尔尼', '寒檀', '特米米', '黑', '初雪', '临光', '冰酿', '塑心',
                    ]:
                        continue
                    if 干员['charId'] == 'char_391_rosmon':  # 迷迭香
                        感知信息 = True
                    if 干员['charId'] == 'char_455_nothin':  # 乌有
                        人间烟火 = True
                    if len(数据['building']['powers']) < 3:
                        if 数据['charInfoMap'][干员['charId']]['name'] in ['至简', ]:
                            continue
                    if 数据['building']['hire']['level'] == 1:
                        if 数据['charInfoMap'][干员['charId']]['name'] in ['桑葚', '絮雨', '琴柳', ]:
                            continue
                    干员心情 = 干员['ap'] / 360000
                    if 基建类目 == 'powers':
                        # Lancet-2
                        if 干员['charId'] == 'char_285_medic2':
                            承曦格雷伊在发电站 = False
                            for 房间 in 数据['building']['powers']:
                                for 发电站干员 in 房间['chars']:
                                    if 发电站干员['charId'] == 'char_1027_greyy2':
                                        承曦格雷伊在发电站 = True
                            if 承曦格雷伊在发电站:
                                break
                    if 基建类目 == 'dormitories':
                        # 菲亚梅塔
                        if 干员['charId'] == 'char_300_phenxi':
                            干员心情 = min(干员心情 + (数据['currentTs'] - 干员['lastApAddTime']) / 1800, 24)
                        if 干员心情 > 17:
                            刺玫 = False
                            for 同宿舍干员 in 房间['chars']:
                                if 同宿舍干员['charId'] == 'char_494_vendla':
                                    刺玫 = True
                                    break
                            if 刺玫:
                                信息内容 += f"{数据['charInfoMap'][干员['charId']]['name']}在刺玫的宿舍 {门牌号[房间['slotId']]} 心情达到了 {round(干员心情, 2)}\n"
                            elif 干员心情 > 23.5:
                                信息内容 += f"{数据['charInfoMap'][干员['charId']]['name']}的心情达到了 {round(干员心情, 2)}\n"
                        elif 干员['charId'] == 'char_2023_ling':
                            if 感知信息 and 11.8 < 干员心情 < 18:
                                信息内容 += f"令的心情达到了{round(干员心情, 2)}\n"
                        elif 干员['charId'] == 'char_2015_dusk':
                            if 人间烟火 and 11.8 < 干员心情 < 18:
                                信息内容 += f"夕的心情达到了{round(干员心情, 2)}\n"
                    elif 干员心情 < 1:
                        信息内容 += f"{数据['charInfoMap'][干员['charId']]['name']}的心情仅剩 {round(干员心情, 2)}\n"
        elif 基建类目 in ['control', 'meeting', 'hire']:
            for 干员 in 数据['building'][基建类目]['chars']:
                干员心情 = 干员['ap'] / 360000
                if 干员心情 < 1:
                    信息内容 += f"{数据['charInfoMap'][干员['charId']]['name']}的心情仅剩 {round(干员心情, 2)}\n"
                elif 干员['charId'] == 'char_2023_ling':
                    if 人间烟火 and 11 < 干员心情 < 12.1:
                        信息内容 += f"令的心情仅剩 {round(干员心情, 2)}\n"
                elif 干员['charId'] == 'char_2015_dusk':
                    if 感知信息 and 6 < 干员心情 < 12.1:
                        信息内容 += f"夕的心情仅剩 {round(干员心情, 2)}\n"

    信息内容 += (
        "------------------------------------\n"
        "森空岛信息刷新时间 "
        f"{datetime.fromtimestamp(数据['building']['labor']['lastUpdateTime']).strftime('%Y-%m-%d %H:%M')}\n"
        f"森空岛本次汇报时间 {datetime.fromtimestamp(数据['currentTs']).strftime('%Y-%m-%d %H:%M')}\n")
    return 信息内容


async def 森空岛干员阵容查询(token: str, uid: str | None = None) -> str:
    精英化零阶段等级所需经验: list[int] = [
        0, 100, 217, 351, 502, 670, 855, 1057, 1276, 1512,
        1765, 2035, 2322, 2626, 2947, 3285, 3640, 4012, 4401, 4807,
        5230, 5670, 6127, 6601, 7092, 7600, 8125, 8667, 9226, 9800,
        10389, 10994, 11615, 12252, 12905, 13574, 14259, 14960, 15676, 16400,
        17139, 17888, 18647, 19417, 20200, 21004, 21824, 22660, 23512, 24400,
    ]
    精英化零阶段等级所需龙门币: list[int] = [
        0, 30, 66, 109, 159, 216, 281, 354, 435, 525,
        624, 732, 850, 978, 1116, 1265, 1425, 1607, 1813, 2044,
        2302, 2588, 2903, 3249, 3627, 4038, 4484, 4966, 5486, 6043,
        6638, 7273, 7950, 8670, 9434, 10243, 11099, 12003, 12955, 13947,
        14989, 16075, 17206, 18384, 19613, 20907, 22260, 23673, 25147, 26719,
    ]
    精英化一阶段等级所需经验: list[int] = [
        0, 120, 292, 516, 792, 1120, 1500, 1932, 2416, 2952,
        3540, 4180, 4872, 5616, 6412, 7260, 8160, 9112, 10116, 11172,
        12280, 13440, 14652, 15916, 17232, 18600, 20020, 21492, 23016, 24592,
        26220, 27926, 29710, 31572, 33512, 35530, 37626, 39800, 42052, 44382,
        46790, 49374, 52134, 55070, 58182, 61470, 64934, 68574, 72390, 76382,
        80550, 84894, 89414, 94110, 99000, 104326, 110345, 116657, 123162, 130000,
        137391, 145048, 152871, 160960, 169315, 177936, 186823, 195976, 205395, 215000,
        224951, 235399, 246344, 257786, 269725, 282161, 295094, 308524, 322451, 337000,
    ]
    精英化一阶段等级所需龙门币: list[int] = [
        0, 48, 119, 214, 334, 480, 653, 854, 1085, 1347,
        1640, 1966, 2327, 2723, 3155, 3625, 4133, 4681, 5270, 5901,
        6576, 7295, 8060, 8871, 9730, 10638, 11596, 12606, 13668, 14784,
        15955, 17200, 18522, 19922, 21402, 22964, 24609, 26340, 28157, 30063,
        32059, 34230, 36579, 39110, 41827, 44734, 47834, 51132, 54631, 58336,
        62250, 66377, 70721, 75286, 80093, 85387, 91436, 97849, 104530, 111628,
        119381, 127497, 135875, 144627, 153759, 163277, 173186, 183492, 194201, 205228,
        216761, 228985, 241911, 255550, 269913, 285010, 300853, 317452, 334819, 353122,
    ]
    精英化二阶段等级所需经验: list[int] = [
        0, 191, 494, 909, 1436, 2075, 2826, 3689, 4664, 5751,
        6950, 8261, 9684, 11219, 12866, 14625, 16496, 18479, 20574, 22781,
        25100, 27531, 30074, 32729, 35496, 38375, 41366, 44469, 47684, 51011,
        54450, 58052, 61817, 65745, 69836, 74090, 78507, 83087, 87830, 92736,
        97805, 103037, 108432, 113990, 119711, 125595, 131642, 137852, 144225, 150761,
        157460, 164362, 171467, 178775, 186286, 194000, 201917, 210037, 218360, 226886,
        235615, 244778, 254375, 264406, 274871, 285770, 297103, 308870, 321071, 333800,
        346869, 360616, 375041, 390144, 405925, 422384, 439521, 457336, 475829, 495000,
        514849, 535954, 558315, 581932, 606805, 632934, 660319, 688960, 718857, 750000,
    ]
    精英化二阶段等级所需龙门币: list[int] = [
        0, 76, 200, 373, 598, 877, 1211, 1603, 2054, 2567,
        3144, 3786, 4496, 5276, 6127, 7052, 8053, 9132, 10291, 11531,
        12855, 14265, 15763, 17351, 19031, 20804, 22673, 24640, 26707, 28876,
        31149, 33562, 36118, 38820, 41671, 44674, 47832, 51148, 54625, 58265,
        62072, 66048, 70197, 74521, 79023, 83707, 88575, 93630, 98875, 104313,
        109947, 115814, 121917, 128260, 134847, 141682, 148768, 156108, 163707, 171568,
        179695, 188308, 197416, 207026, 217146, 227783, 238946, 250642, 262880, 275762,
        289105, 303264, 318252, 334080, 350761, 368306, 386728, 406039, 426252, 447378,
        469470, 493192, 518572, 545637, 574415, 604934, 637221, 671304, 707210, 744955,
    ]

    obj = await 森空岛获取信息(token, uid)
    数据: dict[str, Any] = obj['data']
    阵容内容: str = (f"Dr. {数据['status']['name'].split('#')[0]} 博士，\n"
                 "根据从森空岛采集到的信息，罗德岛目前的阵容概况如下：\n")
    总计消耗经验 = 0
    总计消耗龙门币 = 0

    # 计算干员精英化与升级的经验和龙门币花销
    for 干员 in 数据['chars']:
        阵容内容 += 数据['charInfoMap'][干员['charId']]['name']
        精英化阶段 = '零'
        消耗经验 = 0
        消耗龙门币 = 0
        if 干员['evolvePhase'] == 0:
            消耗经验 = 精英化零阶段等级所需经验[干员['level'] - 1]
            消耗龙门币 = 精英化零阶段等级所需龙门币[干员['level'] - 1]
        elif 干员['evolvePhase'] == 1:
            精英化阶段 = '一'
            if 数据['charInfoMap'][干员['charId']]['rarity'] == 2:
                消耗经验 = 16400 + 精英化一阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 23947 + 精英化一阶段等级所需龙门币[干员['level'] - 1]
            elif 数据['charInfoMap'][干员['charId']]['rarity'] == 3:
                消耗经验 = 20200 + 精英化一阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 34613 + 精英化一阶段等级所需龙门币[干员['level'] - 1]
            elif 数据['charInfoMap'][干员['charId']]['rarity'] == 4:
                消耗经验 = 24400 + 精英化一阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 46719 + 精英化一阶段等级所需龙门币[干员['level'] - 1]
            elif 数据['charInfoMap'][干员['charId']]['rarity'] == 5:
                消耗经验 = 24400 + 精英化一阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 56719 + 精英化一阶段等级所需龙门币[干员['level'] - 1]
        elif 干员['evolvePhase'] == 2:
            精英化阶段 = '二'
            if 数据['charInfoMap'][干员['charId']]['rarity'] == 3:
                消耗经验 = 150200 + 精英化二阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 206241 + 精英化二阶段等级所需龙门币[干员['level'] - 1]
            elif 数据['charInfoMap'][干员['charId']]['rarity'] == 4:
                消耗经验 = 239400 + 精英化二阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 371947 + 精英化二阶段等级所需龙门币[干员['level'] - 1]
            elif 数据['charInfoMap'][干员['charId']]['rarity'] == 5:
                消耗经验 = 361400 + 精英化二阶段等级所需经验[干员['level'] - 1]
                消耗龙门币 = 589841 + 精英化二阶段等级所需龙门币[干员['level'] - 1]
        if 干员['charId'] == 'char_1001_amiya2':
            消耗经验 = 0
            消耗龙门币 = 0
            阵容内容 += "-近卫"
        阵容内容 += f"：精英化{精英化阶段}阶段{干员['level']}级"

        # 计算干员模组的龙门币花销
        if 干员['evolvePhase'] == 2:
            for 模组 in 干员['equip']:
                模组是开的 = False
                if 模组['level'] == 3:
                    模组是开的 = True
                    if 数据['charInfoMap'][干员['charId']]['rarity'] == 3:
                        消耗龙门币 += 30000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 4:
                        消耗龙门币 += 60000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 5:
                        消耗龙门币 += 120000
                elif 模组['level'] == 2:
                    模组是开的 = True
                    if 数据['charInfoMap'][干员['charId']]['rarity'] == 3:
                        消耗龙门币 += 25000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 4:
                        消耗龙门币 += 50000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 5:
                        消耗龙门币 += 100000
                elif not 数据['equipmentInfoMap'][模组['id']]['typeIcon'] == 'original' and 模组['id'] == 干员[
                        'defaultEquipId']:
                    模组是开的 = True
                    if 数据['charInfoMap'][干员['charId']]['rarity'] == 3:
                        消耗龙门币 += 20000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 4:
                        消耗龙门币 += 40000
                    elif 数据['charInfoMap'][干员['charId']]['rarity'] == 5:
                        消耗龙门币 += 80000
                if 模组是开的:
                    阵容内容 += f"，模组「{数据['equipmentInfoMap'][模组['id']]['name']}」等级{模组['level']}"

        if not 消耗经验 == 0:
            阵容内容 += f"，消耗龙门币 {消耗龙门币} / 经验 {消耗经验} = {round(消耗龙门币 / 消耗经验, 3)}"
        阵容内容 += '\n'
        总计消耗经验 += 消耗经验
        总计消耗龙门币 += 消耗龙门币
    if 总计消耗经验 != 0:
        阵容内容 += f"\n总计消耗龙门币 {总计消耗龙门币} / 经验 {总计消耗经验} = {round(总计消耗龙门币 / 总计消耗经验, 3)}"
    return 阵容内容


CST = timezone(timedelta(hours=8), name="CST")


门牌号: dict[str, str] = {
    "slot_3": "B401",
    "slot_5": "B301",
    "slot_6": "B302",
    "slot_7": "B303",
    "slot_9": "B304",
    "slot_13": "B305",
    "slot_14": "B201",
    "slot_15": "B202",
    "slot_16": "B203",
    "slot_20": "B204",
    "slot_23": "B205",
    "slot_24": "B101",
    "slot_25": "B102",
    "slot_26": "B103",
    "slot_28": "B104",
    "slot_32": "B105",
    "slot_34": "控制中枢",
    "slot_36": "1F02",
    "slot_41": "B306",
    "slot_44": "B206",
    "slot_47": "B106",
    "slot_49": "B307",
    "slot_50": "B207",
    "slot_51": "B107",
}


def divide(x, y, /, *, positive=float("inf"), negative=float("-inf"), zero=float("nan")) -> float:
    try:
        return x / y
    except ZeroDivisionError:
        if x > 0:
            return positive
        elif x < 0:
            return negative
        else:
            return zero


def format_positive_time_delta(time_delta: timedelta) -> str:
    if time_delta < timedelta(0):
        raise ValueError("time_delta must be non-negative")

    days = time_delta.days
    hours = time_delta.seconds // 3600
    minutes = time_delta.seconds % 3600 // 60

    parts = []
    if days != 0:
        parts.append(f"{days} 天")
    if days != 0 or hours != 0:
        parts.append(f"{hours} 小时")
    parts.append(f"{minutes} 分钟")

    return " ".join(parts)


def format_time(current_timestamp: int,
                target_timestamp: int,
                timezone: timezone | None,
                *,
                prefix_future: str = "将于 ",
                prefix_past: str = "已于 ",
                seconds: bool = False) -> str:
    current_time = datetime.fromtimestamp(current_timestamp, tz=timezone)
    target_time = datetime.fromtimestamp(target_timestamp, tz=timezone)
    time_delta = target_time - current_time

    if current_time.date() == target_time.date():
        format_str = "%H:%M"
    else:
        format_str = "%Y-%m-%d %H:%M"
    if seconds:
        format_str += ":%S"

    if time_delta > timedelta(0):
        return f"{prefix_future}{target_time.strftime(format_str)}（{format_positive_time_delta(time_delta)}后）"
    else:
        return f"{prefix_past}{target_time.strftime(format_str)}（{format_positive_time_delta(-time_delta)}前）"


async def skl_assistant_func(player_info: PlayerInfo, verbose: bool) -> str:
    # 开始构建文本
    alerts: list[str] = []
    lines: list[str] = []

    # contents.append(f"{binding_character["channelName"]}账号 {binding_character["nickName"]}（{binding_character["uid"]}）")
    # contents.append("________________")

    lines.append(f"Dr. {player_info.data.status.name}，")
    lines.append("根据森空岛目前采集到的信息推算，罗德岛需要注意的情况向您汇报如下：")
    lines.append("")

    # 理智
    当前理智 = player_info.data.status.ap.current
    if 当前理智 < player_info.data.status.ap.max:  # 如果理智未满，则考虑信息刷新延迟期间的理智恢复
        当前理智 += (player_info.data.current_ts - player_info.data.status.ap.last_ap_add_time) // 360
        当前理智 = min(当前理智, player_info.data.status.ap.max)

    if 当前理智 >= player_info.data.status.ap.max:
        alerts.append("理智已满！")
    elif 当前理智 >= player_info.data.status.ap.max - 20:
        alerts.append("理智快满了！")

    lines.append(f"当前理智 {当前理智}，{format_time(player_info.data.current_ts, player_info.data.status.ap.complete_recovery_time, CST)}回满。")
    lines.append("")

    # 公开招募刷新
    if player_info.data.building.hire is not None:
        公开招募刷新次数 = player_info.data.building.hire.refresh_count
        if player_info.data.building.hire.complete_work_time > 0 and player_info.data.current_ts >= player_info.data.building.hire.complete_work_time:
            公开招募刷新次数 += 1

        if 公开招募刷新次数 >= 3:
            alerts.append("公开招募刷新次数已满！")
        elif 公开招募刷新次数 >= 2:
            alerts.append("公开招募刷新次数快满了！")

        if player_info.data.building.hire.complete_work_time <= 0:
            lines.append(f"当前公开招募可刷新 {公开招募刷新次数} 次，请及时使用。")
        else:
            lines.append(f"当前公开招募可刷新 {公开招募刷新次数} 次，{format_time(player_info.data.current_ts, player_info.data.building.hire.complete_work_time, CST)}填充次数。")
        lines.append("")

    # 无人机
    当前无人机 = player_info.data.building.labor.value
    if 当前无人机 < player_info.data.building.labor.max_value:  # 如果无人机未满，则考虑信息刷新延迟期间的无人机恢复
        当前无人机 += ((player_info.data.current_ts - player_info.data.building.labor.last_update_time)
                  * divide(player_info.data.building.labor.max_value - player_info.data.building.labor.value,
                           player_info.data.building.labor.remain_secs, positive=0, negative=0, zero=0))
        当前无人机 = min(当前无人机, player_info.data.building.labor.max_value)

    if 当前无人机 >= player_info.data.building.labor.max_value:
        alerts.append("无人机已满！")
    elif 当前无人机 >= player_info.data.building.labor.max_value - 30:
        alerts.append("无人机快满了！")

    无人机充满时间戳 = player_info.data.building.labor.last_update_time + player_info.data.building.labor.remain_secs
    lines.append(f"当前无人机 {int(当前无人机)} 个，{format_time(player_info.data.current_ts, 无人机充满时间戳, CST)}充满。")
    lines.append("")

    # 可赠线索
    if player_info.data.building.meeting is not None:
        可赠线索 = player_info.data.building.meeting.clue.own

        if 可赠线索 >= 10:
            alerts.append("线索自有库已满！")
        elif 可赠线索 >= 9:
            alerts.append("线索自有库快满了！")

        lines.append(f"可赠线索 {可赠线索} 份，{format_time(player_info.data.current_ts, player_info.data.building.meeting.complete_work_time, CST)}刷新。")
        lines.append("")

    # 线索交流剩余时间
    if player_info.data.building.meeting is not None:
        if player_info.data.building.meeting.clue.share_complete_time <= 0:
            if player_info.data.building.meeting.clue.sharing:
                lines.append("线索交流已开启。")
            else:
                lines.append("线索交流未开启。")
        else:
            lines.append(f"线索交流{format_time(player_info.data.current_ts, player_info.data.building.meeting.clue.share_complete_time, CST, seconds=True)}结束。")
        lines.append("")
        # if not player_info.data.building.meeting.clue.sharing:
        #     lines.append("线索交流已完成")
        # else:
        #     lines.append(f"线索交流{format_time(player_info.data.current_ts, player_info.data.building.meeting.clue.share_complete_time, CST)}结束。")

    # 注意力涣散的干员
    if player_info.data.building.tired_chars:
        char_name_list: list[str] = [player_info.data.char_info_map[tired_char.char_id].name
                                     for tired_char in player_info.data.building.tired_chars]
        lines.append(f"注意力涣散的干员：{"、".join(char_name_list)}")
        lines.append("")

    # 菲亚梅塔、令、夕的心情
    菲亚梅塔_id = game_data.characters.by_name("菲亚梅塔").id
    令_id = game_data.characters.by_name("令").id
    夕_id = game_data.characters.by_name("夕").id
    rooms: list[Power | Manufacture | Trading | Dormitory | Meeting | Hire | Control] = []
    rooms.extend(player_info.data.building.powers)
    rooms.extend(player_info.data.building.manufactures)
    rooms.extend(player_info.data.building.tradings)
    rooms.extend(player_info.data.building.dormitories)
    if player_info.data.building.meeting is not None:
        rooms.append(player_info.data.building.meeting)
    if player_info.data.building.hire is not None:
        rooms.append(player_info.data.building.hire)
    # if player_info.data.building.training is not None:
    #     rooms.append(player_info.data.building.training)
    rooms.append(player_info.data.building.control)
    for room in rooms:
        for char in room.chars:
            if char.char_id in {菲亚梅塔_id, 令_id, 夕_id}:
                lines.append(f"{player_info.data.char_info_map[char.char_id].name}的心情为 {char.ap / 360000:.2f}")
    lines.append("")

    # 剿灭作战
    if player_info.data.campaign.reward.current < player_info.data.campaign.reward.total and (datetime.fromtimestamp(player_info.data.current_ts, tz=CST) - timedelta(hours=4)).weekday() >= 5:  # 鹰历周六、周日
        alerts.append("剿灭没打完！")
    lines.append(f"剿灭作战每周报酬：{player_info.data.campaign.reward.current} / {player_info.data.campaign.reward.total}")

    # 详细信息
    if verbose:
        lines.append("")
        lines.append("/- 详细信息 -/")
        lines.append("")

        # 基本信息
        lines.append(f"Dr. {player_info.data.status.name}（{player_info.data.status.uid}），声望 Lv. {player_info.data.status.level}，入职于 {datetime.fromtimestamp(player_info.data.status.register_ts, tz=CST).strftime("%Y-%m-%d %H:%M:%S")}。")

        # 作战进度
        if not player_info.data.status.main_stage_progress:
            作战进度字符串 = "全部完成"
        elif player_info.data.status.main_stage_progress in game_data.raw_data.excel.stage_table.stages:
            作战进度字符串 = game_data.raw_data.excel.stage_table.stages[player_info.data.status.main_stage_progress].code
        else:
            作战进度字符串 = player_info.data.status.main_stage_progress
        lines.append(f"作战进度：{作战进度字符串}")

        # 月卡
        if player_info.data.status.subscription_end <= 0:
            lines.append("未购买月卡")
        else:
            lines.append(f"月卡{format_time(player_info.data.current_ts, player_info.data.status.subscription_end, CST, seconds=True)}到期")

        # storeTs
        lines.append(f"storeTs：{datetime.fromtimestamp(player_info.data.status.store_ts, tz=CST).strftime("%Y-%m-%d %H:%M:%S")}")

        # 最近登录时间
        lines.append(f"最近登录于 {format_time(player_info.data.current_ts, player_info.data.status.last_online_ts, CST, seconds=True, prefix_future="", prefix_past="")}")

        # 蚀刻章
        lines.append(f"蚀刻章总数：{player_info.data.medal.total}")

        # 助战干员
        lines.append(f"助战干员：{"、".join(player_info.data.char_info_map[char.char_id].name for char in player_info.data.assist_chars)}")

        # 已拥有干员
        lines.append(f"已拥有干员：{sum(1 for skl_char in player_info.data.chars if not game_data.characters.by_id(skl_char.char_id).is_patch_char)} / {sum(1 for character in game_data.characters.values() if not character.is_patch_char)}")

        # 已拥有时装
        lines.append(f"已拥有时装：{len(player_info.data.skins)}")

        # 已拥有家具
        lines.append(f"已拥有家具：{player_info.data.building.furniture.total}")

        # 常规任务
        lines.append("")
        lines.append(f"日常任务：{player_info.data.routine.daily.current} / {player_info.data.routine.daily.total}")
        lines.append(f"周常任务：{player_info.data.routine.weekly.current} / {player_info.data.routine.weekly.total}")

        # 基建
        lines.append("")
        lines.append("/- 基建 -/")

        # 控制中枢
        control = player_info.data.building.control
        lines.append("")
        lines.append(f"{control.level} 级控制中枢 {门牌号[control.slot_id]}：")
        for char in control.chars:
            lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 制造站
        for manufacture in player_info.data.building.manufactures:
            lines.append("")
            manufact_formula = game_data.raw_data.excel.building_data.manufact_formulas[manufacture.formula_id]
            item_name = game_data.items.by_id(manufact_formula.item_id).name
            lines.append(f"{manufacture.level} 级制造站 {门牌号[manufacture.slot_id]}（{item_name}）")
            lines.append(f"{format_time(player_info.data.current_ts, manufacture.complete_work_time, CST)}结束工作")
            lines.append(f"容量：{manufacture.weight} / {manufacture.capacity}")
            lines.append(f"已完成 / 剩余：{manufacture.complete} / {manufacture.remain}")
            lines.append(f"效率：{manufacture.speed:.2%}")
            for char in manufacture.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 贸易站
        for trading in player_info.data.building.tradings:
            lines.append("")
            lines.append(f"{trading.level} 级贸易站 {门牌号[trading.slot_id]}（{game_data.raw_data.excel.building_data.trading_order_des_dict[trading.strategy]}）")
            lines.append(f"{format_time(player_info.data.current_ts, trading.complete_work_time, CST)}结束工作")
            lines.append(f"容量：{len(trading.stock)} / {trading.stock_limit}")
            for char in trading.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 发电站
        for power in player_info.data.building.powers:
            lines.append("")
            lines.append(f"{power.level} 级发电站 {门牌号[power.slot_id]}：")
            for char in power.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 会客室
        if player_info.data.building.meeting is not None:
            meeting = player_info.data.building.meeting
            lines.append("")
            lines.append(f"{meeting.level} 级会客室 {门牌号[meeting.slot_id]}：")
            lines.append(f"结束工作时间：{format_time(player_info.data.current_ts, meeting.complete_work_time, CST, seconds=True)}")
            for char in meeting.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 办公室
        if player_info.data.building.hire is not None:
            hire = player_info.data.building.hire
            lines.append("")
            lines.append(f"{hire.level} 级办公室 {门牌号[hire.slot_id]}：")
            lines.append(f"结束工作时间：{format_time(player_info.data.current_ts, hire.complete_work_time, CST, seconds=True)}")
            for char in hire.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已工作 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 训练室
        if player_info.data.building.training is not None:
            training = player_info.data.building.training
            lines.append("")
            lines.append(f"{training.level} 级训练室 {门牌号[training.slot_id]}：")

        # 宿舍
        for dormitory in player_info.data.building.dormitories:
            lines.append("")
            lines.append(f"{dormitory.level} 级宿舍 {门牌号[dormitory.slot_id]}：")
            lines.append(f"氛围：{dormitory.comfort}")
            for char in dormitory.chars:
                lines.append(f"　{player_info.data.char_info_map[char.char_id].name}（心情 {char.ap / 360000:.2f}，已休息 {format_positive_time_delta(timedelta(seconds=char.work_time))}）")

        # 公开招募
        lines.append("")
        lines.append("/- 公开招募 -/")
        lines.append("")
        for index, recruit_item in enumerate(player_info.data.recruit, start=1):
            match recruit_item.state:
                case 0:
                    lines.append(f"公开招募 {index}：未解锁")
                case 1:
                    lines.append(f"公开招募 {index}：未开始")
                case 2:
                    lines.append(f"公开招募 {index}：开始于 {format_time(player_info.data.current_ts, recruit_item.start_ts, CST, prefix_future="", prefix_past="")}，结束于 {format_time(player_info.data.current_ts, recruit_item.finish_ts, CST, prefix_future="", prefix_past="")}")

        # 保全派驻
        lines.append("")
        lines.append("/- 保全派驻 -/")
        lines.append("")
        lines.append(f"保全派驻每周报酬（数据增补仪）：{player_info.data.tower.reward.higher_item.current} / {player_info.data.tower.reward.higher_item.total}")
        lines.append(f"保全派驻每周报酬（数据增补条）：{player_info.data.tower.reward.lower_item.current} / {player_info.data.tower.reward.lower_item.total}")

        # 集成战略
        lines.append("")
        lines.append("/- 集成战略 -/")
        lines.append("")
        for rogue in player_info.data.rogue.records:
            lines.append(f"集成战略 {rogue.rogue_id}")
            lines.append(f"　解锁道具：{rogue.relic_cnt}")
            lines.append(f"　投资系统：{rogue.bank.current} / {rogue.bank.record}")
            lines.append(f"　通关次数：{rogue.clear_time}")
            lines.append(f"　奖励等级：{rogue.bp_level}")
            lines.append(f"　蚀刻章：{rogue.medal.current} / {rogue.medal.total}")

    lines.append("")
    lines.append("________________")
    lines.append(f"森空岛信息刷新时间：{format_time(player_info.data.current_ts, player_info.data.building.labor.last_update_time, CST, prefix_future="", prefix_past="", seconds=True)}")
    lines.append("")
    lines.append("# Generated by BioBot")
    lines.append("# Made by bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    if alerts:
        alerts.append("")
        alerts.append("")
    result = f"{"\n".join(alerts)}{"\n".join(lines)}"

    return result
