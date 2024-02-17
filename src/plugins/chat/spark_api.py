import base64
import hashlib
import hmac
import json
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

import websockets.client
import websockets.exceptions
from nonebot import logger

from .typing import Result, Text

VERSION_TO_DOMAIN = {
    'v1.5': 'general',
    'v2.0': 'generalv2',
    'v3.0': 'generalv3',
    'v3.5': 'generalv3.5',
}

VERSION_TO_URL = {
    'v1.5': 'ws://spark-api.xf-yun.com/v1.1/chat',
    'v2.0': 'ws://spark-api.xf-yun.com/v2.1/chat',
    'v3.0': 'ws://spark-api.xf-yun.com/v3.1/chat',
    'v3.5': 'ws://spark-api.xf-yun.com/v3.5/chat',
}


# 生成url
def create_url(APPID: str, APIKey: str, APISecret: str, Spark_url: str):
    host = urlparse(Spark_url).netloc
    path = urlparse(Spark_url).path
    # 生成RFC1123格式的时间戳
    date = format_date_time(None)

    # 拼接字符串
    signature_origin = (f"host: {host}\n"
                        f"date: {date}\n"
                        f"GET {path} HTTP/1.1")

    # 进行hmac-sha256进行加密
    signature_sha = hmac.new(
        APISecret.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).digest()

    signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')

    authorization_origin = f'api_key="{APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

    # 将请求的鉴权参数组合为字典
    v = {
        "authorization": authorization,
        "date": date,
        "host": host
    }
    # 拼接鉴权参数，生成url
    url = f'{Spark_url}?{urlencode(v)}'
    # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
    return url


def gen_params(appid, domain, question, **kwargs):
    """
    通过appid和用户的提问来生成请参数
    """
    data = {
        "header": {
            "app_id": appid,
            # "uid": "1234"
        },
        "parameter": {
            "chat": {
                "domain": domain,
                # "temperature": 0.5,
                # "max_tokens": 2048
                **kwargs,
            }
        },
        "payload": {
            "message": {
                "text": question
            }
        }
    }
    return data


async def get_reply(appid: str, api_key: str, api_secret: str, version: str, text: Text) -> Result:
    try:
        version = version.lower()
        if not version.startswith('v'):
            version = f'v{version}'
        if version not in VERSION_TO_DOMAIN:
            logger.error(f'不支持的星火版本：{version}，插件将使用默认版本v3.5')
            version = 'v3.5'
        Spark_url = VERSION_TO_URL[version]
        domain = VERSION_TO_DOMAIN[version]
        answer_segments: list[str] = []
        wsUrl = create_url(appid, api_key, api_secret, Spark_url)
        async with websockets.client.connect(wsUrl) as websocket:
            await websocket.send(json.dumps(gen_params(appid, domain, text)))
            while True:
                try:
                    message = await websocket.recv()
                except websockets.exceptions.ConnectionClosed as e:
                    break
                data = json.loads(message)
                code = data['header']['code']
                if code != 0:
                    return {
                        'code': code,
                        'message': data['header']['message'],
                        'data': {},
                    }
                else:
                    choices = data["payload"]["choices"]
                    status = choices["status"]
                    content = choices["text"][0]["content"]
                    answer_segments.append(content)
                    if status == 2:
                        await websocket.close()
                        break
        logger.debug(repr(text) + ' -> ' + ''.join(answer_segments))
        return {
            'code': 0,
            'message': 'Success',
            'data': {'content': ''.join(answer_segments)},
        }
    except Exception as e:
        return {
            'code': -1,
            'message': repr(e),
            'data': {},
        }
