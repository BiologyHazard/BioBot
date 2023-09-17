import asyncio
from typing import Any

from nonebot import on_command, on_request
from nonebot.adapters.onebot.v11 import (Bot, FriendRequestEvent,
                                         GroupRequestEvent, Message,
                                         PrivateMessageEvent, RequestEvent)
from nonebot.params import CommandArg, RawCommand
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from .config import forward_to_expanded

__plugin_meta__: PluginMetadata = PluginMetadata(
    name='转发加好友加群请求',
    description='',
    usage='''''',
)

request_matcher = on_request()
approve_request = on_command('同意好友请求', aliases={'拒绝好友请求'})

latest_event = None
latest_user_info = None


@request_matcher.handle()
async def request_matcher_func(bot: Bot, event: RequestEvent, state: T_State) -> None:
    global latest_event, latest_user_info
    if isinstance(event, FriendRequestEvent):
        message: Message = await format_message(bot, event)
        tasks = [
            bot.send_private_msg(user_id=user_id, message=message)
            for user_id in forward_to_expanded
        ]
        latest_event = event
    else:
        tasks = [
            bot.send_private_msg(user_id=user_id, message=repr(event))
            for user_id in forward_to_expanded
        ]
    await asyncio.gather(*tasks)


@approve_request.handle()
async def approve_request_func(bot: Bot, event: PrivateMessageEvent, message: Message = CommandArg(), command: str = RawCommand()) -> None:
    global latest_event, latest_user_info
    if latest_event is None:
        await approve_request.finish('没有待处理的请求')

    if command == '同意好友请求':
        approve: bool = True
    else:
        approve: bool = False
    text = command[:2]

    remark: str = message.extract_plain_text()
    try:
        await bot.set_friend_add_request(flag=latest_event.flag, approve=approve, remark=remark)
    except Exception as e:
        await approve_request.finish(f'{text}请求失败：{e}')
    else:
        self_nickname: str = (await bot.get_login_info())['nickname']
        tasks = [
            bot.send_private_msg(
                user_id=user_id,
                message=f'{event.sender.nickname} ({event.user_id}) 已{text} {latest_user_info["nickname"]} ({latest_event.user_id}) 添加 {self_nickname} ({bot.self_id}) 为好友的请求'
            )
            for user_id in forward_to_expanded
        ]
        latest_event = latest_user_info = None
        await asyncio.gather(*tasks)


def get_user_avatar(user_id: int) -> str:
    return f'http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640'


async def format_message(bot: Bot, event: FriendRequestEvent) -> Message:
    global latest_user_info
    user_id: int = event.user_id
    stranger_info: dict[str, Any] = await bot.get_stranger_info(user_id=user_id)
    latest_user_info = stranger_info
    nickname: str = stranger_info['nickname']
    self_nickname: str = (await bot.get_login_info())['nickname']
    return Message(
        f'''[fwdrequests]
{nickname} ({user_id}) 请求添加 {self_nickname} ({bot.self_id}) 为好友
头像：[CQ:image,file={get_user_avatar(user_id)}]
对方留言：{event.comment}
flag：{event.flag}
若同意，请发送“同意好友请求 [<备注>]”
若拒绝，请发送“拒绝好友请求”'''
    )
