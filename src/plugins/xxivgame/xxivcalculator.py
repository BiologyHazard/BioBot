from fractions import Fraction
from functools import cache
from itertools import combinations
from typing import Sequence, Generator


class XXIV_Solver:
    __len: int = 4
    __log: bool = False
    __target: Fraction = Fraction(24)

    def __init__(self,
                 target: int | Fraction | str | None = None,
                 log_flag: bool = False) -> None:

        if target is not None:
            self.target = target
        if log_flag:
            self.__log = True

    @property
    def target(self) -> Fraction:
        return self.__target

    @target.setter
    def target(self, val: int | Fraction | str) -> None:
        if isinstance(val, (int, Fraction, str)):
            self.__target = Fraction(val)
        else:
            msg = f"Requires an int | Fraction | str, given {type(val)}"
            raise ValueError(msg)

    def solve_with_record(
        self,
        nums: Sequence[int | Fraction | str],
    ) -> tuple[bool, str | None]:

        def fr_str(x: Fraction) -> str:
            tmp = int(x)
            if x == tmp:
                return str(tmp)
            return f'{float(x):.3f}'
        nums_fr: tuple[Fraction, ...] = tuple(map(lambda x: Fraction(x), nums))
        nums_fr_str = tuple((x, fr_str(x))for x in nums_fr)
        self.__len = len(nums)
        result = self.__dfs_with_record(nums_fr_str, self.__target)
        if result:
            return True, f"{result} = {self.__target}"
        return False, None

    def __dfs_with_record(
        self,
        nums_and_strnums: tuple[tuple[Fraction, str], ...],
        target: Fraction,
    ) -> str | None:

        def combine(x: tuple[Fraction, str], y: tuple[Fraction, str]) -> Generator[tuple[Fraction, str], None, None]:
            numx, strx = x
            numy, stry = y
            yield numx+numy, f'({strx} + {stry})'
            yield numx-numy, f'({strx} - {stry})'
            yield numy-numx, f'({stry} - {strx})'
            yield numx*numy, f'({strx} * {stry})'
            if numy != 0:
                yield numx/numy, f'({strx} / {stry})'
            if numx != 0:
                yield numy/numx, f'({stry} / {strx})'

        n: int = len(nums_and_strnums)

        if self.__log:
            if n <= self.__len - 1:
                print("           " * (self.__len - 1 - n) + "        └->", end="")
            for i, _ in nums_and_strnums:
                print("{:10.3f}".format(float(i)), end=" ")
            print()

        if n == 1:
            if nums_and_strnums[0][0] != target:
                return None
            return nums_and_strnums[0][1]

        for i, j in combinations(range(n), 2):
            tmp: list[tuple[Fraction, str]] = [item for k,
                                               item in enumerate(nums_and_strnums) if k != i and k != j]

            x: tuple[Fraction, str] = nums_and_strnums[i]
            y: tuple[Fraction, str] = nums_and_strnums[j]
            for combxy in combine(x, y):
                msg: str | None = self.__dfs_with_record(tuple([combxy]+tmp), target)
                if msg:
                    return msg


def solve_problem(nums: Sequence[int | Fraction | str],
                  target: int | Fraction | str,
                  default_solver: XXIV_Solver = XXIV_Solver()) -> tuple[bool, str | None]:
    default_solver.target = target
    return default_solver.solve_with_record(nums)
