import random
from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventMessage
from nonebot.typing import T_State

answers_path: Path = Path(__file__).parent / "answersbook.txt"
answers: list[str] = answers_path.read_text("utf-8").splitlines()


def get_answers() -> str:
    return random.choice(answers)


look_answer: type[Matcher] = on_command("翻看答案")


@look_answer.handle()
async def answersbook(matcher: Matcher,
                      state: T_State,
                      event: MessageEvent,
                      command_arg: Message = CommandArg(),
                      event_message: Message = EventMessage()) -> None:
    state['user_id'] = event.user_id
    if event_message[0].type == 'reply':
        state['reply'] = event_message[0].data['id']
    if command_arg.extract_plain_text():
        matcher.set_arg('question', command_arg)


@look_answer.got('question', Message.template('{user_id:at}你想问什么问题呢？'))
async def anwsersbook(state: T_State, event: MessageEvent) -> None:
    answer: str = get_answers()
    if 'reply' in state:
        reply: int = state['reply']
    else:
        reply = event.message_id
    await look_answer.finish(Message([MessageSegment.reply(reply), MessageSegment.text(answer)]))
