from typing import ClassVar

from .boardgame import BoardGame, MoveResult, Piece, Placement, Pos


class Go(BoardGame):
    """围棋游戏，支持 9/13/19 路棋盘，含提子与禁入点规则。"""

    star_position_map: ClassVar[dict[int, list[Pos]]] = {
        9: [Pos(2, 2), Pos(2, 6), Pos(4, 4), Pos(6, 2), Pos(6, 6)],
        13: [Pos(3, 3), Pos(3, 9), Pos(6, 6), Pos(9, 3), Pos(9, 9)],
        19: [
            Pos(3, 3),
            Pos(3, 9),
            Pos(3, 15),
            Pos(9, 3),
            Pos(9, 9),
            Pos(9, 15),
            Pos(15, 3),
            Pos(15, 9),
            Pos(15, 15),
        ],
    }

    def __init__(self, width: int, height: int):
        """初始化围棋棋局。"""
        star_positions = (
            self.star_position_map.get(width, []) if width == height else []
        )
        super().__init__(
            width=width,
            height=height,
            placement=Placement.CROSS,
            star_positions=star_positions,
        )
        self._pass_count: int = 0

    def _neighbors(self, pos: Pos) -> list[Pos]:
        """返回 pos 的上下左右四个相邻且在棋盘内的坐标。"""
        candidates = [
            Pos(pos.x - 1, pos.y),
            Pos(pos.x + 1, pos.y),
            Pos(pos.x, pos.y - 1),
            Pos(pos.x, pos.y + 1),
        ]
        return [p for p in candidates if self.in_range(p)]

    def _get_group(self, pos: Pos) -> set[Pos]:
        """用 BFS 找出与 pos 同色且相连的所有棋子坐标。"""
        color = self.get(pos)
        group: set[Pos] = set()
        queue = [pos]
        while queue:
            cur = queue.pop()
            if cur in group:
                continue
            group.add(cur)
            for nb in self._neighbors(cur):
                if nb not in group and self.get(nb) == color:
                    queue.append(nb)
        return group

    def _get_liberties(self, group: set[Pos]) -> set[Pos]:
        """返回棋组的所有气（相邻空点）。"""
        liberties: set[Pos] = set()
        for pos in group:
            for nb in self._neighbors(pos):
                if self.get(nb) == Piece.EMPTY:
                    liberties.add(nb)
        return liberties

    def _capture_group(self, group: set[Pos]) -> None:
        """提掉棋组中所有棋子（置为空）。"""
        for pos in group:
            self._set(pos, Piece.EMPTY)

    def update(self, pos: Pos | None) -> tuple[MoveResult, str]:
        """在指定坐标落子或跳过回合。

        Args:
            pos: 要落子的位置，或 None 表示跳过回合（PASS）。

        Returns:
            落子结果以及非法落子时的提示信息。
        """

        # PASS 操作（跳过回合）
        if pos is None:
            self._pass_count += 1
            self.next_move_side = self.next_move_side.flip()
            self._positions.append(pos)
            self._save()

            if self._pass_count >= 2:
                return MoveResult.DRAW, ""
            return MoveResult.CONTINUE, ""

        if not self.in_range(pos):
            return MoveResult.ILLEGAL, "落子超过边界"

        if self.get(pos) != Piece.EMPTY:
            return MoveResult.ILLEGAL, "此处已有落子"

        my_piece = Piece.from_move_side(self.next_move_side)
        opp_piece = my_piece.flip()

        # 暂时落子
        self._set(pos, my_piece)

        # 提掉周围无气的对方棋组
        for nb in self._neighbors(pos):
            if self.get(nb) == opp_piece:
                opp_group = self._get_group(nb)
                if not self._get_liberties(opp_group):
                    self._capture_group(opp_group)

        # 检查自己落子后是否有气（禁入点判断）
        my_group = self._get_group(pos)
        if not self._get_liberties(my_group):
            # 回滚棋盘状态
            self._b_board = self._history[-1].b_board
            self._w_board = self._history[-1].w_board
            return MoveResult.ILLEGAL, "自杀禁入"

        # 检查禁止全局同形
        new_next_move_side = self.next_move_side.flip()
        for history in self._history:
            if (
                history.b_board == self._b_board
                and history.w_board == self._w_board
                and history.next_move_side == new_next_move_side
            ):
                # 回滚棋盘状态
                self._b_board = self._history[-1].b_board
                self._w_board = self._history[-1].w_board
                return MoveResult.ILLEGAL, "禁止全局同形"

        # 合法落子：切换行棋方并保存历史
        self.next_move_side = self.next_move_side.flip()
        self._positions.append(pos)
        self._save()
        self._pass_count = 0

        if self.is_full():
            return MoveResult.DRAW, ""

        return MoveResult.CONTINUE, ""
