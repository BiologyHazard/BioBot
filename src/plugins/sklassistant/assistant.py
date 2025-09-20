from datetime import datetime
from typing import Any

from .skland import SKLand, SKLandError

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


async def 森空岛获取信息(token: str, uid: str | None = None) -> dict[str, Any]:
    skland = SKLand()
    await skland.login_by_token(token)
    characters = await skland.get_binding_list()
    if not characters:
        raise SKLandError('该账号未绑定任何角色。')
    if uid is None:
        uid = characters['defaultUid']
    elif not any(character['uid'] == uid for character in characters["bindingList"]):
        raise SKLandError('该账号未绑定该角色。')

    return await skland.get_player_info(uid)


async def 森空岛实时数据分析(token: str, uid: str | None = None) -> str:
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
        信息内容 += f"，距离理智回满还有 {理智回满剩余时间 // 3600} 小时 {理智回满剩余时间 % 3600 // 60} 分钟。"
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
