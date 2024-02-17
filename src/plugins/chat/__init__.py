from nonebot import MatcherGroup, logger
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.params import CommandArg, CommandStart, EventToMe, Command
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .manager import Session, sessions

__plugin_meta__: PluginMetadata = PluginMetadata(
    name='Chat with AI',
    description='和生成式人工智能聊天',
    usage=(
        '· #chat <内容>  # 和AI聊天，默认模型为通义千问（qwen-max）\n'
        '· #<模型> <内容>  # 以指定模型和AI聊天\n'
        '· 回复AI的消息并发送“#<模型> <内容>”  # 从回复的地方继续对话\n'
        '\n'
        '支持的模型有：\n'
        '· qwen-turbo\n'
        '· qwen-plus\n'
        '· qwen-max\n'
        '· qwen-max-1201\n'
        '· qwen-max-longcontext\n'
        '· spark\n'
    )
)


@Rule
def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me


models = {
    'qwen-turbo': 'qwen-turbo',
    'qwen-plus': 'qwen-plus',
    'qwen-max': 'qwen-max',
    'qwen-max-1201': 'qwen-max-1201',
    'qwen-max-longcontext': 'qwen-max-longcontext',
    'spark': 'spark',
    '通义千问': 'qwen-max',
    '通义': 'qwen-max',
    '千问': 'qwen-max',
    '讯飞星火': 'spark',
    '讯飞': 'spark',
    '星火': 'spark',
}
chat_command_group = MatcherGroup(rule=with_command_start_or_to_me, block=False, priority=5)
chat = chat_command_group.on_command('chat', aliases=set(models.keys()), force_whitespace=True)


@chat.handle()
async def chat_func(bot: Bot, event: MessageEvent, message: Message = CommandArg(), command: tuple[str, ...] = Command()):
    command_str = '.'.join(command)
    message_plain_text = message.extract_plain_text()
    session = Session()
    if reply_segments := event.original_message['reply']:
        reply_segment: MessageSegment = reply_segments[0]
        reply_message_id = int(reply_segment.data['id'])
        if reply_message_id in sessions:
            session = sessions[reply_message_id]
        else:
            await chat.send('您回复的消息可能不是 Chat 的回答，已改为发起新的会话。\n'
                            '如果您认为这是一个错误，请联系管理员。')

    answer, session = await session.get_reply(message_plain_text, models.get(command_str, 'qwen-max'))
    if answer['code'] == 0:
        content = answer['data']['content']
        content = (f'您可以回复任意一条 Chat 的回答，并发送“#{command_str} <下一个问题>”，可以从回复的地方继续对话。\n'
                   f'若要开启新的对话，请直接发送“#{command_str} <问题>”。\n'
                   '以下内容由 AI 生成。\n'
                   '======\n'
                   f'{content}')
        send_result = await chat.send(content, reply_message=True)
        message_id = send_result['message_id']
        sessions[message_id] = session
        # logger.info(sessions)
    else:
        await chat.finish(f'出现错误，错误码：{answer["code"]}，错误信息：{answer["message"]}，请联系管理员。', reply_message=True)
