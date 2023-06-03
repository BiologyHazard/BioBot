import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.drivers import Driver
from nonebot.log import default_filter, default_format, logger


def main() -> None:
    logger.add('logs/bot_{time:YYYY-MM-DD}.log',
               level=0, rotation='00:00', format=default_format, filter=default_filter)
    nonebot.init()

    # app = nonebot.get_asgi()

    driver: Driver = nonebot.get_driver()
    driver.register_adapter(OneBotV11Adapter)
    # driver.config.help_text = {}

    # nonebot.load_plugin('nonebot_plugin_gocqhttp')
    nonebot.load_builtin_plugins('echo')
    nonebot.load_plugin('src.plugins.help')
    nonebot.load_plugin('src.plugins.maimai')
    # nonebot.load_plugin('src.plugins.autoreply')
    # nonebot.load_plugin('src.plugins.biliav')
    # nonebot.load_plugin('src.plugins.roll')
    # nonebot.load_plugin('src.plugins.poke')
    # nonebot.load_plugin('src.plugins.simplemusic')
    # nonebot.load_plugin('src.plugins.repeater')
    # nonebot.load_plugin('src.plugins.boardgame')
    # nonebot.load_plugin('src.plugins.text2sound')
    # nonebot.load_plugin('src.plugins.xxivgame')
    # nonebot.load_plugin('src.plugins.homo')
    # nonebot.load_plugin('src.plugins.mahjong')
    # nonebot.load_plugin('src.plugins.answersbook')
    # nonebot.load_plugin('src.plugins.tygj')
    # nonebot.load_plugin('src.plugins.revoke')
    # nonebot.load_plugin('src.plugins.ncm')
    # nonebot.load_plugin('src.plugins.abbreply')
    # nonebot.load_plugin('src.plugins.kfccrazythu')
    # nonebot.load_plugin('src.plugins.choose')
    # nonebot.load_plugin('src.plugins.wordle')
    # nonebot.load_plugin('src.plugins.memes')
    # nonebot.load_plugin('src.plugins.petpet')
    # # nonebot.load_plugin('src.plugins.wordcloud')

    # nonebot.load_plugin('nonebot_plugin_emojimix')
    # nonebot.load_plugin('nonebot_plugin_abstract')
    # nonebot.load_plugin('nonebot_plugin_makemidi')
    # nonebot.load_plugin('nonebot_plugin_wordcloud')

    # nonebot.load_plugins('src/plugins')]
    # nonebot.load_plugin('nonebot_plugin_help')
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
