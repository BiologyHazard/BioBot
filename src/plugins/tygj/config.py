from nonebot import get_driver, logger
from pathlib import Path

config: dict = get_driver().config.dict()
DEFAULT_DATA_PATH: str = "data/tygj/tygj.json"

data_path = config.get('tygj_data_path', DEFAULT_DATA_PATH)
if not isinstance(data_path, str):
    logger.warning(f"Data path must be type 'str', falling back to '{DEFAULT_DATA_PATH}'.")
    data_path = DEFAULT_DATA_PATH
data_path = Path(data_path)
