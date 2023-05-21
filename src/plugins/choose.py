import random

from nonebot import on_regex
from nonebot.params import RegexGroup

chooseAorB = on_regex(r'^选择(.+还是.+)')


@chooseAorB.handle()
async def chooseAorB_func(group: tuple[str] = RegexGroup()) -> None:
    (message,) = group
    await chooseAorB.finish(f'建议您选择{random.choice(message.split("还是"))}')
