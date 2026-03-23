from typing import Annotated

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Event,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .boardgame import BoardGame, MoveResult, Pos
from .go import Go
from .gomoku import Gomoku
from .image import image_to_message_segment
from .othello import Othello

__plugin_meta__ = PluginMetadata(
    name="棋类游戏",
    description="和群友下围棋 / 五子棋 / 黑白棋",
    usage=(
        "· 开始围棋 19  # 开始 19x19 围棋\n"
        "· 开始五子棋\n"
        "· 开始黑白棋\n"
        "· 落子 <坐标>  # 使用例：落子 H4\n"
        "· 悔棋\n"
        "· 跳过回合\n"
        "· 停止下棋"
    ),
)

games: dict[int, BoardGame] = {}

not_group_text = "仅限群聊中使用哦~"
start_go = on_command("开始围棋")
start_gomoku = on_command("开始五子棋")
start_othello = on_command("开始黑白棋")
place = on_command("落子")
repent = on_command("悔棋")
skip = on_command(
    "跳过回合", aliases={"跳过", "停一手", "虚手", "pass", "PASS", "Pass"}
)
stop_game = on_command("停止下棋", aliases={"停止游戏", "结束游戏"})


def game_running(group_id: int) -> bool:
    return group_id in games


@start_go.handle()
@start_gomoku.handle()
@start_othello.handle()
async def start_game_func(
    matcher: Matcher, event: Event, message: Annotated[Message, CommandArg()]
):
    if not isinstance(event, GroupMessageEvent):
        await matcher.finish(not_group_text)

    if game_running(event.group_id):
        await matcher.finish("有正在进行中的游戏，发送“结束游戏”停止下棋")

    if isinstance(matcher, start_go):
        arg = message.extract_plain_text().strip()
        try:
            if "x" in arg:
                width, height = map(int, arg.split("x"))
            elif "*" in arg:
                width, height = map(int, arg.split("*"))
            else:
                width = height = int(arg) if arg else 19
        except ValueError:
            width = height = 19  # 默认棋盘大小

        if not (1 <= width <= 25 and 1 <= height <= 25):
            await matcher.finish("棋盘尺寸必须在 1 到 25 之间")
        game = Go(width, height)
    elif isinstance(matcher, start_gomoku):
        game = Gomoku()
    elif isinstance(matcher, start_othello):
        game = Othello()
    else:
        raise ValueError("未知的游戏类型")

    games[event.group_id] = game
    await matcher.send(image_to_message_segment(game.draw()))
    await matcher.send("游戏已开始，发送“落子 <坐标>”加入游戏")


@place.handle()
@skip.handle()
async def place_func(
    matcher: Matcher, event: Event, message: Annotated[Message, CommandArg()]
):
    if not isinstance(event, GroupMessageEvent):
        await matcher.finish(not_group_text)

    # 解析参数（落子坐标或跳过回合）
    if isinstance(matcher, skip):
        pos = None  # 跳过回合使用 None 表示
    else:
        try:
            pos = Pos.from_str(message.extract_plain_text().strip())
        except ValueError:
            await matcher.finish("无法解析的落子坐标！使用例：落子 H4")

    if event.group_id not in games:  # 检查是否有正在进行的游戏
        await matcher.finish(
            "游戏未开始，发送“开始围棋 / 开始五子棋 / 开始黑白棋”开始游戏"
        )

    # 获取当前游戏实例
    game: BoardGame = games[event.group_id]

    # 新玩家加入游戏
    if game.player_id[game.next_move_side] is None:
        game.player_id[game.next_move_side] = event.user_id
        await matcher.send(
            f"您已加入游戏，您是{game.next_move_side.zh_hans}方", at_sender=True
        )

    # 非当前玩家尝试落子
    if event.user_id not in game.player_id.values():
        await matcher.finish("请等待当前游戏结束之后再加入游戏", at_sender=True)

    # 检查是否轮到当前玩家落子
    if game.player_id[game.next_move_side] != event.user_id:
        await matcher.finish("当前不是您的回合", at_sender=True)

    # 执行落子或跳过回合操作，并获取结果
    move_result, illegal_message = game.update(pos)

    # 处理非法落子
    if move_result == MoveResult.ILLEGAL:
        await matcher.finish(illegal_message, at_sender=True)

    # 处理合法落子
    if move_result == MoveResult.BLACK_WIN:
        await matcher.send(image_to_message_segment(game.draw(show_move_numbers=True)))
        await matcher.finish("黑方获胜！")

    elif move_result == MoveResult.WHITE_WIN:
        await matcher.send(image_to_message_segment(game.draw(show_move_numbers=True)))
        await matcher.finish("白方获胜！")

    elif move_result == MoveResult.DRAW:
        await matcher.send(image_to_message_segment(game.draw(show_move_numbers=True)))
        await matcher.finish("平局！")

    elif move_result == MoveResult.CONTINUE:
        await matcher.send(image_to_message_segment(game.draw(show_move_numbers=False)))
        await matcher.send(
            [
                "下一手轮到",
                game.next_move_side.zh_hans,
                "方",
                MessageSegment.at(game.player_next)
                if game.player_next
                else "，发送“落子 <坐标>”加入游戏",
            ]  # type: ignore
        )


@repent.handle()
async def repent_func(event: Event):
    if not isinstance(event, GroupMessageEvent):
        await repent.finish(not_group_text)

    if event.group_id not in games:
        await repent.finish(
            "游戏未开始，发送“开始围棋 / 开始五子棋 / 开始黑白棋”开始游戏"
        )

    game: BoardGame = games[event.group_id]
    if len(game._history) <= 1:
        await repent.finish("请落子后再悔棋！")

    if game.player_last != event.user_id:
        await repent.finish("上一手棋不是你所下")

    game.repent()
    await repent.send(image_to_message_segment(game.draw()))
    await repent.send(
        [
            "下一手轮到",
            game.next_move_side.zh_hans,
            "方",
            MessageSegment.at(game.player_next)
            if game.player_next
            else "，发送“落子 <坐标>”加入游戏",
        ]  # type: ignore
    )


@stop_game.handle()
async def stop_game_func(event: Event, message: Annotated[Message, CommandArg()]):
    if not isinstance(event, GroupMessageEvent):
        await stop_game.finish(not_group_text)

    if event.group_id not in games:
        await stop_game.finish(
            "游戏未开始，发送“开始围棋 / 开始五子棋 / 开始黑白棋”开始游戏"
        )

    del games[event.group_id]
    await stop_game.finish("游戏已结束")
