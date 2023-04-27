from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg

text2sound: type[Matcher] = on_command('文本转语音', aliases={'tts', 'text2sound', 't2s'}, priority=5)


@text2sound.handle()
async def text2sound_func(message: Message = CommandArg()) -> None:
    await text2sound.finish(MessageSegment('tts', {'text': str(message)}))
