import random
import re
from re import Match

from nonebot import on_command, on_regex
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg, EventMessage
from nonebot.plugin import PluginMetadata

help_str: str = '''
使用方法：
· roll <上限>
· roll <下限>~<上限>
· 扔x面骰子
· 扔骰子
'''.strip()

__plugin_meta__ = PluginMetadata(
    name='roll',
    description='随机数',
    usage=help_str
)

# roll_regex = r"^roll [0-9]+(-|~)[0-9]+"
# roll = on_regex(roll_regex)
roll = on_command('roll')


@roll.handle()
async def roll_func(message: Message = CommandArg()) -> None:
    split_chars: list[str] = ['~', '-', ' ']
    try:
        for split_char in split_chars:
            if split_char in str(message).strip():
                start, end = map(int, str(message).strip().split(split_char))
                break
        else:
            start, end = 1, int(str(message).strip())
    except Exception:
        await roll.send(help_str)
    else:
        roll_res: int = random.randint(start, end)
        await roll.send(f'roll {start}~{end}: {roll_res}')


dice_regex: str = r'^(扔|投|骰).*?面?(骰|色)子'
num_list: list[str] = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九',
                       '十', '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十']
num_dict: dict[str, int] = {v: k for k, v in enumerate(num_list)}
DEFAULT_DICE: int = 6
dice = on_regex(dice_regex)


@dice.handle()
async def dice_func(message: Message = EventMessage()) -> None:
    def find_end(message: Message) -> int:
        match: Match[str] | None = re.match(dice_regex, str(message).strip())
        assert match is not None
        string: str = match.group()[1:-2]
        if string.endswith('面'):
            string = string[:-1]
        if string:
            if string.isdigit():
                return int(string)
            else:
                assert string in num_dict
                return num_dict[string]
        else:
            return DEFAULT_DICE

    try:
        end: int = find_end(message)
    except Exception:
        await dice.send(help_str)
    else:
        roll_res: int = random.randint(1, end)
        await dice.send(f'roll {1}~{end}: {roll_res}')
