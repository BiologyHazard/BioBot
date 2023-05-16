import base64
from io import BytesIO

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as PILImage
from PIL.ImageDraw import ImageDraw as PILImageDraw
from PIL.ImageFont import FreeTypeFont

fontpath = "data/maimai/fonts/SourceHanSans.otf"


def draw_text(img_pil, text, offset_x) -> None:
    draw: PILImageDraw = ImageDraw.Draw(img_pil)
    font: FreeTypeFont = ImageFont.truetype(fontpath, 48)
    width, height = draw.textsize(text, font)
    x = 5
    if width > 390:
        font = ImageFont.truetype(fontpath, int(390 * 48 / width))
        width, height = draw.textsize(text, font)
    else:
        x = int((400 - width) / 2)
    draw.rectangle((x + offset_x - 2, 360,
                    x + 2 + width + offset_x, 360 + height * 1.2),
                   fill=(0, 0, 0, 255))
    draw.text((x + offset_x, 360), text, font=font, fill=(255, 255, 255, 255))


def text_to_image(text: str) -> PILImage:
    font: FreeTypeFont = ImageFont.truetype(fontpath, 24)
    padding: int = 10
    margin: int = 4
    text_list: list[str] = text.split('\n')
    max_width: int = 0
    h: int = 0
    for text in text_list:
        w, h = font.getsize(text)
        max_width: int = max(max_width, w)
    wa: int = max_width + padding * 2
    ha: int = h * len(text_list) + margin * (len(text_list) - 1) + padding * 2
    i: PILImage = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    draw: PILImageDraw = ImageDraw.Draw(i)
    for j in range(len(text_list)):
        text = text_list[j]
        draw.text((padding, padding + j * (margin + h)), text, font=font, fill=(0, 0, 0))
    return i


def image_to_bytesio(img: PILImage, format_='PNG') -> BytesIO:
    bytesio = BytesIO()
    img.save(bytesio, format_)
    bytesio.seek(0)
    return bytesio


async def get_user_logo(qq: int) -> PILImage:
    async with aiohttp.request('GET', f'http://q1.qlogo.cn/g?b=qq&nk={qq}&s=100') as resp:
        return Image.open(BytesIO(await resp.read()))
