"""能跑的代码就别动（×"""
import hashlib
import hmac
import json
import time
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from urllib import parse

import requests
from nonebot import logger
from .email import send_email as _send_email

TOKEN_LENGTH = 24


class SKLSignInError(Exception):
    pass


header: dict[str, str] = {
    'cred': '',
    'User-Agent': 'Skland/1.0.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0',
    'Accept-Encoding': 'gzip',
    'Connection': 'close'
}
header_login: dict[str, str] = {
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


def get_sign_header(url: str, method, body, old_header, sign_token):
    h = json.loads(json.dumps(old_header))
    p = parse.urlparse(url)
    if method.lower() == 'get':
        h['sign'], header_ca = generate_signature(sign_token, p.path, p.query)
    else:
        h['sign'], header_ca = generate_signature(sign_token, p.path, json.dumps(body))
    for i in header_ca:
        h[i] = header_ca[i]
    return h


def login_by_password(phone, password):
    r = requests.post("https://as.hypergryph.com/user/auth/v1/token_by_phone_password",
                      json={"phone": phone, "password": password}, headers=header_login).json()
    return get_token(r)


def get_cred_by_token(token):
    grant_code = get_grant_code(token)
    return get_cred(grant_code)


def get_token(resp):
    if not resp.get('status') == 0:
        raise Exception(f'获得token失败：{resp["msg"]}')
    return resp['data']['token']


def get_grant_code(token):
    response = requests.post("https://as.hypergryph.com/user/oauth2/v2/grant", json={
        'appCode': '4ca99fa6b56cc2ba',
        'token': token,
        'type': 0
    }, headers=header_login)
    resp = response.json()
    if not response.status_code == 200:
        raise Exception(f'获得认证代码失败：{resp}')
    if not resp.get('status') == 0:
        raise Exception(f'获得认证代码失败：{resp["msg"]}')
    return resp['data']['code']


def get_cred(grant):
    resp = requests.post("https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code", json={
        'code': grant,
        'kind': 1
    }, headers=header_login).json()
    if not resp['code'] == 0:
        raise Exception(f'获得cred失败：{resp["message"]}')
    return resp['data']


def get_binding_list(sign_token):
    v = []
    resp = requests.get("https://zonai.skland.com/api/v1/game/player/binding",
                        headers=get_sign_header("https://zonai.skland.com/api/v1/game/player/binding",
                                                'get', None, header, sign_token)).json()

    if not resp['code'] == 0:
        logger.warning(f"请求角色列表出现问题：{resp['message']}")
        if resp.get('message') == '用户未登录':
            logger.warning(f'用户登录可能失效了，请重新运行此程序！')
            return []
    for i in resp['data']['list']:
        if not i.get('appCode') == 'arknights':
            continue
        v.extend(i.get('bindingList'))
    return v


# async def sign_in_with_cred(cred: str) -> str:
#     headers = login_headers | {'cred': cred}
#     binding_list = await get_binding_list(cred)
#     if not binding_list:
#         return '获取账号绑定角色信息失败，可能是因为该账号未绑定任何角色。'

#     result: list[str] = []
#     for character in binding_list:
#         uid: str = character['uid']
#         nickname: str = character['nickName']
#         channel_master_id: str = character['channelMasterId']
#         channel_name: str = character['channelName']
#         data = {
#             'uid': uid,
#             'gameId': channel_master_id,
#         }

#         async with AsyncClient() as client:
#             response = await client.post(
#                 'https://zonai.skland.com/api/v1/game/attendance',
#                 headers=headers,
#                 data=data,
#             )
#             obj = response.json()

#         if obj['code'] == 0:
#             for award in obj['data']['awards']:
#                 award_name: str = award['resource']['name']
#                 award_count: int = award['count'] if 'count' in award else 1
#                 result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 签到成功！获得奖励{award_name} × {award_count}。')
#         elif obj['code'] == 10001:
#             result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 今天已经签到！')
#         else:
#             message: str = obj['message']
#             result.append(f'{channel_name}账号 Dr. {nickname} ({uid}) 签到时出现未知错误：{message}')
#     return '\n'.join(result)


async def sign_in_by_token(token: str) -> dict[str, Any]:
    try:
        sign_token = get_cred_by_token(token)['token']
        header['cred'] = get_cred_by_token(token)['cred']
        characters = get_binding_list(sign_token)
        message: str = ''
        for i in characters:
            body = {
                'gameId': 1,
                'uid': i.get('uid')
            }
            resp = requests.post("https://zonai.skland.com/api/v1/game/attendance",
                                 headers=get_sign_header("https://zonai.skland.com/api/v1/game/attendance",
                                                         'post', body, header, sign_token), json=body).json()
            if resp['code'] == 0:
                已签到日期 = datetime.now().strftime('%Y年%m月%d日')
                logger.warning(f'今天是{已签到日期}，{i.get("nickName")}({i.get("channelName")})在森空岛签到成功！')
                message += f'今天是{已签到日期}，{i.get("nickName")}({i.get("channelName")})在森空岛签到成功！\n'
                for j in resp['data']['awards']:
                    res = j['resource']
                    logger.warning(f'获得了{res["name"]} × {j.get("count") or 1}')
                    message += f'获得了{res["name"]} × {j.get("count") or 1}\n'
            elif resp['code'] == 10001:
                已签到日期 = datetime.now().strftime('%Y年%m月%d日')
                logger.info(f'今天是{已签到日期}，{i.get("nickName")}({i.get("channelName")})今天在森空岛已经签过到了')
                message += f'今天是{已签到日期}，{i.get("nickName")}({i.get("channelName")})今天在森空岛已经签过到了\n'
            else:
                logger.warning(f'{i.get("nickName")}({i.get("channelName")})签到失败了！原因：{resp.get("message")}')
                message += f'{i.get("nickName")}({i.get("channelName")})签到失败了！原因：{resp.get("message")}\n'
                continue
        return {
            'code': 0,
            'msg': message,
        }
        # cred: str = await get_cred(await get_grant_code(token))
        # return {
        #     'code': 0,
        #     'msg': await sign_in_with_cred(cred),
        # }
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
    result = await sign_in_by_token(token)
    if send_email:
        assert recipients is not None, ValueError
        if result['code'] == 0:
            subject: str = '森空岛签到成功'
        else:
            subject = '森空岛签到失败'
        await _send_email(recipients, subject, result['msg'])
    return result
