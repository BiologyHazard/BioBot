from io import BytesIO

import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from PIL.ImageDraw import ImageDraw as PILImageDraw
from PIL.ImageFont import FreeTypeFont
from .config import plugin_config
from pathlib import Path


def draw_text(img_pil, text, offset_x) -> None:
    draw: PILImageDraw = ImageDraw.Draw(img_pil)
    font: FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path), 48)
    width, height = draw.textsize(text, font)
    x = 5
    if width > 390:
        font = ImageFont.truetype(str(plugin_config.text_font_path), int(390 * 48 / width))
        width, height = draw.textsize(text, font)
    else:
        x = int((400 - width) / 2)
    draw.rectangle((x + offset_x - 2, 360,
                    x + 2 + width + offset_x, 360 + height * 1.2),
                   fill=(0, 0, 0, 255))
    draw.text((x + offset_x, 360), text, font=font, fill=(255, 255, 255, 255))


def text_to_image(text: str,
                  font_path=plugin_config.text_font_path,
                  font_size: int = 24,
                  tabs: list[float] | None = None,
                  border: float = 0.5,
                  row_spacing: float = 0.2,
                  ) -> PILImage:
    font: FreeTypeFont = ImageFont.truetype(str(font_path), font_size)
    lines: list[str] = text.splitlines()
    if tabs is None:
        tabs = [0]
    else:
        tabs.insert(0, 0)
    one_space_pixel: float = font.getlength(' ' * 64) / 64
    # tabs_pixels: list[int] = [0] + [font.getlength(' ' * x) for x in tabs]

    max_width: float = 0
    max_line_height: float = 0
    for line in lines:
        segments: list[str] = line.split('\t')
        max_line_height = max(max_line_height, font.getbbox(line)[3])
        for i, segment in enumerate(segments):
            w: int = font.getlength(segment)
            if i >= len(tabs):
                raise ValueError('Not Enough Tabs')
            max_width = max(max_width, tabs[i] * one_space_pixel + w)
    image_width: float = max_width + border * font_size * 2
    image_height: float = (max_line_height * len(lines)
                           + row_spacing * font_size * (len(lines) - 1)
                           + border * font_size * 2)
    image: PILImage = Image.new('RGB', (round(image_width), round(image_height)), color='white')
    draw: PILImageDraw = ImageDraw.Draw(image)

    y: float = border * font_size
    for line in lines:
        segments: list[str] = line.split('\t')
        for i, segment in enumerate(segments):
            draw.text((border * font_size + tabs[i] * one_space_pixel - 1/2, y - 1/2), segment, font=font, fill='black')
        y += max_line_height + row_spacing * font_size
    return image


def image_to_bytesio(img: PILImage, format='PNG') -> BytesIO:
    bytesio = BytesIO()
    img.save(bytesio, format)
    bytesio.seek(0)
    return bytesio


async def get_user_logo(qq: int) -> PILImage:
    async with aiohttp.request('GET', f'http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100') as response:
        return Image.open(BytesIO(await response.read()))


def get_cover_len4_id(music_id: str) -> str:
    return f'{int(music_id) % 10000 :04d}'


async def get_cover(music_id: str) -> bytes:
    '''获取封面'''
    filename: str = f'{get_cover_len4_id(music_id)}.png'
    cover_path: Path = plugin_config.cover_path / filename
    if cover_path.is_file():
        async with aiofiles.open(cover_path, 'rb') as fp:
            # 从本地图片读取
            return await fp.read()

    async with aiohttp.request('GET', f'https://www.diving-fish.com/covers/{filename}') as response:
        if response.status == 200:
            cover_bytes: bytes = await response.read()
            async with aiofiles.open(cover_path, 'wb') as fp:
                await fp.write(cover_bytes)
            # 从水鱼网下载
            return cover_bytes

    async with aiofiles.open(plugin_config.cover_path / '0000.png', 'rb') as fp:
        # 返回'0000.png'
        return await fp.read()
