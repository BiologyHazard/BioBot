import asyncio
import random
from pathlib import Path

from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment, Message
from PIL import Image

from .config import data_path
from .image import get_cover_len4_id, image_to_bytesio
from .music import Mai, Music


class Guess:
    def __init__(self, music: Music | None = None, rounds: int = 7) -> None:
        if music is None:
            self.music: Music = Mai.music_list.random()
            '''答案'''
        else:
            self.music = music
        self.rounds: int = rounds
        '''总轮数'''
        self.hints: list[str] = [
            f'这首乐曲的 Expert 难度是 {self.music.level[2]}',
            f'这首乐曲的 Master 难度是 {self.music.level[3]}',
            f'这首乐曲的分类是 {self.music.genre}',
            f'这首乐曲的版本是 {self.music.version}',
            f'这首乐曲的艺术家是 {self.music.artist}',
            f'这首乐曲{"不" if self.music.type == "SD" else ""}是 DX 谱面',
            f'这首乐曲{"没" if not self.music.has_remaster else ""}有白谱',
            f'这首乐曲的 BPM 是 {self.music.bpm}'
        ]
        self.round: int = 0
        '''已经提示过的轮数'''
        order: list[int] = random.sample(range(len(self.hints)), self.rounds - 1)
        self.hints_shuffled: list[str] = [f'猜歌提示 | 第{i+1}个 / 共{self.rounds}个\n{self.hints[order[i]]}'
                                          for i in range(self.rounds - 1)]
        self.finished: bool = False
        '''是否已结束'''

    def give_hint(self) -> str | Message:
        if self.round > self.rounds:
            raise ValueError
        self.round += 1
        if self.round < self.rounds:
            return self.hints_shuffled[self.round - 1]

        cover_path: Path = data_path / 'mai/cover' / f'{get_cover_len4_id(self.music.id)}.png'

        image: Image.Image = Image.open(cover_path)
        w, h = image.size
        w2, h2 = w//3, h//3
        l, u = random.randrange(0, 2*w//3), random.randrange(0, 2*h//3)
        image = image.crop((l, u, l+w2, u+h2))
        return (f'猜歌提示 | 第{self.rounds}个 / 共{self.rounds}个\n'
                '这首乐曲封面的一部分是\n'
                + MessageSegment.image(image_to_bytesio(image))
                + '\n答案将在30秒后揭晓')


guesses: dict[str, Guess] = {}
