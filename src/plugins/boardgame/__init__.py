from nonebot import logger, on_command
from nonebot.adapters.onebot.v11 import (Bot, Event, GroupMessageEvent,
                                         Message, MessageSegment)
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata

from .boardgame import BoardGame, MoveResult, MoveSide, Pos
from .gomoku import Gomoku
from .image import image_to_message_segment
from .othello import Othello

__plugin_meta__ = PluginMetadata(
    name='棋类游戏',
    description='',
    usage=(
        ''
    )
)

games: dict[int, BoardGame] = {}
# game_players: dict[int, dict[int, str]] = defaultdict(list)

not_group_text: str = '仅限群聊中使用哦~'
game_already_started_text: str = '有正在进行中的游戏，发送“结束游戏”停止下棋'

start_gomoku = on_command('开始五子棋')
start_othello = on_command('开始黑白棋')
place = on_command('落子')
repent = on_command('悔棋')
skip = on_command('跳过回合')
stop_game = on_command('停止下棋', aliases={'停止游戏', '结束游戏'})


# def game_running(group_id: int, user_id: int) -> bool:
# return (group_id in game_players) and (user_id in game_players[group_id])
def game_running(group_id: int) -> bool:
    return group_id in games


@start_gomoku.handle()
async def start_gomuku_func(bot: Bot, event: Event, message: Message = CommandArg()):
    if not isinstance(event, GroupMessageEvent):
        await start_gomoku.finish(not_group_text)

    if game_running(event.group_id):
        await start_gomoku.finish(game_already_started_text)

    game: Gomoku = Gomoku()
    games[event.group_id] = game
    await start_gomoku.finish(image_to_message_segment(game.draw()))


@start_othello.handle()
async def start_othello_func(bot: Bot, event: Event, message: Message = CommandArg()):
    if not isinstance(event, GroupMessageEvent):
        await start_gomoku.finish(not_group_text)

    if game_running(event.group_id):
        await start_gomoku.finish(game_already_started_text)

    game: Othello = Othello()
    games[event.group_id] = game
    await start_gomoku.finish(image_to_message_segment(game.draw()))


@place.handle()
async def place_func(bot: Bot, event: Event, message: Message = CommandArg()):
    if not isinstance(event, GroupMessageEvent):
        await start_gomoku.finish(not_group_text)

    try:
        pos: Pos = Pos.from_str(str(message))
    except ValueError:
        await place.finish('无法解析的落子坐标！使用例：落子 H4')

    if event.group_id not in games:
        await place.finish('游戏未开始，发送“开始五子棋/开始黑白棋”开始游戏')

    game: BoardGame = games[event.group_id]
    if (game.moveside == MoveSide.BLACK) and (not game.player_black):
        game.player_black = event.user_id
        await place.send('您已加入游戏，您是黑方', at_sender=True)
        logger.trace(repr(game.player_black))

    if (game.moveside == MoveSide.WHITE) and (not game.player_white):
        game.player_white = event.user_id
        await place.send('您已加入游戏，您是白方', at_sender=True)
        logger.trace(repr(game.player_white))

    if (((game.moveside == MoveSide.BLACK) and (game.player_black != event.user_id))
            or ((game.moveside == MoveSide.WHITE) and (game.player_white != event.user_id))):
        await place.finish('请等待当前游戏结束之后再加入游戏', at_sender=True)

    if not game.in_range(pos):
        await place.finish('落子超出边界')

    if game.get(pos) != 0:
        await place.finish('此处已有落子')

    move_result = game.update(pos)
    if move_result == MoveResult.BLACK_WIN:
        await place.finish(Message(['黑方获胜！', image_to_message_segment(game.draw())]))  # type: ignore
    elif move_result == MoveResult.WHITE_WIN:
        await place.finish(Message(['白方获胜！', image_to_message_segment(game.draw())]))  # type: ignore
    else:
        await place.send(image_to_message_segment(game.draw()))
        await place.send(['下一手轮到', MoveSide.zh_hans[game.moveside], '方', MessageSegment.at(game.player_next) if game.player_next else '，发送“落子 <坐标>”加入游戏'])  # type: ignore


@repent.handle()
async def repent_func(bot: Bot, event: Event, message: Message = CommandArg()):
    if not isinstance(event, GroupMessageEvent):
        await repent.finish(not_group_text)

    if event.group_id not in games:
        await repent.finish('游戏未开始，发送“开始五子棋”开始游戏')

    game: BoardGame = games[event.group_id]
    if len(game.history) <= 1:
        await repent.finish('请落子后再悔棋！')

    if game.player_last != event.user_id:
        await repent.finish('上一手棋不是你所下')

    game.pop()
    await repent.finish(image_to_message_segment(game.draw()))


@stop_game.handle()
async def stop_game_func(bot: Bot, event: Event, message: Message = CommandArg()):
    if not isinstance(event, GroupMessageEvent):
        await stop_game.finish(not_group_text)

    if event.group_id not in games:
        await stop_game.finish('游戏未开始，发送“开始五子棋”开始游戏')

    del games[event.group_id]
    await stop_game.finish('游戏已结束')
