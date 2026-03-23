from __future__ import annotations

import math
import re
import string
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Literal, NamedTuple

from PIL import Image, ImageDraw, ImageFont

from .config import plugin_config

type Point = tuple[float, float]
type XY = tuple[Point, Point]


def num_to_letter(num: int) -> str:
    """将非负整数转换为大写字母（0 → 'A'，25 → 'Z'，26 → 'AA'，51 → 'AZ'，…）。"""
    if num < 0:
        raise ValueError
    result = ""
    n = num + 1  # 转换为 1-based
    while n > 0:
        n -= 1
        result = string.ascii_uppercase[n % 26] + result
        n //= 26
    return result


def letter_to_num(letter: str) -> int:
    """将字母转换为对应的 0-based 整数（'A'/'a' → 0，'Z'/'z' → 25，'AA'/'aa' → 26，'AZ'/'az' → 51，…）。"""
    upper = letter.upper()
    if not all(c in string.ascii_uppercase for c in upper):
        raise ValueError
    result = 0
    for char in upper:
        result = result * 26 + (string.ascii_uppercase.index(char) + 1)
    return result - 1  # 转换为 0-based


class MoveResult(IntEnum):
    """落子操作的结果。"""

    CONTINUE = 0
    BLACK_WIN = 1
    WHITE_WIN = -1
    DRAW = -2
    # SKIP = 2
    ILLEGAL = 3


class Placement(IntEnum):
    """棋子放置方式：CROSS 表示落于交叉点（如围棋/五子棋），GRID 表示落于格子内（如黑白棋）。"""

    CROSS = 0
    GRID = 1


class MoveSide(IntEnum):
    """当前行棋方：BLACK 为黑方（先手），WHITE 为白方。"""

    BLACK = 1
    WHITE = -1

    @property
    def zh_hans(self) -> str:
        """返回行棋方的中文名称（黑或白）。"""
        return {
            MoveSide.BLACK: "黑",
            MoveSide.WHITE: "白",
        }[self]

    def flip(self) -> MoveSide:
        """返回对方的行棋方。"""
        return MoveSide.WHITE if self == MoveSide.BLACK else MoveSide.BLACK


class Piece(IntEnum):
    """棋盘上的棋子状态：BLACK 为黑子，WHITE 为白子，EMPTY 为空。"""

    BLACK = 1
    WHITE = -1
    EMPTY = 0

    @classmethod
    def from_move_side(cls, moveside: MoveSide) -> Piece:
        """从 MoveSide 构造对应的 PieceState。"""
        return cls.BLACK if moveside == MoveSide.BLACK else cls.WHITE

    def flip(self) -> Piece:
        """返回对方的棋子状态。"""
        if self == Piece.EMPTY:
            return Piece.EMPTY
        return Piece.WHITE if self == Piece.BLACK else Piece.BLACK


class Pos(NamedTuple):
    """棋盘坐标，x 为列（0-based），y 为行（0-based）。"""

    x: int
    y: int

    @classmethod
    def from_str(cls, s: str) -> Pos:
        """从字符串解析坐标，格式为列字母+行数字（如 `"H4"`, `"AA1"`）。支持多字母列（AA=26, AZ=51）。"""
        match_obj = re.fullmatch(r"([a-z]+)(\d+)", s, re.IGNORECASE)
        if match_obj:
            x = letter_to_num(match_obj.group(1))
            y = int(match_obj.group(2)) - 1
            return cls(x, y)
        raise ValueError("坐标格式不合法！")

    def __str__(self) -> str:
        """将坐标转换为字符串（如 `Pos(7, 3)` → `"H4"`，`Pos(26, 0)` → `"AA1"`）。"""
        if self.x < 0 or self.y < 0:
            return repr(self)
        return num_to_letter(self.x) + str(self.y + 1)


@dataclass
class History:
    b_board: int
    w_board: int
    next_move_side: MoveSide


class BoardGame:
    """棋类游戏的抽象基类，提供棋盘状态管理、落子、悔棋及绘图等通用功能。"""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        placement: Placement,
        star_positions: list[Pos] | None = None,
    ) -> None:
        """初始化棋局。

        Args:
            width: 棋盘宽度（列数）。
            height: 棋盘高度（行数）。
            placement: 落子方式，CROSS 为交叉点，GRID 为格子内。
            star_positions: 星位坐标列表，默认为空列表。
        """
        self.width: int = width
        self.height: int = height
        self.placement: Placement = placement
        self.star_positions: list[Pos] = (
            star_positions if star_positions is not None else []
        )

        self.player_id: dict[MoveSide, Any | None] = {
            MoveSide.BLACK: None,
            MoveSide.WHITE: None,
        }

        self.next_move_side: MoveSide = MoveSide.BLACK
        self._positions: list[Pos | None] = []
        self._history: list[History] = []
        self._b_board: int = 0
        self._w_board: int = 0
        self._save()

    def update(self, pos: Pos | None) -> tuple[MoveResult, str]:
        """在指定坐标落子并更新棋局状态，由子类实现。

        Args:
            pos: 落子位置，或 None 表示跳过回合（仅围棋支持）。

        Returns:
            落子结果对应的 MoveResult 值和非法落子的提示信息。
        """
        raise NotImplementedError

    @property
    def last_move_side(self) -> MoveSide | None:
        """上一手的行棋方，若尚未落子则为 `None`。"""
        if len(self._history) <= 1:
            return None
        return self._history[-2].next_move_side

    @property
    def player_next(self) -> Any | None:
        """下一手应落子的玩家 QQ 号，若该方尚未加入则为 None。"""
        return self.player_id.get(self.next_move_side)

    @property
    def player_last(self) -> Any | None:
        """上一手落子的玩家 QQ 号，若该方尚未加入则为 None。"""
        return self.player_id.get(self.last_move_side) if self.last_move_side else None

    @property
    def _area(self) -> int:
        """棋盘总格数（width x height）。"""
        return self.width * self.height

    @property
    def _full(self) -> int:
        """棋盘已满的位掩码（所有位置都有棋子）。"""
        return (1 << self._area) - 1

    def is_full(self) -> bool:
        """判断棋盘是否已落满棋子。"""
        return not ((self._b_board | self._w_board) ^ self._full)

    def _bit(self, pos: Pos) -> int:
        """返回坐标 pos 对应的位掩码（用于位板运算）。"""
        return 1 << (pos.x * self.height + pos.y)

    def in_range(self, pos: Pos) -> bool:
        """判断坐标是否在棋盘范围内。"""
        return 0 <= pos.x < self.width and 0 <= pos.y < self.height

    def get(self, pos: Pos) -> Piece:
        """获取指定坐标的棋子：BLACK 为黑子，WHITE 为白子，EMPTY 为空。"""
        bit: int = self._bit(pos)
        if self._b_board & bit:
            return Piece.BLACK
        if self._w_board & bit:
            return Piece.WHITE
        return Piece.EMPTY

    def _set(self, pos: Pos, piece: Piece) -> None:
        """
        在指定坐标放置棋子。

        本方法不检查落子是否合法，调用前请确保 `pos` 在棋盘范围内且该位置为空。

        Args:
            pos: 要放置棋子的位置。
            piece: 要放置的棋子
        """
        bit: int = self._bit(pos)
        if piece == Piece.BLACK:
            self._w_board &= ~bit
            self._b_board |= bit
        elif piece == Piece.WHITE:
            self._b_board &= ~bit
            self._w_board |= bit
        else:
            self._w_board &= ~bit
            self._b_board &= ~bit

    def _push(self, pos: Pos) -> None:
        """
        以当前行棋方落子于 `pos`（若坐标在棋盘内），切换行棋方并保存历史。

        本方法不检查落子是否合法，调用前请确保 `pos` 在棋盘范围内且该位置为空。

        Args:
            pos: 要落子的位置
        """
        self._set(pos, Piece.from_move_side(self.next_move_side))
        self.next_move_side = self.next_move_side.flip()
        self._positions.append(pos)
        self._save()

    def _save(self) -> None:
        """将当前棋盘状态快照追加到历史记录。"""
        history = History(self._b_board, self._w_board, self.next_move_side)
        self._history.append(history)

    def repent(self) -> None:
        """撤销最后一步，从历史记录中恢复前一状态（悔棋）。"""
        self._history.pop()
        self._positions.pop()
        history = self._history[-1]
        self._b_board = history.b_board
        self._w_board = history.w_board
        self.next_move_side = history.next_move_side

    def draw(
        self,
        grid_pixels: float = 48.0,
        grid_width: float = 0.05,
        border: float = 1.0,
        coordinate_font_size: float = 0.6,
        move_number_font_size: float = 0.48,
        dot_r: float = 0.45,
        dot_width: float = 0.05,
        mark_r: float = 0.1,
        star_r: float = 0.1,
        anti_alias: float = 2.0,
        show_move_numbers: bool = False,
    ) -> Image.Image:
        """将当前棋局绘制为图像并返回。

        Args:
            grid_pixels: 每格像素大小。
            grid_width: 网格线宽度（相对于 grid_pixels）。
            border: 四周留白格数。
            coordinate_font_size: 坐标标注字号（相对于 grid_pixels）。
            move_number_font_size: 步数编号字号（相对于 grid_pixels）。
            dot_r: 棋子半径（相对于 grid_pixels）。
            dot_width: 白子边框宽度（相对于 grid_pixels）。
            mark_r: 最后落子标记半边长（相对于 grid_pixels）。
            star_r: 星位半径（相对于 grid_pixels）。
            anti_alias: 抗锯齿倍率，绘制后缩放至原始尺寸。
            show_move_numbers: 游戏结束时是否显示每一手的步数编号。

        Returns:
            绘制完成的 RGBA 图像。
        """

        def pos_to_pixel(
            pos: tuple[float, float],
            *,
            grid_pixels: float,
            border: float,
            anti_alias: float,
            method: Literal["floor", "round"] | None,
        ) -> tuple[float, float]:
            """将棋盘坐标转换为像素坐标。"""
            x, y = pos
            f = {
                "floor": math.floor,
                "round": round,
                None: lambda x: x,
            }[method]
            return (
                f((border + x + 1 / 2) * grid_pixels * anti_alias),
                f((border + y + 1 / 2) * grid_pixels * anti_alias),
            )

        def xy_to_pixel(
            xy: tuple[tuple[float, float], tuple[float, float]],
            *,
            grid_pixels: float,
            border: float,
            anti_alias: float,
            method: Literal["floor", "round"] | None,
        ) -> XY:
            """将棋盘坐标范围转换为像素坐标范围。"""
            return (
                pos_to_pixel(
                    xy[0],
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=method,
                ),
                pos_to_pixel(
                    xy[1],
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=method,
                ),
            )

        width = round((self.width + 2 * border) * grid_pixels)
        height = round((self.height + 2 * border) * grid_pixels)
        width_anti_alias = round((self.width + 2 * border) * grid_pixels * anti_alias)
        height_anti_alias = round((self.height + 2 * border) * grid_pixels * anti_alias)

        # image0 用于绘制网格和坐标，image1 用于绘制棋子和最后落子标记，最后合成两者得到最终图像
        # image0 不需要抗锯齿，image1 需要抗锯齿以保证棋子和标记边缘平滑
        # image0: Image.Image = Image.new("RGBA", (width, height), "white")
        image1: Image.Image = Image.new(
            "RGB", (width_anti_alias, height_anti_alias), "white"
        )
        # draw0: ImageDraw.ImageDraw = ImageDraw.Draw(image0)
        draw1: ImageDraw.ImageDraw = ImageDraw.Draw(image1)

        # 画格子
        if self.placement == Placement.CROSS:
            for i in range(self.width):
                draw1.line(
                    xy_to_pixel(
                        ((i, 0), (i, self.height - 1)),
                        grid_pixels=grid_pixels,
                        border=border,
                        anti_alias=anti_alias,
                        method="floor",
                    ),
                    "black",
                    round(grid_width * grid_pixels * anti_alias),
                )
            for i in range(self.height):
                draw1.line(
                    xy_to_pixel(
                        ((0, i), (self.width - 1, i)),
                        grid_pixels=grid_pixels,
                        border=border,
                        anti_alias=anti_alias,
                        method="floor",
                    ),
                    "black",
                    round(grid_width * grid_pixels * anti_alias),
                )
        elif self.placement == Placement.GRID:
            for i in range(self.width + 1):
                draw1.line(
                    xy_to_pixel(
                        ((i - 1 / 2, -1 / 2), (i - 1 / 2, self.height - 1 / 2)),
                        grid_pixels=grid_pixels,
                        border=border,
                        anti_alias=anti_alias,
                        method="floor",
                    ),
                    "black",
                    round(grid_width * grid_pixels * anti_alias),
                )
            for i in range(self.height + 1):
                draw1.line(
                    xy_to_pixel(
                        ((-1 / 2, i - 1 / 2), (self.width - 1 / 2, i - 1 / 2)),
                        grid_pixels=grid_pixels,
                        border=border,
                        anti_alias=anti_alias,
                        method="floor",
                    ),
                    "black",
                    round(grid_width * grid_pixels * anti_alias),
                )
        # 写坐标文字
        coordinate_font: ImageFont.FreeTypeFont = ImageFont.truetype(
            plugin_config.font_path.as_posix(),
            round(coordinate_font_size * grid_pixels * anti_alias),
        )
        move_number_font: ImageFont.FreeTypeFont = ImageFont.truetype(
            plugin_config.font_path.as_posix(),
            round(move_number_font_size * grid_pixels * anti_alias),
        )
        # 上面列字母
        for i in range(self.width):
            draw1.text(
                pos_to_pixel(
                    (i, -1 / 2 - 0.1),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=None,
                ),
                num_to_letter(i),
                "black",
                coordinate_font,
                anchor="ms",
            )
        # 下面列字母
        for i in range(self.width):
            draw1.text(
                pos_to_pixel(
                    (i, self.height - 1 / 2 + 0.1),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=None,
                ),
                num_to_letter(i),
                "black",
                coordinate_font,
                anchor="ma",
            )
        # 左边行号
        for i in range(self.height):
            draw1.text(
                pos_to_pixel(
                    (-1 / 2 - 0.1, i),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=None,
                ),
                str(i + 1),
                "black",
                coordinate_font,
                anchor="rm",
            )
        # 右边行号
        for i in range(self.height):
            draw1.text(
                pos_to_pixel(
                    (self.width - 1 / 2 + 0.1, i),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method=None,
                ),
                str(i + 1),
                "black",
                coordinate_font,
                anchor="lm",
            )

        # 画星位
        for star_pos in self.star_positions:
            draw1.ellipse(
                xy_to_pixel(
                    (
                        (star_pos.x - star_r, star_pos.y - star_r),
                        (star_pos.x + star_r, star_pos.y + star_r),
                    ),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method="floor",
                ),
                "black",
            )

        # 画棋子
        for x in range(self.width):
            for y in range(self.height):
                xy: XY = xy_to_pixel(
                    ((x - dot_r, y - dot_r), (x + dot_r, y + dot_r)),
                    grid_pixels=grid_pixels,
                    border=border,
                    anti_alias=anti_alias,
                    method="floor",
                )
                if self.get(Pos(x, y)) == Piece.BLACK:
                    draw1.ellipse(xy, "black")
                elif self.get(Pos(x, y)) == Piece.WHITE:
                    draw1.ellipse(
                        xy,
                        "white",
                        outline="black",
                        width=round(dot_width * grid_pixels * anti_alias),
                    )

        # 显示手数编号
        if show_move_numbers:
            # 构建每个位置最后一次落子的手数映射
            move_number_map: dict[Pos, int] = {}
            move_number: int = 0
            for pos in self._positions:
                if pos is None:  # PASS 操作
                    continue
                move_number += 1
                move_number_map[pos] = move_number  # 覆盖之前的值，只保留最后一次

            # 显示每个位置的最后一次手数
            for pos, move_number in move_number_map.items():
                if self.get(pos) != Piece.EMPTY:
                    draw1.text(
                        pos_to_pixel(
                            (pos.x, pos.y),
                            grid_pixels=grid_pixels,
                            border=border,
                            anti_alias=anti_alias,
                            method=None,
                        ),
                        str(move_number),
                        "white" if self.get(pos) == Piece.BLACK else "black",
                        move_number_font,
                        anchor="mm",
                    )

        else:
            # 画最后落子标记
            if len(self._history) >= 2:
                pos: Pos | None = self._positions[-1]
                if pos is not None:
                    color: str = "white" if self.get(pos) == Piece.BLACK else "black"
                    draw1.rectangle(
                        xy_to_pixel(
                            (
                                (pos.x - mark_r, pos.y - mark_r),
                                (pos.x + mark_r, pos.y + mark_r),
                            ),
                            grid_pixels=grid_pixels,
                            border=border,
                            anti_alias=anti_alias,
                            method="floor",
                        ),
                        color,
                    )

        image1: Image.Image = image1.resize((width, height), Image.Resampling.BILINEAR)
        # return Image.alpha_composite(image0, image1)
        return image1
