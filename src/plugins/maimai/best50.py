from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .config import plugin_config
from .consts import combo_rank, score_rank, sync_rank
from .image import get_user_avatar, image_to_bytesio
from .music import Mai, get_music_cover


class DrawText:
    def __init__(self, image: ImageDraw.ImageDraw, font: Path) -> None:
        self._img: ImageDraw.ImageDraw = image
        self._font: Path = font

    def get_box(self, text: str, size: int) -> tuple[int, int, int, int]:
        return ImageFont.truetype(str(self._font), size).getbbox(text)

    def draw(self,
             pos_x: int,
             pos_y: int,
             size: int,
             text: str,
             color: tuple[int, int, int, int] = (255, 255, 255, 255),
             anchor: str = 'lt',
             stroke_width: int = 0,
             stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 0),
             multiline: bool = False,
             ) -> None:

        font: ImageFont.FreeTypeFont = ImageFont.truetype(str(self._font), size)
        if multiline:
            self._img.multiline_text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)


@dataclass
class ChartInfo:
    id: str
    title: str
    level: int
    achievement: float
    dxscore: int
    rate: int
    ra: int
    fc: int
    fs: int
    ds: float
    type: str

    @classmethod
    def from_json(cls, data) -> Self:
        return cls(
            id=data['song_id'],
            title=data['title'],
            level=data['level_index'],
            achievement=data['achievements'],
            dxscore=data['dxScore'],
            rate=score_rank.index(data['rate']),
            ra=data['ra'],
            fc=combo_rank.index(data['fc']),
            fs=sync_rank.index(data['fs']),
            ds=data['ds'],
            type=data['type']
        )


class DrawBest:
    def __init__(self,
                 sd_best: list[ChartInfo],
                 dx_best: list[ChartInfo],
                 username: str,
                 rating: int,
                 additional_rating: int,
                 plate: str,
                 qqid: int | None = None,
                 ) -> None:
        self.sd_best: list[ChartInfo] = sorted(sd_best, key=lambda x: x.ra, reverse=True)
        self.ds_best: list[ChartInfo] = sorted(dx_best, key=lambda x: x.ra, reverse=True)
        self.username: str = username
        self.additional_rating: int = additional_rating
        self.rating: int = rating
        self.plate: str = plate
        self.qqid: int | None = qqid

    def _getCharWidth(self, o) -> int:
        widths = [
            (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
            (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
            (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
            (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
            (120831, 1), (262141, 2), (1114109, 1),
        ]
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            if o <= num:
                return wid
        return 1

    def _coloumWidth(self, s: str) -> int:
        res = 0
        for ch in s:
            res += self._getCharWidth(ord(ch))
        return res

    def _changeColumnWidth(self, s: str, len: int) -> str:
        res = 0
        sList = []
        for ch in s:
            res += self._getCharWidth(ord(ch))
            if res <= len:
                sList.append(ch)
        return ''.join(sList)

    def _dxScore(self, info: ChartInfo) -> tuple[int, int]:
        value: int = Mai.music_list.by_id(str(info.id), strict=True).charts[info.level].notes
        dx = info.dxscore / (value * 3) * 100
        if dx <= 85:
            result = (0, 0)
        elif dx <= 90:
            result = (0, 1)
        elif dx <= 93:
            result = (0, 2)
        elif dx <= 95:
            result = (1, 3)
        elif dx <= 97:
            result = (1, 4)
        else:
            result = (2, 5)
        return result

    def _findRaPic(self) -> str:
        n: int = bisect_right([1000, 2000, 4000, 7000, 10000, 12000, 13000, 14000, 14500, 15000], self.rating)
        return f'UI_CMN_DXRating_{n+1:02d}.png'

    def _findMatchLevel(self) -> str:
        n: int = self.additional_rating if self.additional_rating <= 10 else self.additional_rating + 1
        return f'UI_DNM_DaniPlate_{n:02d}.png'

    async def whiledraw(self, data: list[ChartInfo], type: bool) -> None:
        # y0为第一排纵向坐标，dy为各排间距
        y0 = 430 if type else 1670
        dy = 170

        TITLE_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (192, 32, 56, 255), (103, 20, 141, 255), (230, 230, 230, 255)]
        TEXT_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (175, 0, 50, 255), (103, 20, 141, 255), (103, 20, 141, 255)]
        rankPic = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'Sp', 'SS', 'SSp', 'SSS', 'SSSp']
        comboPic = ['', 'FC', 'FCp', 'AP', 'APp']
        syncPic = ['', 'FS', 'FSp', 'FSD', 'FSDp']

        dxstar = [Image.open(plugin_config.pic_path / f'UI_RSL_DXScore_Star_0{i+1}.png').resize((20, 20)) for i in range(3)]

        for num, info in enumerate(data):
            info: ChartInfo
            x: int = 100 + (num % 5) * 404
            y: int = y0 + (num // 5) * dy

            cover = Image.open(await get_music_cover(info.id)).convert('RGBA').resize((135, 135))
            version = Image.open(plugin_config.pic_path / f'UI_RSL_MBase_Parts_{info.type}.png').resize((55, 19))
            rate = Image.open(plugin_config.pic_path / f'UI_TTR_PhotoParts_{rankPic[info.rate]}.png').resize((80, 50))

            self._im.alpha_composite(self._diff[info.level], (x, y))
            self._im.alpha_composite(cover, (x + 5, y + 5))
            self._im.alpha_composite(version, (x + 80, y + 141))
            self._im.alpha_composite(rate, (x + 153, y + 68))
            if info.fc:
                fc = Image.open(plugin_config.pic_path / f'UI_MSS_MBase_Icon_{comboPic[info.fc]}.png').resize((45, 45))
                self._im.alpha_composite(fc, (x + 240, y + 70))
            if info.fs:
                fs = Image.open(plugin_config.pic_path / f'UI_MSS_MBase_Icon_{syncPic[info.fs]}.png').resize((45, 45))
                self._im.alpha_composite(fs, (x + 285, y + 70))

            dx = self._dxScore(info)
            for _ in range(dx[1]):
                self._im.alpha_composite(dxstar[dx[0]], (x + 355, y + 40 + 20 * _))

            self._tb.draw(x + 40, y + 148, 20, info.id, anchor='mm')
            title = info.title
            if self._coloumWidth(title) > 16:
                title = self._changeColumnWidth(title, 15) + '...'
            self._siyuanb.draw(x + 155, y + 20, 20, title, TITLE_COLOR[info.level], anchor='lm')
            p, s = f'{info.achievement:.4f}'.split('.')
            r = self._tb.get_box(p, 40)
            self._tb.draw(x + 155, y + 73, 38, p, TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155 + r[2], y + 71, 28, f'.{s}%', TEXT_COLOR[info.level], anchor='ld')
            # p, s = f'{info.achievement:.4f}'.split('.')
            # r = self._tb.get_box(p, 35)
            # self._tb.draw(x + 155, y + 70, 35, p, TEXT_COLOR[info.level], anchor='ld')
            # self._tb.draw(x + 155 + r[2], y + 68, 25, f'.{s}%', TEXT_COLOR[info.level], anchor='ld')
            # self._tb.draw(x + 155, y + 70, 35, f'{info.achievement:.4f}%', TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155, y + 125, 22, f'Rating {info.ds} -> {info.ra}', TEXT_COLOR[info.level], anchor='lm')

    async def draw(self) -> Image.Image:
        meiryo: Path = plugin_config.font_path / 'meiryo.ttc'
        siyuanb: Path = plugin_config.font_path / 'SourceHanSansSC-Bold.otf'
        siyuan: Path = plugin_config.font_path / 'SourceHanSans.otf'
        Torus_SemiBold: Path = plugin_config.font_path / 'Torus SemiBold.otf'
        basic: Image.Image = Image.open(plugin_config.pic_path / 'b40_score_basic.png')
        advanced: Image.Image = Image.open(plugin_config.pic_path / 'b40_score_advanced.png')
        expert: Image.Image = Image.open(plugin_config.pic_path / 'b40_score_expert.png')
        master: Image.Image = Image.open(plugin_config.pic_path / 'b40_score_master.png')
        remaster: Image.Image = Image.open(plugin_config.pic_path / 'b40_score_remaster.png')
        logo: Image.Image = Image.open(plugin_config.pic_path / 'BioBot/logo.png').resize((567, 172))
        dx_rating: Image.Image = Image.open(plugin_config.pic_path / self._findRaPic()).resize((425, 80))
        Name: Image.Image = Image.open(plugin_config.pic_path / 'Name.png')
        # MatchLevel = Image.open(os.path.join(self.maimai_dir, self._findMatchLevel())).resize((134, 55))
        MatchLevel: Image.Image = Image.open(plugin_config.pic_path / self._findMatchLevel()).resize((128, 58))
        rating: Image.Image = Image.open(plugin_config.pic_path / 'UI_CMN_Shougou_Rainbow.png').resize((454, 50))
        self._diff: list[Image.Image] = [basic, advanced, expert, master, remaster]

        # 作图
        self._im = Image.open(plugin_config.pic_path / 'b40_bg.png').convert('RGBA')

        self._im.alpha_composite(logo, (-72, 130))
        if self.plate:
            plate = Image.open(plugin_config.pic_path / f'{self.plate}.png').resize((1420, 230))
        else:
            plate = Image.open(plugin_config.pic_path / 'UI_Plate_000011.png').resize((1420, 230))
        self._im.alpha_composite(plate, (390, 100))
        icon = Image.open(plugin_config.pic_path / 'UI_Icon_0000.png').resize((214, 214))
        self._im.alpha_composite(icon, (398, 108))
        if self.qqid:
            qqLogo = await get_user_avatar(self.qqid)
            self._im.alpha_composite(Image.new('RGBA', (203, 203), (255, 255, 255, 255)), (404, 114))
            self._im.alpha_composite(qqLogo.convert('RGBA').resize((201, 201)), (405, 115))
        self._im.alpha_composite(dx_rating, (620, 108))
        for n, i in enumerate(f'{self.rating:05d}'):
            if i == 0:
                continue
            self._im.alpha_composite(Image.open(plugin_config.pic_path / f'UI_NUM_Drating_{i}.png'),
                                     (round(821 + 33.5 * n), 133))
        self._im.alpha_composite(Name, (620, 200))
        self._im.alpha_composite(MatchLevel, (935, 205))
        self._im.alpha_composite(rating, (620, 275))

        text_im = ImageDraw.Draw(self._im)
        self._meiryo = DrawText(text_im, meiryo)
        self._siyuanb = DrawText(text_im, siyuanb)
        self._siyuan = DrawText(text_im, siyuan)
        self._tb = DrawText(text_im, Torus_SemiBold)

        # self._meiryo.draw(635, 235, 40, self.userName, (0, 0, 0, 255), 'lm')
        self._siyuan.draw(635, 232, 40, self.username, (0, 0, 0, 255), 'lm')
        _sd_rating: int = sum(music.ra for music in self.sd_best)
        _dx_rating: int = sum(music.ra for music in self.ds_best)
        # self._meiryo.draw(847, 300, 22, f'历史版本: {_sd_rating} + DX 2023: {_dx_rating}', (0, 0, 0, 255), 'mm', 3, (255, 255, 255, 255))
        self._siyuan.draw(847, 296, 25, f'历史版本: {_sd_rating} + DX 2023: {_dx_rating}', (0, 0, 0, 255), 'mm', 3, (255, 255, 255, 255))
        self._meiryo.draw(900, 2365, 35, f'Designed by Yuri-YuzuChaN & BlueDeer233 | Generated by BioBot', (103, 20, 141, 255), 'mm', 3, (255, 255, 255, 255))

        await self.whiledraw(self.sd_best, True)
        await self.whiledraw(self.ds_best, False)

        return self._im


async def generate_b50(payload: dict, queryer: int) -> MessageSegment | str:
    payload['b50'] = True
    data: dict[str, Any] | str = await get_player_data('best', payload, queryer)
    if isinstance(data, str):
        return data

    qqid: int | None = payload['qq'] if 'qq' in payload else None
    sd_best: list[ChartInfo] = [ChartInfo.from_json(c) for c in data['charts']['sd']]
    dx_best: list[ChartInfo] = [ChartInfo.from_json(c) for c in data['charts']['dx']]
    draw_best = DrawBest(sd_best, dx_best, data['nickname'], data['rating'], data['additional_rating'], data['plate'], qqid)
    return MessageSegment.image(image_to_bytesio(await draw_best.draw()))
