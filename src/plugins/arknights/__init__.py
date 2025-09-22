import sys

sys.path.append("src/arknights-game-model")  # NOQA

import nonebot
from arknights_game_model.game_data import game_data
from arknights_game_model.utils import escape_description
from nonebot import on_regex, MatcherGroup
from nonebot.params import RegexGroup

from .config import plugin_config

driver = nonebot.get_driver()


@driver.on_startup
def on_startup_func() -> None:
    game_data.load_data(gamedata_folder=plugin_config.arknights_gamedata_folder,
                        online_time_path=plugin_config.arknights_online_time_path,
                        yituliu_item_value_path=plugin_config.arknights_yituliu_item_value_path)


arknights_matcher_group = MatcherGroup(priority=5, block=False)
base_skill = arknights_matcher_group.on_regex(r"(.+)基建技能|基建技能\s*(.+)")
evolve_cost = arknights_matcher_group.on_regex(r"(.+)(?:满练|拉满)消耗")
# all_evolve_cost = arknights_matcher_group.on_regex(r"全(?:干员)?(?:满练|拉满)消耗")


@base_skill.handle()
async def base_skill_func(regex_group: tuple[str, None] | tuple[None, str] = RegexGroup()):
    character_str = regex_group[0] if regex_group[0] is not None else regex_group[1]

    try:
        character = game_data.characters.by_name(character_str)
    except KeyError:
        await base_skill.finish(f"未找到名称为“{character_str}”的干员")

    lines: list[str] = []
    lines.append(f"干员 {character.id}（{character.name}）")
    lines.append("________________")
    lines.append("")

    for skill_num, buff_char_item in enumerate(game_data.raw_data.excel.building_data.chars[character.id].buff_char, start=1):
        if buff_char_item.buff_data:
            lines.append(f"/- 基建技能 {skill_num} -/")
            lines.append("")

            for buff_data_item in buff_char_item.buff_data:
                skill_id = buff_data_item.buff_id
                skill = game_data.raw_data.excel.building_data.buffs[skill_id]
                lines.append(f"【{skill.buff_name}】精英阶段 {buff_data_item.cond.phase} 的 {buff_data_item.cond.level} 级解锁")
                lines.append(escape_description(skill.description))
                lines.append("")

    lines.append("________________")
    lines.append("# 来自 bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    await base_skill.finish("\n".join(lines))


@evolve_cost.handle()
async def evolve_cost_func(regex_group: tuple[str] = RegexGroup()):
    character_str = regex_group[0]

    lines: list[str] = []

    if character_str.rstrip("干员") in ("全", "所有", "全部"):
        item_info_list = game_data.characters.全干员拉满消耗().combine().sort_by_sort_id()

        lines.append("/- 全干员拉满消耗 -/")
        lines.append("")

    else:
        try:
            character = game_data.characters.by_name(character_str)
        except KeyError:
            await evolve_cost.finish(f"未找到名称为“{character_str}”的干员")

        item_info_list = character.养成消耗().combine().sort_by_sort_id()

        lines.append(f"干员 {character.id}（{character.name}）")
        lines.append("________________")
        lines.append("")
        lines.append("/- 拉满消耗 -/")
        lines.append("")

    yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

    lines.extend(str(item_info_list).split())

    lines.append("")
    lines.append(f"相当于 {yituliu_item_value:.2f} 理智")
    lines.append("")
    lines.append("________________")
    lines.append("# 物品价值数据来自 明日方舟一图流 - 物品价值表")
    lines.append("https://ark.yituliu.cn/material/value")
    lines.append("")
    lines.append("# 来自 bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    await evolve_cost.finish("\n".join(lines))


# @all_evolve_cost.handle()
# async def all_evolve_cost_func():
#     lines: list[str] = []
#     lines.append("/- 全干员拉满消耗 -/")
#     lines.append("")

#     item_info_list = game_data.characters.全干员拉满消耗().
#     yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

#     lines.extend(str(item_info_list).split())

#     lines.append("")
#     lines.append(f"相当于 {yituliu_item_value:.2f} 理智")
#     lines.append("# 物品价值数据来自 明日方舟一图流 - 物品价值表")
#     lines.append("# https://ark.yituliu.cn/material/value")

#     await all_evolve_cost.finish("\n".join(lines).rstrip())
