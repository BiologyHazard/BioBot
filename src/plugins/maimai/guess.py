import random
from pathlib import Path

from nonebot.adapters.onebot.v11 import MessageSegment, Message
from PIL import Image

from .config import plugin_config
from .image import get_cover_len4_id, image_to_bytesio
from .music import Mai, Music


class Guess:
    def __init__(self, music: Music | None = None, hot: bool = True, rounds: int = 6) -> None:
        '''
        `music`: 指定乐曲，`None`则随机
        `hot`: `music`为`None`时，随机的范围是否限制在热门乐曲
        `rounds`: 提示的轮数
        '''
        if music is None:
            if hot:
                music = Mai.hot_music_list.random()
            else:
                music = Mai.music_list.random()
        self.music: Music = music
        '''答案'''
        self.rounds: int = rounds
        '''总轮数'''
        self.hints: list[str] = [
            f'这首乐曲 Expert 难度的等级是 {music.level[2]} ({music.ds[2]})',
            f'这首乐曲 Master 难度的等级是 {music.level[3]} ({music.ds[3]})',
            f'这首乐曲的流派是 {music.genre_han}',
            f'这首乐曲的版本是 {music.version}（{music.version_han}代）',
            f'这首乐曲的艺术家是 {music.artist}',
            f'这首乐曲{"不" if music.type == "SD" else ""}是 DX 谱面',
            f'这首乐曲{"没" if not music.has_remaster else ""}有白谱',
            f'这首乐曲的速度是 {music.bpm}bpm',
            f'这首乐曲 Master 难度的谱师是 {music.charts[3].charter}',
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

        cover_path: Path = plugin_config.data_path / 'mai/cover' / f'{get_cover_len4_id(self.music.id)}.png'

        image: Image.Image = Image.open(cover_path)
        w, h = image.size
        w2, h2 = w//3, h//3
        l, u = random.randrange(0, 2*w//3), random.randrange(0, 2*h//3)
        image = image.crop((l, u, l+w2, u+h2))
        return (f'猜歌提示 | 第{self.rounds}个，共{self.rounds}个\n'
                '这首乐曲封面的一部分是\n'
                + MessageSegment.image(image_to_bytesio(image))
                + '\n答案将在30秒后揭晓')


guesses: dict[str, Guess] = {}
