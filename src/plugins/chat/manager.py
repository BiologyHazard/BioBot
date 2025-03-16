from __future__ import annotations

from typing import Literal, Self

from nonebot import logger

from .config import plugin_config
from .spark_api import get_reply as spark_get_reply
from .qwen_api import get_reply as qwen_get_reply
from .typing import Result, Text, TextPart

spark_appid = plugin_config.spark_appid
spark_api_key = plugin_config.spark_api_key
spark_api_secret = plugin_config.spark_api_secret
spark_version = plugin_config.spark_version
qwen_api_key = plugin_config.qwen_api_key


async def get_reply(text: Text, model: str = 'qwen-max', **kwargs) -> Result:
    # return {
    #     'code': 0,
    #     'message': 'Success',
    #     'data': {
    #         'content': repr(text),
    #     },
    # }
    match model:
        case 'qwen-turbo' | 'qwen-plus' | 'qwen-max' | 'qwen-max-1201' | 'qwen-max-longcontext' | "deepseek-r1" | "deepseek-v3":
            return await qwen_get_reply(qwen_api_key, model, text, **kwargs)
        case 'spark':
            return await spark_get_reply(spark_appid, spark_api_key, spark_api_secret, spark_version, text)
        case _:
            logger.error(f'不支持的模型：{model}')
            return {
                'code': -1,
                'message': f'不支持的模型：{model}',
                'data': {},
            }


async def single_question(message: str) -> Result:
    text: Text = [{
        'role': 'user',
        'content': message,
    }]
    return await get_reply(text)


def get_text_length(text: Text) -> int:
    return sum(len(part['content']) for part in text)


def cut_text(text: Text, max_length=4000) -> Text:
    while (get_text_length(text) > max_length):
        del text[0]
    return text


class Session:
    def __init__(self, text_part: TextPart | None = None, parent: Session | None = None) -> None:
        self.text_part: TextPart | None = text_part
        self.parent: Session | None = parent

    def copy(self, **kwargs) -> Self:
        return self.__class__(**(self.__dict__ | kwargs))

    def add_message(self, role: Literal['system', 'user', 'assistant'], message: str) -> Self:
        # if self.text_part is not None:
        # self.parent = self.__class__(self.text_part, self.parent)
        # self.text_part = {
        #     'role': role,
        #     'content': message,
        # }
        text_part: TextPart = {
            'role': role,
            'content': message,
        }
        return self.__class__(text_part, self)

    def add_system(self, message: str) -> Self:
        return self.add_message('system', message)

    def add_question(self, message: str) -> Self:
        return self.add_message('user', message)

    def add_answer(self, message: str) -> Self:
        return self.add_message('assistant', message)

    def get_text(self, cut: int | bool = True) -> Text:
        if self.text_part is None or self.parent is None:
            return []
        text: Text = self.parent.get_text()
        text.append(self.text_part)

        if cut is True:
            text = cut_text(text)
        elif isinstance(cut, int):
            text = cut_text(text, cut)

        return text

    async def get_reply(self, message: str, model: str = 'qwen-max', cut: int | bool = True) -> tuple[Result, Self]:
        # text = {
        #     'role': 'user',
        #     'content': question,
        # }
        session = self.add_question(message)
        answer = await get_reply(session.get_text(cut), model)
        if answer['code'] == 0:
            session = session.add_answer(answer['data']['content'])
            return answer, session
        else:
            return answer, self

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(text={self.text_part}, parent={self.parent})'


sessions: dict[int, Session] = {}
