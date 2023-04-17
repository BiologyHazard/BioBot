from nonebot import get_driver, logger

config: dict = get_driver().config.dict()
# global_nickname = config.get('nickname')
DEFAULT_DATA_PATH: str = "data/autoreply"

data_path = config.get('autoreply_data_path', DEFAULT_DATA_PATH)
if not isinstance(data_path, str):
    logger.warning(f"Data path must be type 'str', falling back to '{DEFAULT_DATA_PATH}'.")
    data_path: str = DEFAULT_DATA_PATH
