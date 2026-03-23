from .boardgame import (
    BoardGame,
    MoveResult,
    MoveSide,
    Piece,
    Placement,
    Pos,
)


class Othello(BoardGame):
    """黑白棋游戏，8x8 棋盘，落于格子内。"""

    def __init__(self):
        """初始化 8x8 黑白棋棋局，并采用标准开局布局。"""
        width = height = 8
        super().__init__(width=width, height=height, placement=Placement.GRID)

        mid_x = width // 2
        mid_y = height // 2
        self._set(Pos(mid_x - 1, mid_y - 1), Piece.WHITE)
        self._set(Pos(mid_x - 1, mid_y), Piece.BLACK)
        self._set(Pos(mid_x, mid_y - 1), Piece.BLACK)
        self._set(Pos(mid_x, mid_y), Piece.WHITE)
        self._history.pop()
        self._save()

    def flip_poses(self, pos: Pos, move_side: MoveSide) -> list[Pos]:
        """计算在 `pos` 位置落子时，`move_side` 方将翻转的所有对方棋子的位置列表。

        Returns:
            所有可被翻转的棋子位置列表，若该落点非法则返回空列表。
        """
        delta = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))

        flipped = []
        our_piece = Piece.from_move_side(move_side)
        opponent_piece = Piece.from_move_side(move_side.flip())

        for dx, dy in delta:
            p = Pos(pos.x + dx, pos.y + dy)
            if not self.in_range(p) or self.get(p) != opponent_piece:
                continue
            temp = []
            while True:
                temp.append(p)
                p = Pos(p.x + dx, p.y + dy)
                if not self.in_range(p) or self.get(p) != opponent_piece:
                    break
            if self.in_range(p) and self.get(p) == our_piece:
                flipped.extend(temp)
        return flipped

    def has_legal_move(self, move_side: MoveSide) -> bool:
        """判断 `move_side` 方在当前棋盘上是否存在合法落点。"""
        for i in range(self.width):
            for j in range(self.height):
                p = Pos(i, j)
                if self.get(p) == Piece.EMPTY and self.flip_poses(p, move_side):
                    return True
        return False

    def check(self) -> MoveResult:
        """统计双方棋子数量，返回当前领先方的胜负结果。"""

        b_count = self._b_board.bit_count()
        w_count = self._w_board.bit_count()

        if b_count > w_count:
            return MoveResult.BLACK_WIN
        elif b_count < w_count:
            return MoveResult.WHITE_WIN
        else:
            return MoveResult.DRAW

    def update(self, pos: Pos | None):
        """在指定坐标落子，翻转夹住的对方棋子，并判断游戏是否结束。"""

        if pos is None:
            return MoveResult.ILLEGAL, "黑白棋不允许跳过回合"

        if not self.in_range(pos):
            return MoveResult.ILLEGAL, "落子超出边界"

        if self.get(pos) != Piece.EMPTY:
            return MoveResult.ILLEGAL, "此处已有落子"

        # 获取要翻转的棋子列表，若列表为空则表示该落点非法
        flipped_pieces = self.flip_poses(pos, self.next_move_side)
        if not flipped_pieces:
            return MoveResult.ILLEGAL, "该位置无法落子"

        # 翻转所有被夹住的棋子
        for p in flipped_pieces:
            self._set(p, Piece.from_move_side(self.next_move_side))

        # 落子并更新棋盘状态
        self._push(pos)

        # 如果棋盘已满则游戏结束
        if self.is_full():
            return self.check(), ""

        # 判断对方是否有合法落点
        current_side = self.next_move_side.flip()
        next_side = self.next_move_side  # self.moveside 已经在 _push 中翻转了
        if not self.has_legal_move(next_side):
            if not self.has_legal_move(current_side):
                # 双方都无法落子则游戏结束
                return self.check(), ""

            # 对方无法落子，自己可以落子则继续由当前玩家落子
            self.next_move_side = current_side
            return MoveResult.CONTINUE, ""

        # 正常情况下轮到对方落子
        return MoveResult.CONTINUE, ""
