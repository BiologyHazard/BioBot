"""
自动回复

让Bot学习消息并自动回复 | Made by BioHazard

指令列表：
1. #学习 <触发语> <回复语>  # 让bot学习一条自动回复
2. #忘记 <触发语> <回复语>  # 让bot忘记一条自动回复
3. #查询 <触发语>  # 查询<触发语>的全部回复内容（仅限管理员使用该命令）
"""

import json
import random
import shutil
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypedDict

import aiofiles
from nonebot import MatcherGroup, get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.event import Sender
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, CommandStart, EventMessage, EventToMe
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .config import plugin_config
from .image import image_to_bytesio, text_to_image

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


class sender_dict_T(TypedDict):
    qqid: int | None
    nickname: str | None
    card: str | None
    role: str | None
    time: int


type ReplyDictT = dict[str, sender_dict_T]
type GroupDictT = defaultdict[str, ReplyDictT]
type MainDictT = defaultdict[int, GroupDictT]

main_dict: MainDictT = defaultdict(lambda: defaultdict(dict))
not_reply_count: defaultdict[int, defaultdict[str, defaultdict[str, int]]] = (
    defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
)


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


def get_sender_info(sender: Sender, timestamp: int) -> sender_dict_T:
    return sender_dict_T(
        qqid=sender.user_id,
        nickname=sender.nickname,
        card=sender.card,
        role=sender.role,
        time=timestamp,
    )


async def load_from_file(group_id: int) -> None:
    if group_id in main_dict:
        return

    file_path: Path = plugin_config.data_folder / f"{group_id}.json"
    if file_path.is_file():
        async with aiofiles.open(file_path, "r", encoding="utf-8") as fp:
            group_dict = json.loads(await fp.read())
        main_dict[group_id] = defaultdict(dict, group_dict)


async def save_to_file(group_id: int) -> None:
    file_path: Path = plugin_config.data_folder / f"{group_id}.json"
    async with aiofiles.open(file_path, "w", encoding="utf-8") as fp:
        await fp.write(json.dumps(main_dict[group_id], ensure_ascii=False))


@Rule
async def with_command_start_or_to_me(
    command_start: str = CommandStart(), to_me: bool = EventToMe()
) -> bool:
    return bool(command_start) or to_me


@Rule
async def should_reply(
    event: GroupMessageEvent, message: Message = EventMessage()
) -> bool:
    await load_from_file(event.group_id)
    message_str = str(message).strip()
    message_str = str(receive_message_preprocess(Message(message_str)))
    return message_str in main_dict[event.group_id]


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


driver: Driver = get_driver()


# @driver.on_bot_connect
# async def on_bot_connect_func(bot: Bot) -> None:
#     '''bot连接成功时运行，获取群自动回复列表'''
#     logger.info('正在获取自动回复列表...')
#     group_list: list[dict] = await bot.get_group_list()
#     for group_dict in group_list:
#         await load_from_file(group_dict['group_id'])


@learn.handle()
async def learn_func(
    bot: Bot, event: MessageEvent, message: Message = CommandArg()
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

    await load_from_file(event.group_id)
    reply_messages_dict: ReplyDictT = main_dict[event.group_id][str(trigger_message)]
    if str(reply_message) in reply_messages_dict:
        await learn.finish(learn_duplicated_text, at_sender=True)

    reply_messages_dict[str(reply_message)] = get_sender_info(event.sender, event.time)
    await save_to_file(event.group_id)

    await learn.finish(learn_success_text, at_sender=True)


@forget.handle()
async def forget_func(
    bot: Bot, event: MessageEvent, message: Message = CommandArg()
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

    trigger_message_str = str(receive_message_preprocess(Message(trigger_message_str)))
    reply_message = receive_message_preprocess(Message(reply_message_str))
    reply_message_str = str(reply_message)

    await load_from_file(event.group_id)
    if trigger_message_str not in main_dict[event.group_id]:
        await forget.finish(forget_failed_text, at_sender=True)

    reply_message_dict: ReplyDictT = main_dict[event.group_id][trigger_message_str]
    if str(reply_message) not in reply_message_dict:
        await forget.finish(forget_failed_text, at_sender=True)

    sender_permission: bool = await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event)
    if (not sender_permission) and (
        reply_message_dict[reply_message_str]["role"] in ["owner", "admin"]
    ):
        await forget.finish(forget_no_permission_text, at_sender=True)

    del reply_message_dict[reply_message_str]
    if not reply_message_dict:
        del main_dict[event.group_id][trigger_message_str]
    await save_to_file(event.group_id)

    await forget.finish(forget_success_text, at_sender=True)


@forget_all.handle()
async def forget_all_func(
    bot: Bot, event: MessageEvent, message: Message = CommandArg()
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await forget_all.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await forget_all.finish(forget_all_no_permission_text, at_sender=True)

    trigger_message_str: str = str(message).strip()
    if not trigger_message_str:
        await forget_all.finish(forget_empty_message_text, at_sender=True)

    trigger_message_str = str(receive_message_preprocess(Message(trigger_message_str)))
    await load_from_file(event.group_id)
    if trigger_message_str not in main_dict[event.group_id]:
        await forget_all.finish(forget_failed_text, at_sender=True)

    num = len(main_dict[event.group_id][trigger_message_str])
    del main_dict[event.group_id][trigger_message_str]
    await save_to_file(event.group_id)

    await forget_all.finish(f"成功忘记了 {num} 条回复语！", at_sender=True)


@query.handle()
async def query_func(
    bot: Bot, event: MessageEvent, message: Message = CommandArg()
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    message_str = str(receive_message_preprocess(Message(message))).strip()

    await load_from_file(event.group_id)
    if message_str not in main_dict[event.group_id]:
        await query.finish(query_failed_text, at_sender=True)

    text = (
        f"{message} 的回复语（共 {len(main_dict[event.group_id][message_str])} 条）：\n"
        + "\n".join(
            f"{i}. {reply_message_str}  # 由 {sender_info['card'] or sender_info['nickname']} ({sender_info['qqid']}) 于 {datetime.fromtimestamp(sender_info['time']).strftime('%Y-%m-%d %H:%M:%S')} 设置"
            for i, (reply_message_str, sender_info) in enumerate(
                main_dict[event.group_id][message_str].items(), start=1
            )
        )
    )

    if len(text) < 256:
        await query.finish(Message(text), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(text))))


@query_all.handle()
async def query_all_func(bot: Bot, event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await query.finish(not_group_text)

    if not await (GROUP_OWNER | GROUP_ADMIN | SUPERUSER)(bot, event):
        await query.finish(query_no_permission_text, at_sender=True)

    await load_from_file(event.group_id)
    if not main_dict[event.group_id]:
        await query.finish("本群未设置自动回复！", at_sender=True)

    text = f"本群的全部回复语（共{len(main_dict[event.group_id])}条）\n" + "\n".join(
        f"{i}. {trigger_message_str}  # 共 {len(main_dict[event.group_id][trigger_message_str])} 条"
        for i, trigger_message_str in enumerate(main_dict[event.group_id], start=1)
    )

    if len(text) < 256:
        await query.finish(Message(text), at_sender=True)
    else:
        await query.finish(MessageSegment.image(image_to_bytesio(text_to_image(text))))


@reply.handle()
async def reply_func(
    event: GroupMessageEvent, message: Message = EventMessage()
) -> None:
    await load_from_file(event.group_id)
    message_str = str(message).strip()
    message_str = str(receive_message_preprocess(Message(message_str)))
    for reply_message_str in main_dict[event.group_id][message_str]:
        not_reply_count[event.group_id][message_str][reply_message_str] += 1
    reply_message_str = random.sample(
        list(main_dict[event.group_id][message_str].keys()),
        1,
        counts=[
            not_reply_count[event.group_id][message_str][reply_message_str] + 1
            for reply_message_str in main_dict[event.group_id][message_str]
        ],
    )[0]
    not_reply_count[event.group_id][message_str][reply_message_str] = 0
    reply_message = send_message_preprocess(Message(reply_message_str))
    await reply.finish(reply_message)
