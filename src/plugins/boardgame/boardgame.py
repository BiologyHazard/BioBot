import re
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from PIL.ImageDraw import ImageDraw as PILImageDraw
from PIL.ImageFont import FreeTypeFont
from enum import Enum

pos_T = tuple[int, int]
xy_T = tuple[pos_T, pos_T]


class MoveResult(Enum):
    BLACK_WIN = 1
    WHITE_WIN = -1
    DRAW = -2
    SKIP = 2
    ILLEGAL = 3


class Placement(Enum):
    CROSS = 0
    GRID = 1


class MoveSide:
    BLACK = 1
    WHITE = -1
    zh_hans = {BLACK: '黑', WHITE: '白'}


@dataclass
class Pos:
    x: int
    y: int

    @classmethod
    def from_str(cls, s: str) -> "Pos":
        if s == "null":
            return cls.null()
        match_obj = re.fullmatch(r"([a-z])(\d+)", s, re.IGNORECASE)
        if match_obj:
            x = (ord(match_obj.group(1).lower()) - ord("a")) % 32
            y = int(match_obj.group(2)) - 1
            return cls(x, y)
        raise ValueError("坐标格式不合法！")

    @classmethod
    def null(cls) -> "Pos":
        return cls(-1, -1)

    @classmethod
    def num_to_letter(cls, num: int) -> str:
        if not 0 <= num < 26:
            raise ValueError
        return chr(num + ord('A'))

    @classmethod
    def letter_to_num(cls, letter: str) -> int:
        letter = letter.upper()
        if not 'A' <= letter <= 'Z':
            raise ValueError
        return ord(letter) - ord('A')

    def __str__(self) -> str:
        if self.x < 0 or self.y < 0:
            return "null"
        return chr(self.x + ord("a")) + str(self.y + 1)


@dataclass
class History:
    b_board: int
    w_board: int
    moveside: int


class BoardGame:
    name: str = ""

    def __init__(
        self,
        size: int = 0,
        placement: Placement = Placement.CROSS,
        allow_skip: bool = False,
        allow_repent: bool = True,
    ) -> None:
        self.size: int = size
        self.placement: Placement = placement
        self.allow_skip: bool = allow_skip
        self.allow_repent: bool = allow_repent

        self.is_game_over: bool = False
        self.player_white: int | None = None
        self.player_black: int | None = None

        self.moveside: int = 1
        """1 代表黑方，-1 代表白方"""
        self.positions: list[Pos] = []
        self.history: list[History] = []
        self.b_board: int = 0
        self.w_board: int = 0
        self.area: int = self.size * self.size
        self.full: int = (1 << self.area) - 1
        self.save()

    def update(self, pos: Pos) -> MoveResult | None:
        raise NotImplementedError

    @property
    def player_next(self) -> int | None:
        return self.player_black if self.moveside == 1 else self.player_white

    @property
    def player_last(self) -> int | None:
        return self.player_white if self.moveside == 1 else self.player_black

    def is_full(self) -> bool:
        return not ((self.b_board | self.w_board) ^ self.full)

    def bit(self, pos: Pos) -> int:
        return 1 << (pos.x * self.size + pos.y)

    def in_range(self, pos: Pos) -> bool:
        return pos.x >= 0 and pos.y >= 0 and pos.x < self.size and pos.y < self.size

    def get(self, pos: Pos) -> int:
        bit: int = self.bit(pos)
        if self.b_board & bit:
            return 1
        if self.w_board & bit:
            return -1
        return 0

    def set(self, pos: Pos, value: int) -> None:
        bit: int = self.bit(pos)
        if value == 1:
            self.w_board &= ~bit
            self.b_board |= bit
        elif value == -1:
            self.b_board &= ~bit
            self.w_board |= bit
        else:
            self.w_board &= ~bit
            self.b_board &= ~bit

    def push(self, pos: Pos) -> None:
        if self.in_range(pos):
            self.set(pos, self.moveside)
        self.moveside = -self.moveside
        self.positions.append(pos)
        self.save()

    def save(self) -> None:
        history: History = History(self.b_board, self.w_board, self.moveside)
        self.history.append(history)

    def pop(self) -> None:
        self.history.pop()
        self.positions.pop()
        history = self.history[-1]
        self.b_board = history.b_board
        self.w_board = history.w_board
        self.moveside = history.moveside

    def draw(self,
             grid_pixels=48.0,
             grid_width=0.04,
             border=1.0,
             font_size=0.6,
             dot_r=0.45,
             dot_width=0.04,
             anti_alias=2.0) -> Image.Image:

        width = height = round((self.size + 2 * border) * grid_pixels)
        width_anti_alias = height_anti_alias = round(
            (self.size + 2 * border) * grid_pixels * anti_alias)
        image0: PILImage = Image.new('RGBA', (width, height), 'white')
        image1 = Image.new(
            'RGBA', (width_anti_alias, height_anti_alias), (0, 0, 0, 0))
        draw0: PILImageDraw = ImageDraw.Draw(image0)
        draw1: PILImageDraw = ImageDraw.Draw(image1)
        if self.placement == Placement.CROSS:
            for i in range(self.size):
                draw0.line(((round((border + i + 1/2) * grid_pixels),
                             round((border + 1/2) * grid_pixels)),
                            (round((border + i + 1/2) * grid_pixels),
                             round((border + self.size - 1 + 1/2) * grid_pixels))),
                           'black', round(grid_width * grid_pixels))
            for i in range(self.size):
                draw0.line(((round((border + 1/2) * grid_pixels),
                             round((border + i + 1/2) * grid_pixels)),
                            (round((border + self.size - 1 + 1/2) * grid_pixels),
                             round((border + i + 1/2) * grid_pixels))),
                           'black', round(grid_width * grid_pixels))
        elif self.placement == Placement.GRID:
            for i in range(self.size + 1):
                draw0.line(((round((border + i) * grid_pixels),
                             round((border) * grid_pixels)),
                            (round((border + i) * grid_pixels),
                             round((border + self.size) * grid_pixels))),
                           'black', round(grid_width * grid_pixels))
            for i in range(self.size + 1):
                draw0.line(((round((border) * grid_pixels),
                             round((border + i) * grid_pixels)),
                            (round((border + self.size) * grid_pixels),
                             round((border + i) * grid_pixels))),
                           'black', round(grid_width * grid_pixels))

        for x in range(self.size):
            for y in range(self.size):
                xy: xy_T = ((round((border + x + 1/2 - dot_r) * grid_pixels * anti_alias),
                             round((border + y + 1/2 - dot_r) * grid_pixels * anti_alias)),
                            (round((border + x + 1/2 + dot_r) * grid_pixels * anti_alias),
                             round((border + y + 1/2 + dot_r) * grid_pixels * anti_alias)))
                if self.get(Pos(x, y)) == 1:
                    draw1.ellipse(xy, 'black')
                elif self.get(Pos(x, y)) == -1:
                    draw1.ellipse(xy, 'white', 'black',
                                  round(dot_width * anti_alias * grid_pixels))

        font0: FreeTypeFont = ImageFont.truetype(
            r'data/boardgame/consola.ttf', round(font_size * grid_pixels))
        for i in range(self.size):
            font_pixels: tuple[int, int] = font0.getsize(Pos.num_to_letter(i))
            draw0.text((round((border + i + 1/2) * grid_pixels - font_pixels[0] / 2),
                        round((border - 0.1) * grid_pixels - font_pixels[1])),
                       Pos.num_to_letter(i), 'black', font0, align='center')
        for i in range(self.size):
            font_pixels = font0.getsize(str(i + 1))
            draw0.text((round((border - 0.1) * grid_pixels - font_pixels[0]),
                        round((border + i + 1/2) * grid_pixels - font_pixels[1] / 2)),
                       str(i + 1), 'black', font0, align='center')

        image1: PILImage = image1.resize((width, height), Image.Resampling.BILINEAR)
        return Image.alpha_composite(image0, image1)


if __name__ == '__main__':
    game: BoardGame = BoardGame(8, Placement.GRID)
    game.set(Pos(0, 0), 1)
    game.set(Pos(0, 1), -1)
    game.draw(grid_pixels=64).show()
