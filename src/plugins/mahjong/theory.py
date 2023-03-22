from collections import Counter
from typing import Iterable, Final, Generator


class Tiles(Counter[int]):
    BEGINS: Final[dict[str, int]] = {'m': 0, 's': 10, 'p': 20, 'z': 30}
    ALLOW_KEYS: Final[list[int]] = [i for i in range(38)]

    WAN_TILES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    SUO_TILES: tuple[int, ...] = (11, 12, 13, 14, 15, 16, 17, 18, 19)
    TONG_TILES: tuple[int, ...] = (21, 22, 23, 24, 25, 26, 27, 28, 29)
    KANJI_TILES: tuple[int, ...] = (31, 32, 33, 34, 35, 36, 37)
    DORA_TILES: tuple[int, ...] = (0, 10, 20)
    WAN_TILES_WITH_DORA: tuple[int, ...] = (1, 2, 3, 4, 0, 5, 6, 7, 8, 9)
    SUO_TILES_WITH_DORA: tuple[int, ...] = (11, 12, 13, 14, 10, 15, 16, 17, 18, 19)
    TONG_TILES_WITH_DORA: tuple[int, ...] = (21, 22, 23, 24, 20, 25, 26, 27, 28, 29)

    NUMBER_TILES: tuple[int, ...] = WAN_TILES + SUO_TILES + TONG_TILES
    TILES: tuple[int, ...] = WAN_TILES + SUO_TILES + TONG_TILES + KANJI_TILES
    TILES_WITH_DORA: tuple[int, ...] = WAN_TILES_WITH_DORA + SUO_TILES_WITH_DORA + TONG_TILES_WITH_DORA + KANJI_TILES

    def __init__(self, iterable: Iterable | None = None, /, **kwargs) -> None:
        if isinstance(iterable, str):
            mark: str = 'm'
            for char in reversed(iterable):
                if char.lower() in Tiles.BEGINS:
                    mark = char.lower()
                elif char.isdigit():
                    self[Tiles.BEGINS[mark] + int(char)] += 1
                else:
                    raise ValueError
        else:
            super().__init__(iterable, **kwargs)

        if any(x not in Tiles.ALLOW_KEYS for x in self.keys()):
            raise ValueError

    def __str__(self) -> str:
        l: list[str] = []
        for tiles, char in ((Tiles.WAN_TILES_WITH_DORA, 'm'), (Tiles.SUO_TILES_WITH_DORA, 's'), (Tiles.TONG_TILES_WITH_DORA, 'p'), (Tiles.KANJI_TILES, 'z')):
            flag: bool = False
            for tile in tiles:
                if self[tile] > 0:
                    flag = True
                    l.append(str(tile-Tiles.BEGINS[char]) * self[tile])
            if flag:
                l.append(char)
        return ''.join(l)

    def __add__(self, other: 'Tiles'):
        if not isinstance(other, Counter):
            return NotImplemented
        result: Tiles = Tiles()
        for elem, count in self.items():
            newcount: int = count + other[elem]
            if newcount > 0:
                result[elem] = newcount
        for elem, count in other.items():
            if elem not in self and count > 0:
                result[elem] = count
        return result

    def __sub__(self, other: 'Tiles'):
        # return self.__class__(super().__sub__(other))
        if not isinstance(other, Counter):
            return NotImplemented
        result: Tiles = Tiles()
        for elem, count in self.items():
            newcount: int = count - other[elem]
            if newcount > 0:
                result[elem] = newcount
        for elem, count in other.items():
            if elem not in self and count < 0:
                result[elem] = 0 - count
        return result


class Theory:
    def __init__(self, tiles: Tiles | str | Counter[int] | Iterable) -> None:
        self.tiles_with_dora: Tiles = Tiles(tiles)
        self.tiles: Tiles = Tiles()
        for tile in Tiles.TILES:
            self.tiles[tile] = self.tiles_with_dora[tile]
        for tile in Tiles.DORA_TILES:
            self.tiles[tile+5] += self.tiles_with_dora[tile]

    def can_ting(self) -> list[int]: ...

    def can_hu(self) -> bool:
        if self.tiles_with_dora.total() % 3 != 2:
            raise ValueError
        flag: bool = False
        for tile in Tiles.TILES:
            if self.tiles[tile] >= 2:
                if self.wu_quetou_hu():
                    flag = True
        return flag

    def wu_quetou_hu(self) -> bool: ...

    def analyze(self): ...

    @staticmethod
    def _shanten(tiles: Tiles) -> int:
        def 取雀头(tiles: Tiles, crem: int) -> None:
            # print(f'取雀头，{str(tiles):20}, crem={crem}, shanten={shanten}, mutc={max_use_tile_count}')
            for tile in Tiles.TILES:
                if tiles[tile] >= 2:
                    # print(f'取出雀头{Tiles({tile: 2})}')
                    取面子(tiles - Tiles({tile: 2}), 0, crem-2, 1, 0)

            # print(f'不取雀头')
            取面子(tiles, 0, crem, 0, 0)

        def 取面子(tiles: Tiles, i: int, crem: int, quetou: int, mianzi: int) -> None:
            # print(f'取面子，{str(tiles):20}, i={i}, crem={crem}, quetou={quetou}, mianzi={mianzi}, shanten={shanten}, mutc={max_use_tile_count}')
            while i <= 37:
                if i in Tiles.TILES:
                    if tiles[i] >= 1:
                        break
                i += 1

            if i > 37:
                取搭子(tiles, 0, crem, quetou, mianzi, 0)
                return

            if tiles[i] >= 3:
                # print(f'取出面子{Tiles({i: 3})}')
                取面子(tiles - Tiles({i: 3}), i, crem-3, quetou, mianzi+1)
            if i <= 27 and tiles[i] >= 1 and tiles[i+1] >= 1 and tiles[i+2] >= 1:
                # print(f'取出面子{Tiles({i: 1, i+1: 1, i+2: 1})}')
                取面子(tiles - Tiles({i: 1, i+1: 1, i+2: 1}), i, crem-3, quetou, mianzi+1)

            取面子(tiles, i+1, crem, quetou, mianzi)

        def 取搭子(tiles: Tiles, i: int, crem: int, quetou: int, mianzi: int, dazi: int) -> None:
            nonlocal shanten, max_use_tile_count
            # print(f'取搭子，{str(tiles):20}, i={i}, crem={crem}, quetou={quetou}, mianzi={mianzi}, dazi={dazi}, shanten={shanten}, mutc={max_use_tile_count}')
            if shanten == -1:
                return
            if mianzi + dazi > groups:
                return
            use_tile_count: int = 3 * mianzi + 2 * dazi + 2 * quetou
            if crem < max_use_tile_count - use_tile_count:
                return
            if crem <= 0:
                shanten = min(shanten, 2 * (groups - mianzi) - dazi - quetou)
                max_use_tile_count = max(max_use_tile_count, use_tile_count)
                return

            while i <= 37:
                if i in Tiles.TILES:
                    if tiles[i] >= 1:
                        break
                i += 1

            if tiles[i] >= 2:
                取搭子(tiles - Tiles({i: 2}), i, crem-2, quetou, mianzi, dazi+1)
            if i <= 28 and tiles[i] >= 1 and tiles[i+1] >= 1:
                取搭子(tiles - Tiles({i: 1, i+1: 1}), i, crem-2, quetou, mianzi, dazi+1)
            if (1 <= i <= 7 or 11 <= i <= 17 or 21 <= i <= 27) and tiles[i] >= 1 and tiles[i+2] >= 1:
                取搭子(tiles - Tiles({i: 1, i+2: 1}), i, crem-2, quetou, mianzi, dazi+1)

            取搭子(tiles - Tiles({i: tiles[i]}), i+1, crem - tiles[i], quetou, mianzi, dazi)
            # 取搭子(tiles, i+1, crem - tiles[i], quetou, mianzi, dazi)

        shanten: int = 8
        max_use_tile_count: int = 0
        groups: int = (tiles.total() - 2) // 3
        取雀头(tiles, tiles.total())
        return shanten

    def shanten(self) -> int:
        return Theory._shanten(self.tiles)

    def 何切(self) -> list[tuple[int, list[int]]]:
        shanten: int = self.shanten()
        possible_jinzhang: set[int] = set()
        jinzhang_set: set[int] = set()
        print(repr(self.tiles))
        for tile in self.tiles:
            if self.tiles[tile] >= 1:
                possible_jinzhang |= {tile-2, tile-1, tile, tile+1, tile+2}
        possible_jinzhang &= set(Tiles.TILES)
        for tile in possible_jinzhang:
            if (tmp := Theory._shanten(self.tiles - Tiles({tile: -1}))) < shanten:
                assert tmp == shanten - 1
                jinzhang_set.add(tile)

        from collections import defaultdict
        ans: defaultdict[int, list[int]] = defaultdict(list)
        for jinzhang in jinzhang_set:
            for qiepai in self.tiles:
                if self.tiles[qiepai] >= 1:
                    if (tmp := Theory._shanten(self.tiles - Tiles({qiepai: 1}) + Tiles({jinzhang: 1}))) < shanten:
                        assert tmp == shanten - 1
                        ans[qiepai].append(jinzhang)

        return [(key, sorted(ans[key])) for key in sorted(ans)]


if __name__ == '__main__':
    # l: list[tuple[str, int]] = [
    #     ('2466m78p578899s5z6p', 1),
    #     ('2466m678p58899s5z4z', 2),
    #     ('266m678p58899s45z7m', 3),
    #     ('2667m678p58899s5z8s', 2),
    #     ('479m27p223689s57z5m', 4),
    #     ('4579m7p223689s57z3s', 3),
    #     ('4579m7p2233689s7z9m', 3),
    #     ('45799m2233689s7z0s', 3),
    #     ('45799m2233089s7z5z', 3),
    #     ('45799m223389s57z6p', 3),
    #     ('4599m6p223389s57z6p', 3),
    #     ('459m66p223389s57z6z', 3),
    #     ('45m66p223389s567z1m', 3),
    #     ('145m66p223389s67z5m', 3),
    #     ('455m66p223389s67z5z', 3),
    #     ('455m66p22389s567z6s', 4),

    #     ('1233444666m11333s', -1),
    #     ('6m7p12579s7p', 1),
    #     ('6m7p12579s7p3s', 0),
    #     ('6m7p12579s7p6s', 0),
    #     ('6m7p12579s7p8s', 0),
    #     ('1233m245689s124z7m', 3),
    #     ('1233m245689s124z7m1m', 2),
    #     ('1233m245689s124z7m2z', 2),
    #     ('1233m245689s124z7m1s', 2),
    #     ('1233m245689s124z7m4z', 2),
    # ]
    # for question, answer in l:
    #     c: Tiles = Tiles(question)
    #     xts: int = Theory(c).shanten()
    #     print(xts)
    #     assert xts == answer

    # import random
    # ans: Counter[int] = Counter()
    # N: int = 10000
    # for i in range(N):
    #     tiles: Tiles = Tiles()
    #     for j in range(14):
    #         r: int = random.choice(Tiles.TILES)
    #         tiles[r] += 1
    #     xts: int = Theory(tiles).向听数()
    #     ans[xts] += 1
    #     # print(f'{str(tiles):16} {Theory(tiles).向听数()}')
    # print(sorted(ans.items()))
    c: Theory = Theory('1233m245689s124z7m')
    print(c.何切())
