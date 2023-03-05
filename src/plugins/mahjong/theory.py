from collections import Counter


class Theory(Counter):
    def can_ting(self): ...

    def can_hu(self) -> bool:
        if sum(self.values()) % 3 != 2:
            raise ValueError
        for

    def analyze(self): ...
    @staticmethod
    def load_from_str(s: str) -> 'Theory': ...
