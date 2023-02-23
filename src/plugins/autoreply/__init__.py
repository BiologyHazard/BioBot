from nonebot import get_driver, logger, on_command, on_message, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event, Message
from nonebot.internal.driver import Driver
from nonebot.params import CommandArg, EventMessage

from .autoreply import (ResultCode, _load_from_file, forget_autoreply,
                        get_reply, learn_autoreply, query_reply)

driver: Driver = get_driver()


@driver.on_bot_connect
async def on_bot_connect_func(bot: Bot) -> None:
    group_list: list[dict] = await bot.get_group_list()
    # logger.trace(repr(group_list))
    for group_dict in group_list:
        await _load_from_file(group_dict['group_id'])


bot_nickname: str = 'Bio'

not_group_text: str = '仅限群聊中使用哦~'

learn_success_text: str = f'{bot_nickname}学会啦！'
learn_duplicated_text: str = f'{bot_nickname}学过啦！'
learn_missing_para_text: str = f'{bot_nickname}不知道要学什么呢！'

forget_success_text: str = f'{bot_nickname}忘记啦！'
forget_failed_text: str = f'{bot_nickname}没学过呢！'
forget_missing_para_text: str = f'{bot_nickname}一次只能忘记一条回复哦！'
forget_no_permission_text: str = f'管理员添加的自动回复只能由管理员删除！'

query_failed_text: str = f'不存在该触发词！'
query_no_permission_text: str = f'只有管理员可以查询回复语！'


learn = on_command('#学习 ')
forget = on_command('#忘记 ')
reply = on_message(block=False)
query = on_command('#查询 ')


@learn.handle()
async def learn_func(bot: Bot, event: Event, message: Message = CommandArg()):
    # logger.trace(repr(bot))
    # logger.trace(repr(event))
    # logger.trace(repr(message))
    if event.message_type != 'group':
        await learn.finish(not_group_text)

    try:
        trigger_message, reply_message = (
            str(message).strip().split(maxsplit=1))
    except ValueError:
        await learn.finish(learn_missing_para_text, at_sender=True)

    if (not trigger_message) or (not reply_message):
        await learn.finish(learn_missing_para_text, at_sender=True)

    # logger.trace(trigger_msg)
    # logger.trace(reply_msg)
    # await learn.send(str(group_id))
    # await learn.send(Message(trigger_msg))
    # await learn.send(Message(reply_msg))

    result_code: int = await learn_autoreply(event.group_id, trigger_message, reply_message, event.sender)
    if result_code == ResultCode.LEARN_SUCCESS:
        await learn.finish(learn_success_text, at_sender=True)
    elif result_code == ResultCode.LEARN_DUPLICATED:
        await learn.finish(learn_duplicated_text, at_sender=True)


@forget.handle()
async def forget_func(bot: Bot, event: Event, message: Message = CommandArg()) -> None:
    if event.message_type != 'group':
        await forget.finish(not_group_text)

    try:
        trigger_message, reply_message = str(
            message).strip().split(maxsplit=1)
    except ValueError:
        await forget.finish(forget_missing_para_text, at_sender=True)

    if (not trigger_message) or (not reply_message):
        await forget.finish(forget_missing_para_text, at_sender=True)

    result_code: int = await forget_autoreply(event.group_id, trigger_message, reply_message, event.sender)
    if result_code == ResultCode.FORGET_SUCCESS:
        await forget.finish(forget_success_text, at_sender=True)
    elif result_code == ResultCode.FORGET_FAILED:
        await forget.finish(forget_failed_text, at_sender=True)
    elif result_code == ResultCode.FORGET_NO_PERMISSION:
        await forget.finish(forget_no_permission_text, at_sender=True)


@reply.handle()
async def reply_func(bot: Bot, event: Event, message: Message = EventMessage()) -> None:
    if event.message_type != 'group':
        return

    # async with aiofiles.open('messages.txt', 'a', encoding='utf-8') as fp:
    #     await fp.write(
    #         f'{group_id} | {event.get_user_id()} : {str(message)}\n')
    reply_message: str | None = await get_reply(event.group_id, str(message))
    if reply_message:
        await reply.finish(Message(reply_message))


@query.handle()
async def query_func(bot: Bot, event: Event, message: Message = CommandArg()) -> None:
    if event.message_type != 'group':
        await query.finish(not_group_text)

    if event.sender.role not in ['admin', 'owner']:
        await query.finish(query_no_permission_text, at_sender=True)

    num, query_result = await query_reply(event.group_id, message)
    if num == 0:
        await query.finish(query_failed_text, at_sender=True)

    await query.finish(Message(f'{message}的回复语（共{num}条）：\n{query_result}'), at_sender=True)
