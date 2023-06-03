import aiohttp
from typing import Any
from .privacy import query_privacy

player_error: str = '''
未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。
如未绑定，请前往查分器官网进行绑定
https://www.diving-fish.com/maimaidx/prober/
'''.strip()


async def get_player_data(project: str, payload: dict[str, Any], queryer: int) -> dict[str, Any] | str:
    """
    获取用户数据，获取失败时返回字符串
    - `project` : 项目
        - `best` : 玩家数据
        - `plate` : 牌子
    - `payload` : 传递给查分器的数据
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
            elif response.status == 403:
                return '该用户禁止了其他人获取数据。'
            elif response.status == 200:
                return await response.json()
            else:
                return '未知错误，请联系BOT管理员'
    except Exception as e:
        # log.error(f'Error: {traceback.print_exc()}')
        return f'获取玩家数据时发生错误，请联系BOT管理员: {type(e)}'


async def get_rating_ranking_data() -> dict | str:
    """
    获取排名，获取失败时返回字符串
    """
    try:
        async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/rating_ranking') as resp:
            if resp.status != 200:
                data = '未知错误，请联系BOT管理员'
            else:
                data = await resp.json()
    except Exception as e:
        # log.error(f'Error: {traceback.print_exc()}')
        data = f'获取排名时发生错误，请联系BOT管理员: {type(e)}'
    return data
