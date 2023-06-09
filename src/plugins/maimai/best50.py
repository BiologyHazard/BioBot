from typing import Any
import math
import os
from typing import Literal, overload

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL import Image, ImageDraw, ImageFont

from .api_data import get_player_data
from .consts import *
from .image import get_music_cover, get_user_logo, image_to_bytesio
from .music import Mai

static = 'data/maimai'


class DrawText:

    def __init__(self, image: ImageDraw.ImageDraw, font: str) -> None:
        self._img = image
        self._font = font

    def get_box(self, text: str, size: int):
        return ImageFont.truetype(self._font, size).getbbox(text)

    def draw(self,
             pos_x: int,
             pos_y: int,
             size: int,
             text: str,
             color: tuple[int, int, int, int] = (255, 255, 255, 255),
             anchor: str = 'lt',
             stroke_width: int = 0,
             stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 0),
             multiline: bool = False):

        font = ImageFont.truetype(self._font, size)
        if multiline:
            self._img.multiline_text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)

    def draw_partial_opacity(self,
                             pos_x: int,
                             pos_y: int,
                             size: int,
                             text: str,
                             po: int = 2,
                             color: tuple[int, int, int, int] = (255, 255, 255, 255),
                             anchor: str = 'lt',
                             stroke_width: int = 0,
                             stroke_fill: tuple[int, int, int, int] = (0, 0, 0, 0)):

        font = ImageFont.truetype(self._font, size)
        self._img.text((pos_x + po, pos_y + po), str(text), (0, 0, 0, 128), font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        self._img.text((pos_x, pos_y), str(text), color, font, anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)


class ChartInfo(object):
    def __init__(self, id: str, title: str, level: int, achievement: float, dxscore: int, rate: int, ra: int, fc: int, fs: int, ds: float, type: str):
        self.id = id
        self.title = title
        self.level = level
        self.achievement = achievement
        self.dxscore = dxscore
        self.rate = rate
        self.ra = ra
        self.fc = fc
        self.fs = fs
        self.ds = ds
        self.type = type

    def __eq__(self, other):
        return self.ra == other.ra

    def __lt__(self, other):
        return self.ra < other.ra

    @classmethod
    def from_json(cls, data):
        rate = ['d', 'c', 'b', 'bb', 'bbb', 'a', 'aa', 'aaa', 's', 'sp', 'ss', 'ssp', 'sss', 'sssp']
        ri = rate.index(data['rate'])
        fc = ['', 'fc', 'fcp', 'ap', 'app']
        fi = fc.index(data['fc'])
        fs = ['', 'fs', 'fsp', 'fsd', 'fsdp']
        si = fs.index(data['fs'])
        return cls(
            id=data['song_id'],
            title=data['title'],
            level=data['level_index'],
            achievement=data['achievements'],
            dxscore=data['dxScore'],
            rate=ri,
            ra=data['ra'],
            fc=fi,
            fs=si,
            ds=data['ds'],
            type=data['type']
        )


class BestList(object):

    def __init__(self, size: int):
        self.data: list[ChartInfo] = []
        self.size = size

    def push(self, elem: ChartInfo):
        if len(self.data) >= self.size and elem < self.data[-1]:
            return
        self.data.append(elem)
        self.data.sort(key=lambda x: x.ra)
        self.data.reverse()
        while (len(self.data) > self.size):
            del self.data[-1]

    def __getitem__(self, index):
        return self.data[index]


class DrawBest:

    def __init__(self, sdBest: BestList,
                 dxBest: BestList,
                 userName: str,
                 addRating: int,
                 rankRating: int,
                 plate: str,
                 qqId: int | None = None,
                 ) -> None:
        self.sdBest: BestList = sdBest
        self.dxBest: BestList = dxBest
        self.userName: str = userName
        self.addRating: int = addRating
        self.rankRating: int = rankRating
        self.Rating: int = rankRating
        self.plate: str = plate
        self.qqId: int | None = qqId
        self.cover_dir: str = os.path.join(static, 'mai', 'cover')
        self.maimai_dir: str = os.path.join(static, 'mai', 'pic')

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
        if self.Rating < 1000:
            num = '01'
        elif self.Rating < 2000:
            num = '02'
        elif self.Rating < 4000:
            num = '03'
        elif self.Rating < 7000:
            num = '04'
        elif self.Rating < 10000:
            num = '05'
        elif self.Rating < 12000:
            num = '06'
        elif self.Rating < 13000:
            num = '07'
        elif self.Rating < 14000:
            num = '08'
        elif self.Rating < 14500:
            num = '09'
        elif self.Rating < 15000:
            num = '10'
        else:
            num = '11'
        return f'UI_CMN_DXRating_{num}.png'

    def _findMatchLevel(self) -> str:
        ra = [1000, 1200, 1400, 1500, 1600, 1700, 1800, 1850, 1900, 1950, 2000, 2010, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
        for n, v in enumerate(ra):
            if self.addRating < v:
                return f'UI_DNM_DaniPlate_{n:02d}.png'
            elif n == (len(ra) - 1) and self.addRating >= v:
                return f'UI_DNM_DaniPlate_{n:02d}.png'
        raise ValueError

    async def whiledraw(self, data: BestList, type: bool) -> None:
        # y0为第一排纵向坐标，dy为各排间距
        y0 = 430 if type else 1670
        dy = 170

        TITLE_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (192, 32, 56, 255), (103, 20, 141, 255), (230, 230, 230, 255)]
        TEXT_COLOR = [(14, 117, 54, 255), (199, 69, 12, 255), (175, 0, 50, 255), (103, 20, 141, 255), (103, 20, 141, 255)]
        rankPic = ['D', 'C', 'B', 'BB', 'BBB', 'A', 'AA', 'AAA', 'S', 'Sp', 'SS', 'SSp', 'SSS', 'SSSp']
        comboPic = ['', 'FC', 'FCp', 'AP', 'APp']
        syncPic = ['', 'FS', 'FSp', 'FSD', 'FSDp']

        dxstar = [Image.open(os.path.join(self.maimai_dir, f'UI_RSL_DXScore_Star_0{_ + 1}.png')).resize((20, 20)) for _ in range(3)]

        for num, info in enumerate(data.data):
            info: ChartInfo
            x: int = 100 + (num % 5) * 404
            y: int = y0 + (num // 5) * dy

            cover = Image.open(await get_music_cover(info.id)).resize((135, 135))
            version = Image.open(os.path.join(self.maimai_dir, f'UI_RSL_MBase_Parts_{info.type}.png')).resize((55, 19))
            rate = Image.open(os.path.join(self.maimai_dir, f'UI_TTR_PhotoParts_{rankPic[info.rate]}.png')).resize((80, 50))

            self._im.alpha_composite(self._diff[info.level], (x, y))
            self._im.alpha_composite(cover, (x + 5, y + 5))
            self._im.alpha_composite(version, (x + 80, y + 141))
            self._im.alpha_composite(rate, (x + 153, y + 68))
            if info.fc:
                fc = Image.open(os.path.join(self.maimai_dir, f'UI_MSS_MBase_Icon_{comboPic[info.fc]}.png')).resize((45, 45))
                self._im.alpha_composite(fc, (x + 240, y + 70))
            if info.fs:
                fs = Image.open(os.path.join(self.maimai_dir, f'UI_MSS_MBase_Icon_{syncPic[info.fs]}.png')).resize((45, 45))
                self._im.alpha_composite(fs, (x + 285, y + 70))

            dx = self._dxScore(info)
            for _ in range(dx[1]):
                self._im.alpha_composite(dxstar[dx[0]], (x + 355, y + 40 + 20 * _))

            self._tb.draw(x + 40, y + 148, 20, info.id, anchor='mm')
            title = info.title
            if self._coloumWidth(title) > 16:
                title = self._changeColumnWidth(title, 15) + '...'
            self._siyuan.draw(x + 155, y + 20, 20, title, TITLE_COLOR[info.level], anchor='lm')
            p, s = f'{info.achievement:.4f}'.split('.')
            r = self._tb.get_box(p, 35)
            self._tb.draw(x + 155, y + 70, 35, p, TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155 + r[2], y + 68, 25, f'.{s}%', TEXT_COLOR[info.level], anchor='ld')
            self._tb.draw(x + 155, y + 125, 22, f'Rating {info.ds} -> {info.ra}', TEXT_COLOR[info.level], anchor='lm')

    async def draw(self) -> Image.Image:
        meiryo = os.path.join(static, 'meiryo.ttc')
        siyuan = os.path.join(static, 'SourceHanSansSC-Bold.otf')
        Torus_SemiBold = os.path.join(static, 'Torus SemiBold.otf')
        basic = Image.open(os.path.join(self.maimai_dir, 'b40_score_basic.png'))
        advanced = Image.open(os.path.join(self.maimai_dir, 'b40_score_advanced.png'))
        expert = Image.open(os.path.join(self.maimai_dir, 'b40_score_expert.png'))
        master = Image.open(os.path.join(self.maimai_dir, 'b40_score_master.png'))
        remaster = Image.open(os.path.join(self.maimai_dir, 'b40_score_remaster.png'))
        logo = Image.open(os.path.join(self.maimai_dir, 'logo.png')).resize((378, 172))
        dx_rating = Image.open(os.path.join(self.maimai_dir, self._findRaPic())).resize((425, 80))
        Name = Image.open(os.path.join(self.maimai_dir, 'Name.png'))
        MatchLevel = Image.open(os.path.join(self.maimai_dir, self._findMatchLevel())).resize((134, 55))
        rating = Image.open(os.path.join(self.maimai_dir, 'UI_CMN_Shougou_Rainbow.png')).resize((454, 50))
        self._diff = [basic, advanced, expert, master, remaster]

        # 作图
        self._im = Image.open(os.path.join(self.maimai_dir, 'b40_bg.png')).convert('RGBA')

        self._im.alpha_composite(logo, (5, 130))
        if self.plate:
            plate = Image.open(os.path.join(self.maimai_dir, f'{self.plate}.png')).resize((1420, 230))
        else:
            plate = Image.open(os.path.join(self.maimai_dir, 'UI_Plate_000011.png')).resize((1420, 230))
        self._im.alpha_composite(plate, (390, 100))
        icon = Image.open(os.path.join(self.maimai_dir, 'UI_Icon_0000.png')).resize((214, 214))
        self._im.alpha_composite(icon, (398, 108))
        if self.qqId:
            qqLogo = await get_user_logo(self.qqId)
            self._im.alpha_composite(Image.new('RGBA', (203, 203), (255, 255, 255, 255)), (404, 114))
            self._im.alpha_composite(qqLogo.convert('RGBA').resize((201, 201)), (405, 115))
        self._im.alpha_composite(dx_rating, (620, 108))
        for n, i in enumerate(f'{self.Rating:05d}'):
            if n == 0 and i == 0:
                continue
            self._im.alpha_composite(Image.open(os.path.join(self.maimai_dir, f'UI_NUM_Drating_{i}.png')), (820 + 33 * n, 133))
        self._im.alpha_composite(Name, (620, 200))
        self._im.alpha_composite(MatchLevel, (935, 205))
        self._im.alpha_composite(rating, (620, 275))

        text_im = ImageDraw.Draw(self._im)
        self._meiryo = DrawText(text_im, meiryo)
        self._siyuan = DrawText(text_im, siyuan)
        self._tb = DrawText(text_im, Torus_SemiBold)

        self._meiryo.draw(635, 235, 40, self.userName, (0, 0, 0, 255), 'lm')
        self._meiryo.draw(847, 300, 22, f'底分：{self.rankRating}', (0, 0, 0, 255), 'mm', 3, (255, 255, 255, 255))
        self._meiryo.draw(900, 2365, 35, f'Designed by Yuri-YuzuChaN & BlueDeer233 | Generated by BioBot', (103, 20, 141, 255), 'mm', 3, (255, 255, 255, 255))

        await self.whiledraw(self.sdBest, True)
        await self.whiledraw(self.dxBest, False)

        return self._im


async def generate(payload: dict, queryer: int) -> MessageSegment | str:
    payload['b50'] = True
    data: dict[str, Any] | str = await get_player_data('best', payload, queryer)
    if isinstance(data, str):
        return data
    qqid: int | None = payload['qq'] if 'qq' in payload else None
    sd_best = BestList(35)
    dx_best = BestList(15)

    for c in data['charts']['sd']:
        sd_best.push(ChartInfo.from_json(c))
    for c in data['charts']['dx']:
        dx_best.push(ChartInfo.from_json(c))
    draw_best = DrawBest(sd_best, dx_best, data['nickname'], data['additional_rating'], data['rating'], data['plate'], qqid)
    pic: Image.Image = await draw_best.draw()
    return MessageSegment.image(image_to_bytesio(pic))
