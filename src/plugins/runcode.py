from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

run_code = on_command('runcode', permission=SUPERUSER, priority=1, block=False)


@run_code.handle()
async def run_code_func(message: Message = CommandArg()) -> None:
    command: str = message.extract_plain_text()
    try:
        result = eval(command)
    except Exception as e:
        await run_code.finish(repr(e))
    else:
        await run_code.finish(repr(result))
