import nonebot
from nonebot.adapters.onebot.v11 import Adapter
from nonebot.internal.driver import Driver


def main() -> None:
    nonebot.init()

    # app = nonebot.get_asgi()

    driver: Driver = nonebot.get_driver()
    driver.register_adapter(Adapter)
    # driver.config.help_text = {}

    # nonebot.load_plugin('nonebot_plugin_gocqhttp')
    nonebot.load_builtin_plugins('echo')

    nonebot.load_plugin('src.plugins.autoreply')
    nonebot.load_plugin('src.plugins.biliav')
    nonebot.load_plugin('src.plugins.roll')
    nonebot.load_plugin('src.plugins.poke')
    nonebot.load_plugin('src.plugins.simplemusic')
    nonebot.load_plugin('src.plugins.repeater')
    nonebot.load_plugin('src.plugins.maimai')
    nonebot.load_plugin('src.plugins.boardgame')
    nonebot.load_plugin('src.plugins.text2sound')
    nonebot.load_plugin('src.plugins.permission')
    # nonebot.load_plugin('src.plugins.wordcloud')

    # nonebot.load_plugin('src.plugins.phlogo')
    # nonebot.load_plugins('src/plugins')]

    nonebot.load_plugin('nonebot_plugin_help')
    nonebot.load_plugin('nonebot_plugin_emojimix')
    nonebot.load_plugin('nonebot_plugin_abstract')
    nonebot.load_plugin('nonebot_plugin_makemidi')
    nonebot.load_plugin('nonebot_plugin_wordcloud')
    # nonebot.load_plugin('nonebot_plugin_memes')
    # nonebot.load_plugin('nonebot_plugin_petpet')
    # nonebot.load_plugin('nonebot_plugin_txt2img')

    # nonebot.load_plugin('nonebot_plugin_treehelp')
    # nonebot.load_plugin('nonebot_plugin_boardgame')  # 有bug
    # nonebot.load_plugin('nonebot_plugin_admin')  # 有bug
    # nonebot.load_plugin('nonebot_plugin_backup')  # 有bug
    # nonebot.load_plugin('nonebot_plugin_bilicover')  # 有bug

    nonebot.run()


if __name__ == '__main__':
    main()
