from collections import Counter
from typing import Iterable, Final, Generator


def _merge_iterator(*iterators) -> Generator:
    for iterator in iterators:
        for item in iterator:
            yield item


class Theory:
    BEGINS: Final[dict[str, int]] = {'m': 0, 's': 10, 'p': 20, 'z': 30}
    ALLOW_KEYS: Final[list[int]] = [i for i in range(38)]

    WAN: range = range(1, 10)
    SUO: range = range(11, 20)
    TONG: range = range(21, 30)
    ZI: range = range(31, 38)
    DORA: list[int] = [0, 10, 20]

    NUMBER_CARDS: Generator = _merge_iterator(WAN, SUO, TONG)
    CARDS: Generator = _merge_iterator(WAN, SUO, TONG)
    CARDS_WITH_DORA: range = range(38)

    def __init__(self, cards: str | Counter | Iterable) -> None:
        self.cards_with_dora: Counter[int] = Counter()
        if isinstance(cards, str):
            mark: str = 'm'
            for char in reversed(cards):
                if char.lower() in Theory.BEGINS:
                    mark = char.lower()
                elif char.isdigit():
                    self.cards_with_dora[Theory.BEGINS[mark] + int(char)] += 1
                else:
                    raise ValueError

        elif isinstance(cards, Counter):
            self.cards_with_dora = cards
        else:
            self.cards_with_dora = Counter(cards)

        if any(x not in Theory.ALLOW_KEYS for x in self.cards_with_dora.keys()):
            raise ValueError

        self.cards: Counter[int] = Counter()
        for card in 0, 10, 20:
            self.cards[card + 5] += self.cards_with_dora[card]
            del self.cards[card]

    def can_ting(self): ...

    def can_hu(self) -> bool:
        if self.cards_with_dora.total() % 3 != 2:
            raise ValueError
        flag: bool = False
        for card in Theory.CARDS:
            if self.cards[card] >= 2:
                if self.wu_quetou_hu():
                    flag = True
        return flag

    def wu_quetou_hu(self) -> bool

    def analyze(self): ...
    # @staticmethod
    # def load_from_str(s: str) -> 'Theory': ...


if __name__ == '__main__':
    print(Theory('123m456s789p1234567z'))
