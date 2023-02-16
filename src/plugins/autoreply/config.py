from nonebot import get_driver

config = get_driver().config.dict()
# global_nickname = config.get('nickname')

data_path = 'data/autoreply'
superusers = config.get('superusers', set())
if isinstance(superusers, str):
    superusers = {superusers}
