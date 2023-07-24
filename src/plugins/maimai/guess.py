import random
from io import BytesIO
from typing import Iterable

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from PIL import Image

from .image import image_to_bytesio
from .music import Mai, Music, MusicList
from .utils import random_audio_clip


class Guess:
    async def __init__(self, music: Music | Iterable[Music] | None = None, hot: bool = True, rounds: int = 6) -> None:
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
        else:
            if not isinstance(music, Music):
                music = MusicList(music).random()
        self.music: Music = music
        '''答案'''
        self.rounds: int = rounds
        '''总轮数'''
        self.hints: list[str] = [
            f'这首乐曲 Expert 难度的等级是 {music.level[2]} ({music.ds[2]})',
            f'这首乐曲 Master 难度的等级是 {music.level[3]} ({music.ds[3]})',
            f'这首乐曲的流派是 {music.genre}',
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
        self.hints_shuffled: list[str] = [f'猜歌提示 | 第{i+1}个，共{self.rounds}个\n{self.hints[order[i]]}'
                                          for i in range(self.rounds - 1)]
        self.finished: bool = False
        '''是否已结束'''
        self.audio: BytesIO | None = await self.music.get_audio()
        self.has_audio: bool = self.audio is not None

    async def give_hint(self) -> list[str | Message | MessageSegment]:
        if self.round > self.rounds:
            raise ValueError
        self.round += 1
        if self.round < self.rounds:
            return [self.hints_shuffled[self.round - 1]]

        return await self.give_hint_cover()
        # return await self.give_hint_audio()

    async def give_hint_cover(self) -> list[Message]:
        image: Image.Image = Image.open(await self.music.get_cover())
        w, h = image.size
        w2, h2 = w//3, h//3
        l, u = random.randrange(0, 2*w//3), random.randrange(0, 2*h//3)
        image = image.crop((l, u, l+w2, u+h2))
        return [f'猜歌提示 | 第{self.rounds}个，共{self.rounds}个\n'
                '这首乐曲封面的一部分是\n'
                + MessageSegment.image(image_to_bytesio(image))
                + '\n答案将在30秒后揭晓']

    async def give_hint_audio(self) -> list[str | MessageSegment]:
        audio: BytesIO | None = await self.music.get_audio()
        assert audio is not None
        audio_clip: BytesIO = random_audio_clip(audio, 'mp3', 5.0)
        return [f'猜歌提示 | 第{self.rounds}个，共{self.rounds}个\n'
                '这首乐曲音乐的一部分是\n'
                '答案将在30秒后揭晓',
                MessageSegment.record(audio_clip)]


guesses: dict[str, Guess] = {}
