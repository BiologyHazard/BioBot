import random
from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_State

answers_path: Path = Path(__file__).parent / "answersbook.txt"
answers: list[str] = answers_path.read_text("utf-8").splitlines()


def get_answers() -> str:
    return random.choice(answers)


look_answer: type[Matcher] = on_command("翻看答案")


@look_answer.handle()
async def answersbook(state: T_State, message: Message = CommandArg()) -> None:
    if message.extract_plain_text():
        state['has_arg'] = True


@look_answer.got('has_arg', '你想问什么问题呢？')
async def anwsersbook() -> None:
    answer: str = get_answers()
    await look_answer.finish(answer, reply_message=True)
