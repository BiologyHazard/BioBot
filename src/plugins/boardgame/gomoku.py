from .boardgame import (
    BoardGame,
    MoveResult,
    MoveSide,
    Piece,
    Placement,
    Pos,
)


class Gomoku(BoardGame):
    """五子棋游戏，15x15 棋盘，落于交叉点，五子连珠者获胜。"""

    def __init__(self):
        """初始化 15x15 五子棋棋局。"""
        super().__init__(
            size=15,
            placement=Placement.CROSS,
            star_positions=[
                Pos(3, 3),
                Pos(3, 11),
                Pos(7, 7),
                Pos(11, 3),
                Pos(11, 11),
            ],
        )

    def _count_direction(self, pos: Pos, dx: int, dy: int, piece_state: Piece) -> int:
        """计算某个方向上相同棋子的连续数量（包括当前位置）。"""
        count = 0
        # 往负方向检查
        x, y = pos.x, pos.y
        while self.in_range(Pos(x, y)) and self.get(Pos(x, y)) == piece_state:
            count += 1
            x -= dx
            y -= dy
        # 往正方向检查（不包括当前位置）
        x, y = pos.x + dx, pos.y + dy
        while self.in_range(Pos(x, y)) and self.get(Pos(x, y)) == piece_state:
            count += 1
            x += dx
            y += dy
        return count

    def update(self, pos: Pos | None) -> tuple[MoveResult, str]:
        """在指定坐标落子，判断是否形成五子连珠或棋盘已满。

        Returns:
            黑/白方获胜返回对应 MoveResult，平局返回 MoveResult.DRAW，游戏继续返回 MoveResult.CONTINUE。
        """
        if pos is None:
            return MoveResult.ILLEGAL, "五子棋不允许跳过回合"

        if not self.in_range(pos):
            return MoveResult.ILLEGAL, "落子超出边界"

        if self.get(pos) != Piece.EMPTY:
            return MoveResult.ILLEGAL, "此处已有落子"

        self._push(pos)
        last_player = self.next_move_side.flip()
        piece_state = Piece.from_move_side(last_player)

        # 检查四个方向：竖直、水平、主对角线、副对角线
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            if self._count_direction(pos, dx, dy, piece_state) >= 5:
                return (
                    (MoveResult.BLACK_WIN, "")
                    if last_player == MoveSide.BLACK
                    else (MoveResult.WHITE_WIN, "")
                )

        if self.is_full():
            return MoveResult.DRAW, ""
        return MoveResult.CONTINUE, ""
