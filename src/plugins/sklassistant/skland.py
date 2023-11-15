"""能跑的代码就别动（×"""
import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Sequence
from typing import Any
from urllib import parse

from httpx import AsyncClient
from loguru import logger

from .email import send_email as _send_email

TOKEN_LENGTH = 24
APP_CODE = '4ca99fa6b56cc2ba'


class SKLAssistantError(Exception):
    pass


login_headers: dict[str, str] = {
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close'
}

# 签名请求头一定要这个顺序，否则失败
# timestamp是必填的,其它三个随便填,不要为none即可
header_for_sign: dict[str, str] = {
    'platform': '',
    'timestamp': '',
    'dId': '',
    'vName': ''
}


def generate_signature(token: str, path: str, body_or_query: str) -> tuple[str, Any]:
    """
    获得签名头
    接口地址+方法为Get请求？用query否则用body+时间戳+ 请求头的四个重要参数（dId，platform，timestamp，vName）.toJSON()
    将此字符串做HMAC加密，算法为SHA-256，密钥token为请求cred接口会返回的一个token值
    再将加密后的字符串做MD5即得到sign
    :param token: 拿cred时候的token
    :param path: 请求路径（不包括网址）
    :param body_or_query: 如果是GET，则是它的query。POST则为它的body
    :return: 计算完毕的sign
    """
    # 总是说请勿修改设备时间，怕不是yj你的服务器有问题吧，所以这里特地-2
    time_stamp = str(int(time.time()) - 2)
    header_ca = json.loads(json.dumps(header_for_sign))
    header_ca['timestamp'] = time_stamp
    header_ca_str: str = json.dumps(header_ca, separators=(',', ':'))
    s: str = path + body_or_query + time_stamp + header_ca_str
    hex_s: str = hmac.new(token.encode('utf-8'), s.encode('utf-8'), hashlib.sha256).hexdigest()
    md5: str = hashlib.md5(hex_s.encode('utf-8')).hexdigest().encode('utf-8').decode('utf-8')  # 算出签名
    return md5, header_ca


def get_sign_header(url: str,
                    method: str,
                    body,
                    old_header,
                    sign_token: str) -> dict[str, str]:
    """能跑的代码就不去动他（"""
    h = json.loads(json.dumps(old_header))
    p = parse.urlparse(url)
    if method.lower() == 'get':
        h['sign'], header_ca = generate_signature(sign_token, p.path, p.query)
    else:
        h['sign'], header_ca = generate_signature(sign_token, p.path, json.dumps(body))
    for i in header_ca:
        h[i] = header_ca[i]
    # logger.debug(f'get_sign_header(url={url!r}, method={method!r}, old_header={old_header!r}, sign_token={sign_token!r}) returns {h!r}')
    return h


async def login_by_phone_password(phone, password) -> str:
    data = {
        "phone": phone,
        "password": password,
    }

    async with AsyncClient() as client:
        response = await client.post(
            "https://as.hypergryph.com/user/auth/v1/token_by_phone_password",
            headers=login_headers,
            json=data,
        )
    obj = response.json()
    # logger.debug(f'POST https://as.hypergryph.com/user/auth/v1/token_by_phone_password returns {obj!r}')

    if obj['status'] != 0:
        raise SKLAssistantError(f'登录失败：{obj["msg"]}')
    # logger.debug(f'login_by_password(phone={phone!r}, password={password!r}) returns {ret!r}')
    return obj['data']['token']


async def get_grant_code(token) -> str:
    data = {
        'appCode': APP_CODE,
        'token': token,
        'type': 0,
    }

    async with AsyncClient() as client:
        response = await client.post(
            "https://as.hypergryph.com/user/oauth2/v2/grant",
            headers=login_headers,
            json=data,
        )
    obj = response.json()
    # logger.debug(f'POST https://as.hypergryph.com/user/oauth2/v2/grant returns {obj!r}')

    if obj['status'] != 0:
        raise SKLAssistantError(f'获取认证代码失败：{obj["msg"]}')
    # ret = obj['data']['code']
    # logger.debug(f'get_grant_code(token={token!r}) returns {ret!r}')
    return obj['data']['code']


async def get_cred(grant_code) -> tuple[str, str]:
    data = {
        'code': grant_code,
        'kind': 1
    }

    async with AsyncClient() as client:
        response = await client.post(
            "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code",
            headers=login_headers,
            json=data,
        )
    obj = response.json()
    # logger.debug(f'POST https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code returns {obj!r}')

    if obj['code'] != 0:
        raise SKLAssistantError(f'获取cred失败：{obj["message"]}')
    # ret = obj['data']
    # logger.debug(f'get_cred(grant={grant!r}) returns {ret!r}')
    return obj['data']['cred'], obj['data']['token']


async def get_binding_list(cred: str, sign_token: str, app_code: str = 'arknights') -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    headers = get_sign_header(
        "https://zonai.skland.com/api/v1/game/player/binding",
        'get',
        None,
        login_headers | {'cred': cred},
        sign_token,
    )

    async with AsyncClient() as client:
        response = await client.get(
            "https://zonai.skland.com/api/v1/game/player/binding",
            headers=headers,
        )
    obj = response.json()
    # logger.debug(f'GET https://zonai.skland.com/api/v1/game/player/binding returns {obj!r}')

    if obj['code'] != 0:
        raise SKLAssistantError(f"请求角色列表出现错误：{obj['message']}")

    for app in obj['data']['list']:
        if app['appCode'] == app_code:
            result.extend(app['bindingList'])
    return result


async def sign_in_single_character(cred: str, sign_token: str, character: dict[str, Any]) -> str:
    uid: str = character['uid']
    nickname: str = character['nickName']
    channel_master_id: str = character['channelMasterId']
    channel_name: str = character['channelName']

    data = {
        'gameId': channel_master_id,
        'uid': uid,
    }
    headers = get_sign_header(
        'https://zonai.skland.com/api/v1/game/attendance',
        'post',
        data,
        login_headers | {'cred': cred},
        sign_token,
    )

    async with AsyncClient() as client:
        response = await client.post(
            'https://zonai.skland.com/api/v1/game/attendance',
            headers=headers,
            json=data,
        )
    obj = response.json()
    # logger.debug(f'POST https://zonai.skland.com/api/v1/game/attendance returns {obj!r}')

    if obj['code'] == 0:
        award_messages: list[str] = []
        for award in obj['data']['awards']:
            award_name: str = award['resource']['name']
            award_count: int = award['count'] if 'count' in award else 1
            award_messages.append(f'{award_name} × {award_count}')
        award_message = f'获得奖励{"、".join(award_messages)}。' if award_messages else '未获得任何奖励。'
        return f'{channel_name}账号 Dr. {nickname} ({uid}) 签到成功！{award_message}'

    elif obj['code'] == 10001:
        return f'{channel_name}账号 Dr. {nickname} ({uid}) 今天已经签到！'

    else:
        message: str = obj['message']
        raise SKLAssistantError(f'{channel_name}账号 Dr. {nickname} ({uid}) 签到时出现未知错误：{message}')


async def sign_in_by_token(token: str) -> dict[str, Any]:
    try:
        cred, sign_token = await get_cred(await get_grant_code(token))
        binding_list: list[dict[str, Any]] = await get_binding_list(cred, sign_token)

        if not binding_list:
            return {
                'code': 1,
                'msg': '获取账号绑定角色信息失败，该账号未绑定任何角色。',
            }

        tasks = [sign_in_single_character(cred, sign_token, character) for character in binding_list]
        result: list[str | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)
        success: bool = all(isinstance(x, str) for x in result)
        message: str = '\n'.join(x if isinstance(x, str) else repr(x) for x in result)

        return {
            'code': 0 if success else 3,
            'msg': message,
        }
    except SKLAssistantError as e:
        return {
            'code': 1,
            'msg': f'森空岛自动签到出现错误：{e!r}',
        }
    except Exception as e:
        return {
            'code': 2,
            'msg': f'森空岛自动签到出现错误：{e!r}',
        }


async def sign_in_and_send_email(token: str,
                                 send_email: bool = True,
                                 recipients: str | Sequence[str] | None = None) -> dict[str, Any]:
    result = await sign_in_by_token(token)
    if send_email:
        assert recipients is not None, ValueError
        if result['code'] == 0:
            subject: str = '森空岛签到成功'
        else:
            subject = '森空岛签到失败'
        await _send_email(recipients, subject, result['msg'])
    return result
