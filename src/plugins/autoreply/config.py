from nonebot import get_driver

config: dict = get_driver().config.dict()
# global_nickname = config.get('nickname')

data_path: str = 'data/autoreply'
superusers = config.get('superusers', set())
if isinstance(superusers, str):
    superusers: set = {superusers}
