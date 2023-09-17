from nonebot import get_driver
from pydantic import BaseModel


class Config(BaseModel):
    forward_friend_request: bool = True
    forward_group_request: bool = True
    forward_to: set[str] = {'$SUPERUSERS'}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


plugin_config: Config = Config.parse_obj(get_driver().config)
forward_to_expanded: set[int] = {int(user) for user in plugin_config.forward_to if user.isdigit()}
if any(user.upper() == '$SUPERUSERS' for user in plugin_config.forward_to):
    forward_to_expanded |= {int(superuser) for superuser in get_driver().config.superusers}
