import random

from nonebot import on_regex
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='选择困难症',
    description='让bot帮你做决定',
    usage='· 选择A还是B还是...'
)


chooseAorB = on_regex(r'^选择(.+还是.+)')


@chooseAorB.handle()
async def chooseAorB_func(group: tuple[str] = RegexGroup()) -> None:
    (message,) = group
    await chooseAorB.finish(f'建议您选择{random.choice(message.split("还是"))}', reply_message=True)
