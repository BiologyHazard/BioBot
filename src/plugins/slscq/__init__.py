from pathlib import Path

from nonebot import on_command, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .slscq import Slscq

__plugin_meta__ = PluginMetadata(
    name='申论生成器',
    description='生成申论文章',
    usage=(
        "· (申论生成器|slscq|生成申论|scsl) <申论主题> <字数下限>"
    ),
    type='application',
)

sl = on_command('申论生成器', aliases={'生成申论', 'slscq', 'scsl'}, priority=5, block=False)
slscq = Slscq(Path(__file__).parent / 'data.json')


@sl.handle()
async def sl_func(message: Message = CommandArg()):
    logger.info(message)
    try:
        args: list[str] = message.extract_plain_text().split()
        if len(args) == 1:
            topic, length = args[0], 500
        elif len(args) == 2:
            topic, length = args[0], int(args[1])
        else:
            raise ValueError
    except Exception:
        await sl.finish(f'使用方法：(申论生成器|slscq|生成申论|scsl) <申论主题> <字数下限>')

    if length > 1000:
        await sl.finish('字数下限不能超过1000')

    text = slscq.gen_text(topic, length)
    await sl.finish(text)
