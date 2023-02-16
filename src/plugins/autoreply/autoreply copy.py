import json
import os
import random
from collections import defaultdict
from hashlib import md5

import aiofiles
from nonebot import logger
from nonebot.adapters.onebot.v11 import Message

from .config import data_path

# loaded_from_file: set[int] = set()
group_dict_T = dict[str: list[str]]
main_dict: dict[int: group_dict_T] = defaultdict(lambda: defaultdict(list))


class ResultCode:
    LEARN_SUCCESS = 0
    LEARN_DUPLICATED = 1
    FORGET_SUCCESS = 2
    FORGET_FAILED = 3


def md5str(s: str) -> str:
    return md5(s.encode('utf-8')).hexdigest()


def _message_preprocess(message: Message) -> Message:
    for message_segment in message:
        if message_segment.type == 'image':
            message_segment.data = {'file': message_segment.data['file']}
    return message


def _str_msg_proprecess(message: str) -> str:
    return str(_message_preprocess(Message(message)))


async def _load_from_file(group_id: int):
    if group_id in main_dict:
        return

    file_dir = os.path.join(data_path, str(group_id))
    if os.path.exists(file_dir):
        for filename in os.listdir(file_dir):
            file_path = os.path.join(file_dir, filename)
            assert not os.path.isdir(file_path)
            if not os.path.isdir(file_path):
                name, ext = os.path.splitext(filename)
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as fp:
                    main_dict[group_id][name] = json.loads(await fp.read())


async def _save_to_file(group_id: int, hash_value: str, reply_messages_list: list[str]):
    logger.trace(repr(reply_messages_list))
    file_dir = os.path.join(data_path, str(group_id))
    file_path = os.path.join(file_dir, f'{str(hash_value)}.json')
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    if not reply_messages_list:
        if os.path.exists(file_path):
            logger.trace(f'Deleting {file_path}')
            os.remove(file_path)
    else:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(json.dumps(reply_messages_list, ensure_ascii=False))


async def learn_autoreply(group_id: int, trigger_msg: str, reply_msg: str) -> int:
    await _load_from_file(group_id)
    # logger.trace(repr(trigger_msg))
    # logger.trace(repr(reply_msg))
    trigger_msg, reply_msg = (_str_msg_proprecess(trigger_msg),
                              _str_msg_proprecess(reply_msg))
    hash_value = md5str(trigger_msg)
    reply_messages_list = main_dict[group_id][hash_value]

    if reply_msg in reply_messages_list:
        return ResultCode.LEARN_DUPLICATED

    reply_messages_list.append(reply_msg)
    await _save_to_file(group_id=group_id,
                        hash_value=hash_value,
                        reply_messages_list=reply_messages_list)
    return ResultCode.LEARN_SUCCESS


async def forget_autoreply(group_id: int, trigger_msg: str, reply_msg: str) -> int:
    await _load_from_file(group_id)
    trigger_msg, reply_msg = (_str_msg_proprecess(trigger_msg),
                              _str_msg_proprecess(reply_msg))
    hash_value = md5str(trigger_msg)
    if hash_value not in main_dict[group_id]:
        return ResultCode.FORGET_FAILED

    reply_messages_list = main_dict[group_id][hash_value]

    if reply_msg not in reply_messages_list:
        return ResultCode.FORGET_FAILED

    reply_messages_list.remove(reply_msg)
    if not reply_messages_list:
        del main_dict[group_id][hash_value]
    await _save_to_file(group_id=group_id,
                        hash_value=hash_value,
                        reply_messages_list=reply_messages_list)
    return ResultCode.FORGET_SUCCESS


async def get_reply(group_id: int, message: str) -> str | None:
    await _load_from_file(group_id)
    message = _str_msg_proprecess(message)
    hash_value = md5str(message)
    logger.trace(repr(message))
    logger.trace(repr(hash_value))
    logger.trace(repr(main_dict))
    if hash_value in main_dict[group_id]:
        return random.choice(main_dict[group_id][hash_value])
    return None
