# ruff: noqa: E402
"""
自动回复

让Bot学习消息并自动回复 | Made by BioHazard

指令列表：
1. #学习 <触发语> <回复语>  # 让bot学习一条自动回复
2. #忘记 <触发语> <回复语>  # 让bot忘记一条自动回复
3. #查询 <触发语>  # 查询<触发语>的全部回复内容（仅限管理员使用该命令）
"""

import random
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from nonebot import MatcherGroup, get_driver, on_message, require

require("nonebot_plugin_orm")

from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, CommandStart, EventMessage, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot_plugin_orm import async_scoped_session
from sqlalchemy import delete, func, select

from .config import plugin_config
from .image import image_to_bytesio, text_to_image
from .models import AutoReply

__plugin_meta__: PluginMetadata = PluginMetadata(
    name="自动回复",
    description="让Bot学习消息并自动回复 | Made by BioHazard",
    usage=(
        "· #学习 <触发语> <回复语>  # 让bot学习一条自动回复\n"
        "· #忘记 <触发语> <回复语>  # 让bot忘记一条自动回复\n"
        "· #忘记全部 <触发语>  # 让bot忘记某个触发语的全部回复（仅限管理员使用）\n"
        "· #查询 <触发语>  # 查询<触发语>的全部回复内容（仅限管理员使用）\n"
        "· #查询全部  # 查询本群的全部触发语（仅限管理员使用）\n"
    ),
)

bot_nickname: str = "苏茜"

not_group_text: str = "仅限群聊中使用哦~"

learn_success_text: str = f"{bot_nickname}学会啦！"
learn_duplicated_text: str = f"{bot_nickname}学过啦！"
learn_missing_parameter_text: str = f"{bot_nickname}不知道要学什么呢！"

forget_success_text: str = f"{bot_nickname}忘记啦！"
forget_failed_text: str = f"{bot_nickname}没学过呢！"
forget_empty_message_text: str = f"{bot_nickname}不知道要忘记什么呢！"
forget_missing_para_text: str = f"{bot_nickname}一次只能忘记一条回复哦！"
forget_no_permission_text: str = f"管理员添加的自动回复只能由管理员删除！"

forget_all_no_permission_text: str = "只有管理员才能删除全部回复语！"

query_no_permission_text: str = f"只有管理员可以查询回复语！"
query_failed_text = f"{bot_nickname}没学过呢！"


def receive_message_preprocess(message: Message) -> Message:
    """预处理 message, 下载所有图片, 对于 `CQ:image` 仅保留 `file` 字段"""
    for message_segment in message:
        if message_segment.type == "image":
            message_segment.data = {"file": message_segment.data["file"]}
    return message


def send_message_preprocess(message: Message) -> Message:
    """发送消息时预处理 message, 把 `CQ:image` 的 `file` 字段扩展为本地路径"""
    for message_segment in message:
        if message_segment.type == "image":
            message_segment.data = {
                "file": (plugin_config.image_folder / message_segment.data["file"])
                .resolve()
                .as_uri()
            }
    return message


async def download_images_from_message(message: Message, bot: Bot) -> None:
    for message_segment in message:
        if message_segment.type == "image":
            image_info: dict[str, Any] = await bot.get_image(
                file=message_segment.data["file"]
            )
            path = Path(image_info["file"])
            destination_path = plugin_config.image_folder / image_info["file_name"]
            shutil.copy2(path, destination_path)


driver: Driver = get_driver()


@Rule
async def with_command_start_or_to_me(
    command_start: str = CommandStart(), to_me: bool = EventToMe()
) -> bool:
    return bool(command_start) or to_me


@Rule
async def should_reply(
    session: async_scoped_session,
    event: GroupMessageEvent,
    state: T_State,
    message: Annotated[Message, EventMessage()],
) -> bool:
    message_str = str(message).strip()
    message_str = str(receive_message_preprocess(Message(message_str)))

    statement = select(AutoReply).where(
        AutoReply.group_id == str(event.group_id), AutoReply.trigger == message_str
    )
    replies = (await session.scalars(statement)).all()
    if replies:
        state["replies"] = replies
        return True
    return False


autoreply_command_group = MatcherGroup(
    rule=with_command_start_or_to_me, block=False, priority=5
)
# autoreply_command_group = MatcherGroup(block=False, priority=5)
learn: type[Matcher] = autoreply_command_group.on_command("学习", force_whitespace=True)
forget: type[Matcher] = autoreply_command_group.on_command(
    "忘记", aliases={"删除"}, force_whitespace=True
)
forget_all: type[Matcher] = autoreply_command_group.on_command(
    "忘记全部", aliases={"删除全部"}, force_whitespace=True
)
query: type[Matcher] = autoreply_command_group.on_command("查询", force_whitespace=True)
query_all: type[Matcher] = autoreply_command_group.on_command(
    "查询全部", force_whitespace=True
)
reply: type[Matcher] = on_message(rule=should_reply, block=False, priority=15)


@driver.on_startup
async def on_startup_func() -> None:
    from .migrate_data import migrate

    await migrate()


# @driver.on_bot_connect
# async def on_bot_connect_func(bot: Bot) -> None:
#     '''bot连接成功时运行，获取群自动回复列表'''
#     logger.info('正在获取自动回复列表...')
#     group_list: list[dict] = await bot.get_group_list()
#     for group_dict in group_list:
#         await load_from_file(group_dict['group_id'])


@learn.handle()
async def learn_func(
    bot: Bot,
    event: MessageEvent,
    session: async_scoped_session,
    message: Annotated[Message, CommandArg()],
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await learn.finish(not_group_text)

    try:
        trigger_message_str, reply_message_str = str(message).strip().split(maxsplit=1)
    except Exception:
        await learn.finish(learn_missing_parameter_text, at_sender=True)

    if (not trigger_message_str) or (not reply_message_str):
        await learn.finish(learn_missing_parameter_text, at_sender=True)

    trigger_message = receive_message_preprocess(Message(trigger_message_str))
    reply_message = receive_message_preprocess(Message(reply_message_str))
    await download_images_from_message(reply_message, bot)

    trigger_str = str(trigger_message)
    reply_str = str(reply_message)

    statement = select(AutoReply).where(
        AutoReply.group_id == str(event.group_id),
        AutoReply.trigger == trigger_str,
        AutoReply.reply == reply_str,
    )
    existing = await session.scalar(statement)
    if existing:
        await learn.finish(learn_duplicated_text, at_sender=True)

    new_reply = AutoReply(
        group_id=str(event.group_id),
        trigger=trigger_str,
        reply=reply_str,
        user_id=str(event.user_id),
        nickname=event.sender.nickname,
        card=event.sender.card,
        role=event.sender.role,
        created_at=event.time,
    )
    session.add(new_reply)
    await session.commit()

    await learn.finish(learn_success_text, at_sender=True)


@forget.handle()
async def forget_func(
    bot: Bot,
    event: MessageEvent,
    session: async_scoped_session,
    message: Annotated[Message, CommandArg()],
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await forget.finish(not_group_text)

    if not message:
        await forget.finish(forget_empty_message_text, at_sender=True)

    try:
        trigger_message_str, reply_message_str = str(message).strip().split(maxsplit=1)
    except ValueError:
        await forget.finish(forget_missing_para_text, at_sender=True)

    if (not trigger_message_str) or (not reply_message_str):
        await forget.finish(forget_missing_para_text, at_sender=True)

    trigger_str = str(receive_message_preprocess(Message(trigger_message_str)))
    reply_str = str(receive_message_preprocess(Message(reply_message_str)))

    statement = select(AutoReply).where(
        AutoReply.group_id == str(event.group_id),
        AutoReply.trigger == trigger_str,
        AutoReply.reply == reply_str,
    )
    target = await session.scalar(statement)
    if not target:
        await forget.finish(forget_failed_text, at_sender=True)

    sender_permission: bool = await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event)
    if (not sender_permission) and (target.role in ["owner", "admin"]):
        await forget.finish(forget_no_permission_text, at_sender=True)

    await session.delete(target)
    await session.commit()

    await forget.finish(forget_success_text, at_sender=True)


@forget_all.handle()
async def forget_all_func(
    bot: Bot,
    event: MessageEvent,
    session: async_scoped_session,
    message: Annotated[Message, CommandArg()],
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await forget_all.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await forget_all.finish(forget_all_no_permission_text, at_sender=True)

    trigger_message_str: str = str(message).strip()
    if not trigger_message_str:
        await forget_all.finish(forget_empty_message_text, at_sender=True)

    trigger_str = str(receive_message_preprocess(Message(trigger_message_str)))

    statement = delete(AutoReply).where(
        AutoReply.group_id == str(event.group_id), AutoReply.trigger == trigger_str
    )
    result = await session.execute(statement)
    num = result.rowcount  # type: ignore
    await session.commit()

    if num == 0:
        await forget_all.finish(forget_failed_text, at_sender=True)

    await forget_all.finish(f"成功忘记了 {num} 条回复语！", at_sender=True)


@query.handle()
async def query_func(
    bot: Bot,
    event: MessageEvent,
    session: async_scoped_session,
    message: Annotated[Message, CommandArg()],
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    trigger_str = str(receive_message_preprocess(Message(message))).strip()

    statement = select(AutoReply).where(
        AutoReply.group_id == str(event.group_id), AutoReply.trigger == trigger_str
    )
    replies = (await session.scalars(statement)).all()
    if not replies:
        await query.finish(query_failed_text, at_sender=True)

    text = f"{message} 的回复语（共 {len(replies)} 条）：\n" + "\n".join(
        f"{i}. {r.reply}  # 由 {r.card or r.nickname} ({r.user_id}) 于 {datetime.fromtimestamp(r.created_at).astimezone()} 设置"
        for i, r in enumerate(replies, start=1)
    )

    if len(text) < 256:
        await query.finish(Message(text), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(text))))


@query_all.handle()
async def query_all_func(
    bot: Bot, event: MessageEvent, session: async_scoped_session
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    statement = (
        select(AutoReply.trigger, func.count(AutoReply.id))
        .where(AutoReply.group_id == str(event.group_id))
        .group_by(AutoReply.trigger)
    )
    results = (await session.execute(statement)).all()

    if not results:
        await query.finish("本群未设置自动回复！", at_sender=True)

    text = f"本群的全部回复语（共{len(results)}条）\n" + "\n".join(
        f"{i}. {trigger}  # 共 {count} 条"
        for i, (trigger, count) in enumerate(results, start=1)
    )

    if len(text) < 256:
        await query.finish(Message(text), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(text))))


@reply.handle()
async def reply_func(
    session: async_scoped_session,
    state: T_State,
) -> None:
    replies: list[AutoReply] = state["replies"]
    if not replies:
        return

    # 计算权重：untriggered_count + 1
    weights = [r.untriggered_count + 1 for r in replies]

    # 使用 random.choices 进行加权随机抽取
    selected_reply = random.choices(replies, weights=weights, k=1)[0]
    selected_id = selected_reply.id
    reply_content = selected_reply.reply

    # 更新数据库中的 untriggered_count
    for r in replies:
        # 使用 merge 将对象合并到当前 session，避免 session 冲突
        # load=False 表示不从数据库重新加载，而是直接更新
        merged_r = await session.merge(r, load=False)
        if merged_r.id == selected_id:
            merged_r.untriggered_count = 0
        else:
            merged_r.untriggered_count += 1

    await session.commit()

    reply_message = send_message_preprocess(Message(reply_content))
    await reply.finish(reply_message)
