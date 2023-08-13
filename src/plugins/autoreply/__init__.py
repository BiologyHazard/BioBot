'''
自动回复

让Bot学习消息并自动回复 | Made by BioHazard

指令列表：
1. #学习 <触发语> <回复语>  # 让bot学习一条自动回复
2. #忘记 <触发语> <回复语>  # 让bot忘记一条自动回复
3. #查询 <触发语>  # 查询<触发语>的全部回复内容（仅限管理员使用该命令）
'''


from nonebot import MatcherGroup, get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import (GROUP_ADMIN, GROUP_OWNER, Bot,
                                         GroupMessageEvent, Message,
                                         MessageEvent, MessageSegment)
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, CommandStart, EventMessage, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from . import autoreply
from .autoreply import ResultCode
from .image import image_to_bytesio, text_to_image

__plugin_meta__: PluginMetadata = PluginMetadata(
    name='自动回复',
    description='让Bot学习消息并自动回复 | Made by BioHazard',
    usage=(
        '· #学习 <触发语> <回复语>  # 让bot学习一条自动回复\n'
        '· #忘记 <触发语> <回复语>  # 让bot忘记一条自动回复\n'
        '· #忘记全部 <触发语>  # 让bot忘记某个触发语的全部回复（仅限管理员使用）\n'
        '· #查询 <触发语>  # 查询<触发语>的全部回复内容（仅限管理员使用）\n'
        '· #查询全部  # 查询本群的全部触发语（仅限管理员使用）\n'
    )
)

bot_nickname: str = 'Bio'

not_group_text: str = '仅限群聊中使用哦~'

learn_success_text: str = f'{bot_nickname}学会啦！'
learn_duplicated_text: str = f'{bot_nickname}学过啦！'
learn_missing_para_text: str = f'{bot_nickname}不知道要学什么呢！'

forget_success_text: str = f'{bot_nickname}忘记啦！'
forget_failed_text: str = f'{bot_nickname}没学过呢！'
forget_empty_message_text: str = f'{bot_nickname}不知道要忘记什么呢！'
forget_missing_para_text: str = f'{bot_nickname}一次只能忘记一条回复哦！'
forget_no_permission_text: str = f'管理员添加的自动回复只能由管理员删除！'

forget_all_no_permission_text: str = '只有管理员才能删除全部回复语！'

query_no_permission_text: str = f'只有管理员可以查询回复语！'


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me


@Rule
async def should_reply(event: GroupMessageEvent, message: Message = EventMessage()) -> bool:
    return await autoreply.get_reply(event.group_id, str(message)) is not None


# autoreply_command_group = MatcherGroup(rule=with_command_start_or_to_me, block=False, priority=5)
autoreply_command_group = MatcherGroup(block=False, priority=5)
learn: type[Matcher] = autoreply_command_group.on_command('学习')
forget: type[Matcher] = autoreply_command_group.on_command('忘记', aliases={'删除'})
forget_all: type[Matcher] = autoreply_command_group.on_command('忘记全部', aliases={'删除全部'})
query: type[Matcher] = autoreply_command_group.on_command('查询')
query_all: type[Matcher] = autoreply_command_group.on_command('查询全部')
reply: type[Matcher] = on_message(rule=should_reply, block=False, priority=15)


driver: Driver = get_driver()


@driver.on_bot_connect
async def on_bot_connect_func(bot: Bot) -> None:
    '''bot连接成功时运行，获取群自动回复列表'''
    logger.info('正在获取自动回复列表...')
    group_list: list[dict] = await bot.get_group_list()
    for group_dict in group_list:
        await autoreply.load_from_file(group_dict['group_id'])


@learn.handle()
async def learn_func(event: MessageEvent, message: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await learn.finish(not_group_text)

    try:
        trigger_message, reply_message = (
            str(message).strip().split(maxsplit=1))
    except ValueError:
        await learn.finish(learn_missing_para_text, at_sender=True)

    if (not trigger_message) or (not reply_message):
        await learn.finish(learn_missing_para_text, at_sender=True)

    result_code: ResultCode = await autoreply.learn_autoreply(event.group_id,
                                                              trigger_message,
                                                              reply_message,
                                                              event.sender,
                                                              event.time)
    if result_code == ResultCode.LEARN_SUCCESS:
        await learn.finish(learn_success_text, at_sender=True)
    elif result_code == ResultCode.LEARN_DUPLICATED:
        await learn.finish(learn_duplicated_text, at_sender=True)


@forget.handle()
async def forget_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await forget.finish(not_group_text)

    if not message:
        await forget.finish(forget_empty_message_text, at_sender=True)

    try:
        trigger_message, reply_message = str(
            message).strip().split(maxsplit=1)
    except ValueError:
        await forget.finish(forget_missing_para_text, at_sender=True)

    if (not trigger_message) or (not reply_message):
        await forget.finish(forget_missing_para_text, at_sender=True)

    sender_permission: bool = await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event)
    result_code: ResultCode = await autoreply.forget_autoreply(event.group_id,
                                                               trigger_message,
                                                               reply_message,
                                                               event.sender,
                                                               sender_permission)
    if result_code == ResultCode.FORGET_SUCCESS:
        await forget.finish(forget_success_text, at_sender=True)
    elif result_code == ResultCode.FORGET_FAILED:
        await forget.finish(forget_failed_text, at_sender=True)
    elif result_code == ResultCode.FORGET_NO_PERMISSION:
        await forget.finish(forget_no_permission_text, at_sender=True)


@forget_all.handle()
async def forget_all_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await forget_all.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await forget_all.finish(forget_all_no_permission_text, at_sender=True)

    trigger_message: str = str(message)
    if not trigger_message:
        await forget_all.finish(forget_empty_message_text, at_sender=True)

    result_code, num = await autoreply.forget_all_autoreply(event.group_id, trigger_message)
    if result_code == ResultCode.FORGET_FAILED:
        await forget_all.finish(forget_failed_text, at_sender=True)
    elif result_code == ResultCode.FORGET_SUCCESS:
        await forget_all.finish(f'成功忘记了{num}条回复语！', at_sender=True)


@query.handle()
async def query_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    query_result: str = await autoreply.query_reply(event.group_id, str(message))

    if len(query_result) < 256:
        await query.finish(Message(query_result), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(query_result))))


@query_all.handle()
async def query_all_func(bot: Bot, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    query_result: str = await autoreply.query_all_reply(event.group_id)

    if len(query_result) < 256:
        await query.finish(Message(query_result), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(query_result))))


@reply.handle()
async def reply_func(event: GroupMessageEvent, message: Message = EventMessage()) -> None:
    reply_message: str | None = await autoreply.get_reply(event.group_id, str(message))
    if reply_message is None:
        return

    await reply.finish(Message(reply_message))
