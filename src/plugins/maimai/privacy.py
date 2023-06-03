import json

from .config import plugin_config

if (plugin_config.data_path / 'privacy.json').is_file():
    disabled_users: list[int] = json.loads((plugin_config.data_path / 'privacy.json').read_text('utf-8'))
else:
    disabled_users = []


def set_privacy(user_id: int, enable: bool) -> None:
    save: bool = False
    if enable:
        if user_id in disabled_users:
            disabled_users.remove(user_id)
            save = True
    else:
        if user_id not in disabled_users:
            disabled_users.append(user_id)
            save = True
    if save:
        (plugin_config.data_path / 'privacy.json').write_text(json.dumps(disabled_users), 'utf-8')


def query_privacy(user_id: int) -> bool:
    return not user_id in disabled_users
