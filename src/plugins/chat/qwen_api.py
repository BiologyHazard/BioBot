import aiohttp
from nonebot import logger

from .typing import Result

url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'


async def get_reply(api_key, model, text, **kwargs) -> Result:
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': api_key,
        }
        data = {
            'model': model,
            'input': {
                'messages': text,
            },
            'parameters': {
                'result_format': 'message',
                **kwargs,
            }
        }
        async with aiohttp.request('POST', url, headers=headers, json=data) as response:
            obj = await response.json()
        if response.status != 200:
            return {
                'code': response.status,
                'message': obj['code'] + ': ' + obj['message'],
                'data': {},
            }
        content = obj['output']['choices'][0]['message']['content']
        logger.debug(repr(text) + ' -> ' + content)
        return {
            'code': 0,
            'message': 'Success',
            'data': {'content': obj['output']['choices'][0]['message']['content']},
        }
    except Exception as e:
        return {
            'code': -1,
            'message': repr(e),
            'data': {},
        }
