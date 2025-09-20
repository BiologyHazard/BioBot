import asyncio
from typing import Any

from nonebot import MatcherGroup, get_driver, logger, require
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .app import app
from .assistant import 森空岛实时数据分析, 森空岛干员阵容查询
from .config import plugin_config
from .image import image_to_bytesio, text_to_image
from .manager import tokens
from .skland import TOKEN_LENGTH, SKLand, SKLandError, attendance_and_send_email
from .utils import get_qq_mail_address, is_base64

require('nonebot_plugin_apscheduler')

from nonebot_plugin_apscheduler import scheduler  # NOQA: E402

driver: Driver = get_driver()
default_command_start: str = tuple(driver.config.command_start)[0]

help_str: str = f'''
【如何使用】
方法一：点击下面链接，按照提示操作
http://{plugin_config.server}/BioBot/plugins/sklassistant/
方法二：点击上面链接查看如何获取森空岛token，
然后添加bot为好友，私聊发送“{default_command_start}绑定森空岛token <token>”

【如何暂时关闭/开启自动签到】
群聊/私聊发送“{default_command_start}关闭/开启森空岛自动签到”

【其他命令】
- {default_command_start}森空岛小秘书 <uid>    # 查看森空岛小秘书的功能
- {default_command_start}森空岛干员阵容查询 <uid>    # 查询森空岛干员阵容

# 为了您的账号安全，请不要在群聊中直接发送token！
'''.strip()


__plugin_meta__ = PluginMetadata(
    name='森空岛小助手',
    description='明日方舟森空岛自动签到工具，可以在每日00:00自动签到，并发送邮件提醒。',
    usage=help_str
)

matcher_group = MatcherGroup(priority=1)
bind_skl_token = matcher_group.on_command('绑定森空岛token')
skl_auto_sign_in = matcher_group.on_keyword({'森空岛自动签到'})
skl_assistant = matcher_group.on_command('森空岛小秘书', aliases={'森空岛助手', '森空岛小助手'})
skl_query = matcher_group.on_command('森空岛查询', aliases={'森空岛干员阵容查询'})
skl_attendance_all = matcher_group.on_command('森空岛签到全部', permission=SUPERUSER)


@scheduler.scheduled_job('cron', hour=0)
# @driver.on_startup
async def skl_sign_in_all() -> list[dict[str, Any] | BaseException]:
    logger.info('开始森空岛自动签到')
    tasks = [attendance_and_send_email(item['token'], item['remind'], item['email'])
             for item in tokens if item['enabled']]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        logger.info(repr(result))
    return results


@driver.on_startup
async def run_app() -> None:
    asyncio.get_event_loop().create_task(app.run_task('0.0.0.0', 80))


@bind_skl_token.handle()
async def bind_skl_token_func(event: MessageEvent, message: Message = CommandArg()) -> None:
    token: str = message.extract_plain_text().strip()
    if not token:
        await bind_skl_token.finish(help_str)

    if not (len(token) == TOKEN_LENGTH and is_base64(token)):
        await bind_skl_token.finish('token格式错误。')

    if tokens.has_token(token):
        await bind_skl_token.finish('token已存在。')

    try:
        await SKLand().login_by_token(token)
    except Exception as e:
        await bind_skl_token.finish(f'绑定森空岛token失败：{e}')

    tokens.add_item(event.user_id, get_qq_mail_address(event.user_id), token)
    await bind_skl_token.send('成功绑定森空岛token。立即进行一次签到。\n'
                              '已为您开启自动签到和邮件提醒，以后将于每日00:00签到。\n'
                              '如暂时不需要开启，请发送“关闭森空岛自动签到”。')

    result: dict[str, Any] = await attendance_and_send_email(token, True, get_qq_mail_address(event.user_id))
    await skl_auto_sign_in.finish(result['msg'])


@skl_auto_sign_in.handle()
async def skl_auto_sign_in_func(event: MessageEvent, message: str = EventPlainText()) -> None:
    if '关闭' in message:
        enable: bool = False
    elif '开启' in message:
        enable = True
    else:
        await skl_auto_sign_in.finish()

    if not tokens.filter(qq=event.user_id):
        await skl_auto_sign_in.finish('请先绑定森空岛token。')

    tokens.set_enable_state('qq', event.user_id, enable)

    if enable:
        await skl_auto_sign_in.send('已开启森空岛自动签到。立即进行一次签到。以后将于每日00:00签到。')
        tasks = (attendance_and_send_email(item['token'], True, item['email'])
                 for item in tokens if item['qq'] == event.user_id)
        results: list[dict[str, Any] | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)
        await skl_auto_sign_in.finish(
            '\n'.join(result['msg'] if isinstance(result, dict) else repr(result)
                      for result in results)
        )
    else:
        await skl_auto_sign_in.finish('已关闭森空岛自动签到。')


@skl_assistant.handle()
@skl_query.handle()
async def skl_assistant_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    uid: str | None = message.extract_plain_text().strip()
    if not uid.isdigit():
        uid = None

    token_list = tokens.filter(qq=event.user_id)
    if not token_list:
        await skl_assistant.finish('请先绑定森空岛token。')

    exception = None
    for item in token_list:
        token = item['token']
        try:
            if type(matcher) is skl_assistant:
                result: str = await 森空岛实时数据分析(token, uid)
            else:
                result = await 森空岛干员阵容查询(token, uid)
        except Exception as e:
            exception = e
        else:
            if len(result) > 512:
                await skl_assistant.finish(MessageSegment.image(image_to_bytesio(text_to_image(result))))
            await skl_assistant.finish(result)

    if isinstance(exception, SKLandError):
        await skl_assistant.send(str(exception))
    else:
        await skl_assistant.send(repr(exception))

    raise exception


@skl_attendance_all.handle()
async def skl_attendance_all_func() -> None:
    results = await skl_sign_in_all()
    await skl_attendance_all.finish('\n'.join(repr(result) for result in results))
