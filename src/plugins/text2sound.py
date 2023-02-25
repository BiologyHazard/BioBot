from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg, CommandStart, EventToMe


text2sound: type[Matcher] = on_command('文本转语音',
                                       aliases={'tts', 'text2sound', 't2s'})


@text2sound.handle()
async def restart_func(bot: Bot, event: Event, message: Message = CommandArg()) -> None:
    await text2sound.send(MessageSegment('tts', {'text': str(message)}))
