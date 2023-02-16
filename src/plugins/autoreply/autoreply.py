import json
import os
import random
from collections import defaultdict

import aiofiles
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message
from nonebot.adapters.onebot.v11.event import Sender

from .config import data_path

sender_dict_T = dict[str, int | str]
reply_dict_T = dict[str, sender_dict_T]
group_dict_T = defaultdict[str, reply_dict_T]
main_dict_T = defaultdict[int, group_dict_T]

main_dict: main_dict_T = defaultdict(lambda: defaultdict(dict))


class ResultCode:
    LEARN_SUCCESS = 0
    LEARN_DUPLICATED = 1
    FORGET_SUCCESS = 2
    FORGET_FAILED = 3
    FORGET_NO_PERMISSION = 4


# PERMISSION_LEVEL = ['member', 'admin', 'owner']


def _message_preprocess(message: Message) -> Message:
    '''预处理message, 对于`CQ:image`仅保留`file`字段'''
    for message_segment in message:
        if message_segment.type == 'image':
            message_segment.data = {'file': message_segment.data['file']}
    return message


def _str_msg_proprecess(message: str) -> str:
    return str(_message_preprocess(Message(message)))


def _get_sender_info(sender: Sender):
    return {
        'qqid': sender.user_id,
        'nickname': sender.nickname,
        'card': sender.card,
        'role': sender.role,
    }


async def _load_from_file(group_id: int):
    if group_id in main_dict:
        return

    if not os.path.exists(data_path):
        os.makedirs(data_path)

    file_path = os.path.join(data_path, f'{group_id}.json')
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as fp:
            main_dict[group_id] = defaultdict(dict, json.loads(await fp.read()))


async def _save_to_file(group_id: int):
    file_path = os.path.join(data_path, f'{group_id}.json')
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(main_dict[group_id], ensure_ascii=False, indent=4))


async def learn_autoreply(group_id: int, trigger_message: str, reply_message: str, sender: Sender) -> int:
    await _load_from_file(group_id)
    trigger_message, reply_message = (_str_msg_proprecess(trigger_message),
                                      _str_msg_proprecess(reply_message),)
    reply_messages_dict = main_dict[group_id][trigger_message]

    if reply_message in reply_messages_dict:
        return ResultCode.LEARN_DUPLICATED

    reply_messages_dict[reply_message] = _get_sender_info(sender)
    await _save_to_file(group_id)
    return ResultCode.LEARN_SUCCESS


async def forget_autoreply(group_id: int, trigger_message: str, reply_message: str, sender: Sender) -> int:
    await _load_from_file(group_id)
    trigger_message, reply_message = (_str_msg_proprecess(trigger_message),
                                      _str_msg_proprecess(reply_message))
    if trigger_message not in main_dict[group_id]:
        return ResultCode.FORGET_FAILED

    reply_messages_dict = main_dict[group_id][trigger_message]

    if reply_message not in reply_messages_dict:
        return ResultCode.FORGET_FAILED

    if ((sender.role not in ['owner', 'admin'])
            and (reply_messages_dict[reply_message]['role'] in ['owner', 'admin'])):
        return ResultCode.FORGET_NO_PERMISSION

    del reply_messages_dict[reply_message]
    if not reply_messages_dict:
        del main_dict[group_id][trigger_message]
    await _save_to_file(group_id)
    return ResultCode.FORGET_SUCCESS


async def get_reply(group_id: int, message: str) -> (str | None):
    await _load_from_file(group_id)
    message = _str_msg_proprecess(message)
    logger.trace(repr(message))
    logger.trace(repr(main_dict))
    if message not in main_dict[group_id]:
        return None
    return random.choice(list(main_dict[group_id][message]))


async def query_reply(group_id: int, message: str) -> tuple[int, str]:
    await _load_from_file(group_id)
    message = _str_msg_proprecess(message)
    if message not in main_dict[group_id]:
        return (0, '')

    reply_list = []
    for reply_message, sender_info in main_dict[group_id][message].items():
        reply_list.append(
            f"{reply_message}  由{sender_info['card']}({sender_info['qqid']}) 设置")
    return (len(reply_list), '\n'.join(reply_list))
