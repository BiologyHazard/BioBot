from nonebot import logger
from functools import lru_cache
import random
import math
from io import BytesIO

import aiohttp
import aiofiles
from PIL import Image, ImageDraw, ImageFont
from .config import plugin_config
from pathlib import Path


# def image_resize_by(image: Image.Image, size: float) -> Image.Image:
#     return image.resize((round(image.width * size), round(image.height * size)))


def image_resize_to(image: Image.Image, size: tuple[float, None] | tuple[None, float], *args, **kwargs) -> Image.Image:
    w, h = image.size
    if size[1] is None:
        return image.resize((round(size[0]), round(size[0] * h / w)), *args, **kwargs)
    else:
        return image.resize((round(size[1] * w / h), round(size[1])), *args, **kwargs)


# def draw_text(img_pil, text, offset_x) -> None:
#     draw: PILImageDraw = ImageDraw.Draw(img_pil)
#     font: FreeTypeFont = ImageFont.truetype(str(plugin_config.text_font_path), 48)
#     width, height = draw.textsize(text, font)
#     x = 5
#     if width > 390:
#         font = ImageFont.truetype(str(plugin_config.text_font_path), int(390 * 48 / width))
#         width, height = draw.textsize(text, font)
#     else:
#         x = int((400 - width) / 2)
#     draw.rectangle((x + offset_x - 2, 360,
#                     x + 2 + width + offset_x, 360 + height * 1.2),
#                    fill=(0, 0, 0, 255))
#     draw.text((x + offset_x, 360), text, font=font, fill=(255, 255, 255, 255))


def text_to_image(text: str,
                  font_path=plugin_config.text_font_path,
                  font_size: float = 24.0,
                  tabs: list[float] | None = None,
                  border: float = 1.0,
                  row_spacing: float = 0.2,
                  *args,
                  **kwargs,
                  ) -> Image.Image:
    font: ImageFont.FreeTypeFont = ImageFont.truetype(str(font_path), round(font_size))
    lines: list[str] = text.splitlines()
    if tabs is None:
        tabs = [0]
    else:
        tabs.insert(0, 0)
    one_space_pixel: float = font.getlength('　')

    max_width: float = 0
    max_line_height: float = 0
    for line in lines:
        segments: list[str] = line.split('\t')
        max_line_height = max(max_line_height, font.getbbox(line)[3])
        for i, segment in enumerate(segments):
            if not segment.endswith('\0'):
                w: int = font.getlength(segment)
            else:
                w = 0
            if i >= len(tabs):
                raise ValueError('Not Enough Tabs')
            max_width = max(max_width, tabs[i] * one_space_pixel + w)
    image_width: float = max_width + border * font_size * 2
    image_height: float = (max_line_height * len(lines)
                           + row_spacing * font_size * (len(lines) - 1)
                           + border * font_size * 2)
    # image: PILImage = Image.new('RGB', (round(image_width), round(image_height)), color='white')
    image: Image.Image = background_image(image_width, image_height, font_size * 4, 0.5)
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)

    y: float = border * font_size
    for line in lines:
        segments: list[str] = line.split('\t')
        for i, segment in enumerate(segments):
            if not segment.endswith('\0'):
                anchor: str = 'la'
            else:
                anchor = 'ra'
                segment: str = segment[:-1]
            draw.text((border * font_size + tabs[i] * one_space_pixel, y), segment,
                      'black', font, anchor, *args, **kwargs)
        y += max_line_height + row_spacing * font_size
    return image


def image_to_bytesio(img: Image.Image, format='PNG') -> BytesIO:
    bytesio = BytesIO()
    img.save(bytesio, format)
    bytesio.seek(0)
    return bytesio


async def get_user_logo(qq: int) -> Image.Image:
    async with aiohttp.request('GET', f'http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100') as response:
        return Image.open(BytesIO(await response.read()))


def get_cover_filename(music_id: str) -> str:
    num = int(music_id)
    if 10000 < num <= 11000:
        num -= 10000
    return f'{num:05d}.png'


@lru_cache
async def get_music_cover(music_id: str) -> BytesIO:
    '''获取封面'''
    filename = get_cover_filename(music_id)
    cover_path: Path = plugin_config.cover_path / filename
    if cover_path.is_file():
        async with aiofiles.open(cover_path, 'rb') as fp:
            # 从本地图片读取
            return BytesIO(await fp.read())

    async with aiohttp.request('GET', f'https://www.diving-fish.com/covers/{filename}') as response:
        if response.status == 200:
            cover_bytes: bytes = await response.read()
            async with aiofiles.open(cover_path, 'wb') as fp:
                await fp.write(cover_bytes)
            # 从水鱼网下载
            return BytesIO(cover_bytes)

    async with aiofiles.open(plugin_config.cover_path / '00000.png', 'rb') as fp:
        # 返回'00000.png'
        return BytesIO(await fp.read())


@lru_cache
def background_image(width: float, height: float, side_pixels: float, alpha: float = 1) -> Image.Image:
    image: Image.Image = (
        Image.open(plugin_config.pic_path / 'BioBot/background.png')
        .resize((round(width), round(height)))
    )
    top_image: Image.Image = image_resize_to(Image.open(plugin_config.pic_path / 'BioBot/top.png'),
                                             (2.52 * width, None))
    bottom_image: Image.Image = image_resize_to(Image.open(plugin_config.pic_path / 'BioBot/bottom.png'),
                                                (2.06 * width, None))
    left_image: Image.Image = image_resize_to(Image.open(plugin_config.pic_path / 'BioBot/left.png'),
                                              (None, side_pixels))
    right_image: Image.Image = image_resize_to(Image.open(plugin_config.pic_path / 'BioBot/right.png'),
                                               (None, side_pixels))
    bubbles_image: Image.Image = image_resize_to(Image.open(plugin_config.pic_path / 'BioBot/bubbles.png'),
                                                 (1.35 * width, None))
    for i in range(math.ceil(image.height / bubbles_image.height)):
        # 反正最大容许偏移量就是这么多，我也解释不明白
        image.alpha_composite(bubbles_image,
                              (round(-0.35 * random.random() * width),
                               i * bubbles_image.height))
    for i in range(math.ceil(image.height / left_image.height)):
        image.alpha_composite(left_image, (0, i * left_image.height))
    for i in range(math.ceil(image.height / right_image.height)):
        image.alpha_composite(right_image, (image.width - right_image.width,
                                            i * right_image.height))
    image.alpha_composite(top_image, (round(-0.15 * width), 0))
    image.alpha_composite(bottom_image, (round(-0.15 * width),
                                         image.height - bottom_image.height))

    mask: Image.Image = Image.new('RGBA', image.size, 'white')
    return Image.blend(mask, image, alpha)
