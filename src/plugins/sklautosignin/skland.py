from typing import Any, Sequence

from httpx import AsyncClient

from .email import send_email as _send_email
from .manager import tokens


class SKLSignInError(Exception):
    pass


TOKEN_LENGTH = 24
APP_CODE = '4ca99fa6b56cc2ba'

login_headers = {
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close',
    'vName': '1.0.1',
    'vCode': '100001014',
    'dId': 'de9759a5afaa634f',
    'platform': '1',
}


async def get_grant_code(token: str) -> str:
    data = {
        'appCode': APP_CODE,
        'token': token,
        'type': 0,
    }

    async with AsyncClient() as client:
        response = await client.post(
            'https://as.hypergryph.com/user/oauth2/v2/grant',
            headers=login_headers,
            data=data,
        )
        obj = response.json()

    if obj['status'] != 0:
        raise SKLSignInError(obj['msg'])

    return obj['data']['code']


async def get_cred(grant_code: str) -> str:
    data = {
        'code': grant_code,
        'kind': 1,
    }

    async with AsyncClient() as client:
        response = await client.post(
            'https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code',
            headers=login_headers,
            data=data,
        )
        obj = response.json()

    if obj['code'] != 0:
        raise SKLSignInError(obj['message'])

    return obj['data']['cred']


async def get_binding_list(cred: str) -> list[dict[str, Any]]:
    headers = login_headers | {'cred': cred}
    async with AsyncClient() as client:
        response = await client.get(
            'https://zonai.skland.com/api/v1/game/player/binding',
            headers=headers,
        )
        obj = response.json()

    if obj['code'] != 0:
        raise SKLSignInError(obj['message'])

    for app in obj['data']['list']:
        if app['appCode'] == 'arknights':
            return app['bindingList']
    return []


async def sign_in_with_cred(cred: str) -> str:
    headers = login_headers | {'cred': cred}
    binding_list = await get_binding_list(cred)
    if not binding_list:
        return '获取账号绑定角色信息失败，可能是因为该账号未绑定任何角色。'

    result: list[str] = []
    for character in binding_list:
        uid: str = character['uid']
        nickname: str = character['nickName']
        channel_master_id: str = character['channelMasterId']
        channel_name: str = character['channelName']
        data = {
            'uid': uid,
            'gameId': channel_master_id,
        }

        async with AsyncClient() as client:
            response = await client.post(
                'https://zonai.skland.com/api/v1/game/attendance',
                headers=headers,
                data=data,
            )
            obj = response.json()

        if obj['code'] == 0:
            for award in obj['data']['awards']:
                award_name: str = award['resource']['name']
                award_count: int = award['resource']['count'] if 'count' in award['resource'] else 1
                result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 签到成功！获得奖励{award_name} × {award_count}。')
        elif obj['code'] == 10001:
            result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 今天已经签到！')
        else:
            message: str = obj['message']
            result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 签到时出现未知错误：{message}')
    return '\n'.join(result)


async def sign_in_with_token(token: str) -> dict[str, Any]:
    try:
        cred: str = await get_cred(await get_grant_code(token))
        return {
            'code': 0,
            'msg': await sign_in_with_cred(cred),
        }
    except SKLSignInError as e:
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
    result = await sign_in_with_token(token)
    if send_email:
        assert recipients is not None, ValueError
        if result['code'] == 0:
            subject: str = '森空岛签到成功'
        else:
            subject = '森空岛签到失败'
        await _send_email(recipients, subject, result['msg'])
    return result
