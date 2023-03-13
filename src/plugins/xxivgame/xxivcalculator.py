import random
from fractions import Fraction
from itertools import combinations
from typing import Sequence

from .expression import Expression, number_T


class XXIVSolver:
    def __init__(self, target: number_T = 24, nums: (Sequence[number_T] | None) = None) -> None:
        self.target: Fraction = Fraction(target)
        self.nums = nums

    @property
    def nums(self) -> list[Fraction] | None:
        return self.__nums

    @nums.setter
    def nums(self, nums: (Sequence[number_T] | None)) -> None:
        self.__nums: list[Fraction] | None
        if nums is None:
            self.__nums = None
            return

        self.__nums = [Fraction(num) for num in nums]

    # @property
    # def target(self) -> Fraction:
    #     return self.__target

    # @target.setter
    # def target(self, target: number_T | None) -> None:
    #     if target is None:
    #         self.__target = 24
    #     elif isinstance(target, Fraction):
    #         self.__target = target
    #     else:
    #         self.__target

    def solve(self) -> Expression | None:
        if self.nums is None:
            raise ValueError("'num' attr has not been initialized.")

        expressions: list[Expression] = [Expression(num) for num in self.nums]
        if (result := self._dfs(expressions, divide=False)) is not None:
            return result
        return self._dfs(expressions, divide=True)

    def _dfs(self, nums: list[Expression], divide: bool = True) -> Expression | None:
        n: int = len(nums)
        if n == 1:
            return nums[0] if nums[0].value == self.target else None

        for i, j in combinations(range(n), 2):
            x: Expression = nums[i]
            y: Expression = nums[j]
            new_nums: list[Expression] = [num for k, num in enumerate(nums) if k != i and k != j]
            if (result := self._dfs(new_nums + [x+y], divide)) is not None:
                return result
            if x.value >= y.value and (result := self._dfs(new_nums + [x-y], divide)) is not None:
                return result
            if x.value < y.value and (result := self._dfs(new_nums + [y-x], divide)) is not None:
                return result
            if (result := self._dfs(new_nums + [x*y], divide)) is not None:
                return result
            if divide:
                if y.value != 0 and (result := self._dfs(new_nums + [x/y], divide)) is not None:
                    return result
                if x.value != 0 and (result := self._dfs(new_nums + [y/x], divide)) is not None:
                    return result

        return None

    @classmethod
    def generate(cls,
                 n: int = 4,
                 target: int = 4,
                 max_num: int = 13,
                 min_num: int = 1,
                 solvable_probability: float | None = None,
                 max_trials: int | None = 16
                 ) -> tuple[list[int] | None, Expression | None]:
        if solvable_probability is None:
            nums: list[int] = [random.randint(min_num, max_num) for _ in range(n)]
            solution: Expression | None = cls(target, nums).solve()
            return nums, solution
        solvable: bool = random.random() < solvable_probability
        trial: int = 0
        while True:
            trial += 1
            nums: list[int] = [random.randint(min_num, max_num) for _ in range(n)]
            solution = cls(target, nums).solve()
            if (solvable and solution is not None) or (not solvable and solution is None):
                return nums, solution
            if (max_trials is not None) and (trial >= max_trials):
                return None, None


if __name__ == '__main__':
    print(*XXIVSolver.generate(4, 100, 6), sep='\n')
    # print(str(XXIVSolver(24, [1, 1, 4, 5, 1, 4]).solve()))
    # print(repr(Expression(Expression(Fraction(10)))))
