from typing import Any, Literal

import aiohttp

from .privacy import query_privacy

T_project = Literal['best', 'plate']


async def get_player_data(project: T_project, payload: dict[str, Any], queryer: int | None = None) -> dict[str, Any] | str:
    """
    获取用户数据，获取失败时返回字符串
    - `project` : 项目
        - `best` : 玩家数据
        - `plate` : 牌子
    - `payload` : 传递给查分器的数据
    - `queryer` : 查询者
    """
    if project == 'best':
        p = 'player'
    elif project == 'plate':
        p = 'plate'
    else:
        raise ValueError

    if 'qq' in payload and queryer != payload['qq'] and not query_privacy(payload['qq']):
        return '该用户禁止了其他人获取数据。'

    try:
        async with aiohttp.request('POST', f'https://www.diving-fish.com/api/maimaidxprober/query/{p}', json=payload) as response:
            if response.status == 400:
                return (
                    '未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。\n'
                    '如未绑定，请前往查分器官网进行绑定\n'
                    'https://www.diving-fish.com/maimaidx/prober/\n'
                )
            if response.status == 403:
                return '该用户禁止了其他人获取数据。'
            if response.status == 200:
                return await response.json()
            return '未知错误，请联系BOT管理员'
    except Exception as e:
        # log.error(f'Error: {traceback.print_exc()}')
        return f'获取玩家数据时发生错误，请联系BOT管理员: {type(e)}'


async def get_rating_ranking_data() -> list[dict[str, Any]] | str:
    """
    获取排名，获取失败时返回字符串
    """
    try:
        async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/rating_ranking') as resp:
            if resp.status != 200:
                return '未知错误，请联系BOT管理员'
            return await resp.json()
    except Exception as e:
        # log.error(f'Error: {traceback.print_exc()}')
        return f'获取排名时发生错误，请联系BOT管理员: {type(e)}'
