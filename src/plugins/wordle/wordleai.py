import json
import math

import numpy as np

from .utils import words_dir


def entropy_to_expected_score(ent: float) -> float:
    return 2 - 2**(-ent) + 1.5 / 11.5 * ent


def calc_hint(ans: str, guess: str) -> list[int]:
    assert len(ans) == len(guess)
    length: int = len(ans)
    hint: list[int] = [-1 for i in range(length)]
    ans_matched: list[bool] = [False for i in range(length)]
    for i in range(length):
        if guess[i] == ans[i]:
            hint[i] = 2
            ans_matched[i] = True
        elif guess[i] not in ans:
            hint[i] = 0
    for i in range(length):
        if hint[i] == -1:
            for j in range(length):
                if not ans_matched[j] and guess[i] == ans[j]:
                    hint[i] = 1
                    ans_matched[j] = True
                    break
            if hint[i] == -1:
                hint[i] = 0
    return hint


def hint_to_num(hint: list[int]) -> int:
    return sum(x * 3**i for i, x in enumerate(hint))


class WordleAI:
    def __init__(self, dic_name: str, length: int) -> None:
        self.psb_answers: set[str] = set(filter(lambda s: len(s) == length,
                                                json.loads((words_dir / f'{dic_name}.json').read_text()).keys()))
        self.supported_guesses: set[str] = self.psb_answers.copy()
        self.length: int = length

    def give_guess(self) -> str:
        if len(self.psb_answers) <= 3:
            guesses: set[str] = self.psb_answers
        else:
            guesses = self.supported_guesses
        guesses_exp: dict[str, float] = {}
        left_entropy: float = math.log2(len(self.psb_answers))
        for guess in guesses:
            prob: float = 1 / len(self.psb_answers) if guess in self.psb_answers else 0.0
            hint_count = np.zeros(3**self.length, dtype=np.int8)
            for ans in self.psb_answers:
                hint_count[hint_to_num(calc_hint(ans, guess))] += 1
            ent = 0
            for count in hint_count:
                if count > 0:
                    ent += (count / len(self.psb_answers) *
                            (-math.log2(count / len(self.psb_answers))))
            guesses_exp[guess] = prob + (1 - prob) * (1 + entropy_to_expected_score(left_entropy - ent))
        return min(guesses_exp, key=lambda x: guesses_exp[x])

    def store_result(self, guess: str, hint: list[int]) -> set[str]:
        if all(x == 2 for x in hint):
            self.psb_answers &= {guess}
        else:
            self.psb_answers = {psb_ans for psb_ans in self.psb_answers
                                if calc_hint(psb_ans, guess) == hint}
        return self.psb_answers
