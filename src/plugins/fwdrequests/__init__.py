import asyncio
from textwrap import dedent
from typing import Any

from nonebot import logger, on_command, on_fullmatch, on_request
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent, GroupMessageEvent, GroupRequestEvent,
                                         Message, MessageEvent, PrivateMessageEvent, RequestEvent)
from nonebot.params import CommandArg, Fullmatch, RawCommand
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from .config import forward_to_expanded

__plugin_meta__: PluginMetadata = PluginMetadata(
    name='转发加好友加群请求',
    description='',
    usage='''仅管理员使用，无触发命令''',
)


def permission_checker(event: MessageEvent) -> bool:
    return event.sender.user_id in forward_to_expanded or getattr(event, 'group_id', None) in forward_to_expanded


request_matcher = on_request()
approve_friend_request = on_command('同意好友请求', aliases={'拒绝好友请求'}, permission=permission_checker)
approve_group_request = on_fullmatch(('同意加群请求', '拒绝加群请求'), permission=permission_checker)

latest_event: FriendRequestEvent | GroupRequestEvent | None = None
latest_user_info: dict[str, Any] | None = None


@request_matcher.handle()
async def request_matcher_func(bot: Bot, event: FriendRequestEvent | GroupRequestEvent) -> None:
    global latest_event, latest_user_info
    latest_event = event
    latest_user_info = await bot.get_stranger_info(user_id=event.user_id)

    message: Message = await format_message(bot, event)
    tasks = [
        bot.send_msg(group_id=user_id, message=message)
        for user_id in forward_to_expanded
    ]
    await asyncio.gather(*tasks)


@approve_friend_request.handle()
async def approve_friend_request_func(bot: Bot,
                                      event: MessageEvent,
                                      message: Message = CommandArg(),
                                      command: str = RawCommand()) -> None:
    global latest_event, latest_user_info
    if not isinstance(latest_event, FriendRequestEvent) or latest_user_info is None:
        await approve_friend_request.finish('没有待处理的请求')

    text: str = command[:2]  # “同意” or “拒绝”
    approve: bool = (text == '同意')
    remark = message.extract_plain_text()
    try:
        await bot.set_friend_add_request(flag=latest_event.flag, approve=approve, remark=remark)
    except Exception as e:
        logger.exception(e)
        await approve_friend_request.finish(f'{text}请求失败：{e}')
    else:
        self_nickname: str = (await bot.get_login_info())['nickname']
        tasks = [
            bot.send_msg(
                group_id=user_id,
                message=f'{event.sender.nickname} ({event.user_id}) 已{text} {latest_user_info["nickname"]} ({latest_event.user_id}) 添加 {self_nickname} ({bot.self_id}) 为好友的请求',
            )
            for user_id in forward_to_expanded
        ]
        latest_event = latest_user_info = None
        await asyncio.gather(*tasks)


@approve_group_request.handle()
async def approve_group_request_func(bot: Bot,
                                     event: MessageEvent,
                                     command: str = Fullmatch()) -> None:
    global latest_event, latest_user_info
    if not isinstance(latest_event, GroupRequestEvent) or latest_user_info is None:
        await approve_group_request.finish('没有待处理的请求')

    text: str = command[:2]  # “同意” or “拒绝”
    approve: bool = (text == '同意')
    try:
        await bot.set_group_add_request(flag=latest_event.flag, sub_type=latest_event.sub_type, approve=approve)
    except Exception as e:
        logger.exception(e)
        await approve_group_request.finish(f'{text}请求失败：{e}')
    else:
        group_name: str = (await bot.get_group_info(group_id=latest_event.group_id))['group_name']
        if event.sub_type == 'invite':
            self_nickname: str = (await bot.get_login_info())['nickname']
            sub_message: str = f'邀请 {self_nickname} ({bot.self_id})'
        else:  # event.sub_type == 'add'
            sub_message = '申请'
        tasks = [
            bot.send_msg(
                group_id=user_id,
                message=f'{event.sender.nickname} ({event.user_id}) 已{text} {latest_user_info["nickname"]} ({latest_event.user_id}) {sub_message} 加群 {group_name} ({latest_event.group_id}) 的请求'
            )
            for user_id in forward_to_expanded
        ]
        latest_event = latest_user_info = None
        await asyncio.gather(*tasks)


def get_user_avatar(user_id: int) -> str:
    return f'http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640'


async def format_message(bot: Bot, event: FriendRequestEvent | GroupRequestEvent) -> Message:
    user_id: int = event.user_id
    stranger_info: dict[str, Any] = await bot.get_stranger_info(user_id=user_id)
    nickname: str = stranger_info['nickname']
    self_nickname: str = (await bot.get_login_info())['nickname']
    if isinstance(event, FriendRequestEvent):
        return Message(
            f'''[fwdrequests]
{nickname} ({user_id}) 请求添加 {self_nickname} ({bot.self_id}) 为好友
头像：[CQ:image,file={get_user_avatar(user_id)}]
对方留言：{event.comment}
flag：{event.flag}
若同意，请发送“同意好友请求 [<备注>]”
若拒绝，请发送“拒绝好友请求”'''
        )
    else:
        group_name: str = (await bot.get_group_info(group_id=event.group_id))['group_name']
        if event.sub_type == 'invite':
            sub_message: str = f'邀请 {self_nickname} ({bot.self_id})'
        else:  # event.sub_type == 'add'
            sub_message = '请求'
        return Message(
            f'''[fwdrequests]
{nickname} ({user_id}) {sub_message} 加群 {group_name} ({event.group_id})
头像：[CQ:image,file={get_user_avatar(user_id)}]
对方留言：{event.comment}
flag：{event.flag}
若同意，请发送“同意加群请求”
若拒绝，请发送“拒绝加群请求”'''
        )
