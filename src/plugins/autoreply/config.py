from nonebot import get_driver

config: dict = get_driver().config.dict()
# global_nickname = config.get('nickname')
DEFAULT_DATA_PATH: str = "data/autoreply"

data_path = config.get('autoreply_data_path', DEFAULT_DATA_PATH)
assert isinstance(data_path, str)

# superusers = config.get('superusers', set())
# if isinstance(superusers, str):
#     superusers: set = {superusers}
