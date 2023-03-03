import json
import os
import random
import time
from collections import defaultdict
from enum import Enum

import aiofiles
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.event import Sender

from . import config

sender_dict_T = dict[str, int | str | None]
reply_dict_T = dict[str, sender_dict_T]
group_dict_T = defaultdict[str, reply_dict_T]
main_dict_T = defaultdict[int, group_dict_T]

data_path: str = config.data_path

main_dict: main_dict_T = defaultdict(lambda: defaultdict(dict))


class ResultCode(Enum):
    LEARN_SUCCESS = 0
    LEARN_DUPLICATED = 1
    FORGET_SUCCESS = 2
    FORGET_FAILED = 3
    FORGET_NO_PERMISSION = 4


def get_main_dict() -> main_dict_T:
    return main_dict


def _strftime(event_time: int) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event_time))


def _message_preprocess(message: Message) -> Message:
    '''预处理message, 对于`CQ:image`仅保留`file`字段'''
    for message_segment in message:
        if message_segment.type == 'image':
            message_segment.data = {'file': message_segment.data['file']}
    return message


def _str_msg_proprecess(message: str) -> str:
    return str(_message_preprocess(Message(message)))


def _get_sender_info(sender: Sender) -> sender_dict_T:
    return {
        'qqid': sender.user_id,
        'nickname': sender.nickname,
        'card': sender.card,
        'role': sender.role,
    }


async def load_from_file(group_id: int) -> None:
    if group_id in main_dict:
        return

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    file_path: str = os.path.join(data_path, f'{group_id}.json')
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as fp:
            main_dict[group_id] = defaultdict(dict, json.loads(await fp.read()))


async def _save_to_file(group_id: int) -> None:
    file_path: str = os.path.join(data_path, f'{group_id}.json')
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(main_dict[group_id], ensure_ascii=False, indent=4))


async def learn_autoreply(group_id: int,
                          trigger_message: str,
                          reply_message: str,
                          sender: Sender,
                          event_time: int) -> ResultCode:
    await load_from_file(group_id)
    trigger_message, reply_message = (
        _str_msg_proprecess(trigger_message), _str_msg_proprecess(reply_message),)
    reply_messages_dict: reply_dict_T = main_dict[group_id][trigger_message]

    if reply_message in reply_messages_dict:
        return ResultCode.LEARN_DUPLICATED

    reply_messages_dict[reply_message] = _get_sender_info(sender) | {'time': event_time}
    await _save_to_file(group_id)
    return ResultCode.LEARN_SUCCESS


async def forget_autoreply(group_id: int,
                           trigger_message: str,
                           reply_message: str,
                           sender: Sender,
                           sender_permission: bool = False) -> ResultCode:
    await load_from_file(group_id)
    trigger_message, reply_message = (
        _str_msg_proprecess(trigger_message), _str_msg_proprecess(reply_message))
    if trigger_message not in main_dict[group_id]:
        return ResultCode.FORGET_FAILED

    reply_messages_dict: reply_dict_T = main_dict[group_id][trigger_message]

    if reply_message not in reply_messages_dict:
        return ResultCode.FORGET_FAILED

    if (not sender_permission) and (reply_messages_dict[reply_message]['role'] in ['owner', 'admin']):
        return ResultCode.FORGET_NO_PERMISSION

    del reply_messages_dict[reply_message]
    if not reply_messages_dict:
        del main_dict[group_id][trigger_message]
    await _save_to_file(group_id)
    return ResultCode.FORGET_SUCCESS


async def forget_all_autoreply(group_id, raw_trigger_message) -> tuple[ResultCode, int]:
    await load_from_file(group_id)
    trigger_message: str = _str_msg_proprecess(raw_trigger_message)
    if trigger_message not in main_dict[group_id]:
        return (ResultCode.FORGET_FAILED, 0)

    num: int = len(main_dict[group_id][trigger_message])
    del main_dict[group_id][trigger_message]
    await _save_to_file(group_id)
    return (ResultCode.FORGET_SUCCESS, num)


async def query_reply(group_id: int, raw_message: str) -> (str | None):
    await load_from_file(group_id)
    message: str = _str_msg_proprecess(raw_message)
    if message not in main_dict[group_id]:
        return None

    num: int = len(main_dict[group_id][message])
    reply_list: list[str] = [f'{message}的回复语（共{num}条）：']
    for i, (reply_message, sender_info) in enumerate(main_dict[group_id][message].items()):
        reply_list.append(
            f"{i+1}. {reply_message}  # 由{sender_info['card'] or sender_info['nickname']} ({sender_info['qqid']}) 于{_strftime(sender_info['time'])}设置")  # type: ignore
    return '\n'.join(reply_list)


async def query_all_reply(group_id: int) -> str:
    await load_from_file(group_id)
    if not main_dict[group_id]:
        return '本群未设置自动回复！'
    else:
        return (f'本群的全部回复语（共{len(main_dict[group_id])}条）\n'
                + '\n'.join(f'{i+1}. {trigger_message}'
                            for i, trigger_message in enumerate(main_dict[group_id])))


async def get_reply(group_id: int, raw_message: str) -> (str | None):
    await load_from_file(group_id)
    message: str = _str_msg_proprecess(raw_message)
    if message not in main_dict[group_id]:
        return None
    return random.choice(list(main_dict[group_id][message]))
