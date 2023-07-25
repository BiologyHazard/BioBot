from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from .config import plugin_config
from pil_utils import text2image, Text2Image


def text_to_image(text: str,
                  font_path=plugin_config.text_font_path,
                  font_size: float = 24.0,
                  tabs: list[float] | None = None,
                  border: float = 1.625,
                  row_spacing: float = 0.2,
                  *args,
                  **kwargs,
                  ) -> Image.Image:
    return Text2Image.from_text(text, round(font_size)).to_image('white', (10, 10))
#     font: ImageFont.FreeTypeFont = ImageFont.truetype(str(font_path), round(font_size))
#     lines: list[str] = text.splitlines()
#     if tabs is None:
#         tabs = [0]
#     else:
#         tabs.insert(0, 0)
#     one_space_pixel: float = font.getlength('　')

#     max_width: float = 0
#     max_line_height: float = 0
#     for line in lines:
#         segments: list[str] = line.split('\t')
#         max_line_height = max(max_line_height, font.getbbox(line)[3])
#         for i, segment in enumerate(segments):
#             if not segment.endswith('\0'):
#                 w: int = font.getlength(segment)
#             else:
#                 w = 0
#             if i >= len(tabs):
#                 raise ValueError('Not Enough Tabs')
#             max_width = max(max_width, tabs[i] * one_space_pixel + w)
#     image_width: float = max_width + border * font_size * 2
#     image_height: float = (max_line_height * len(lines)
#                            + row_spacing * font_size * (len(lines) - 1)
#                            + border * font_size * 2)
#     # image: PILImage = Image.new('RGB', (round(image_width), round(image_height)), color='white')
#     image: Image.Image = background_image(image_width, image_height, font_size * 4, 0.5)
#     draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)

#     y: float = border * font_size
#     for line in lines:
#         segments: list[str] = line.split('\t')
#         for i, segment in enumerate(segments):
#             if not segment.endswith('\0'):
#                 anchor: str = 'la'
#             else:
#                 anchor = 'ra'
#                 segment: str = segment[:-1]
#             draw.text((border * font_size + tabs[i] * one_space_pixel, y), segment,
#                       'black', font, anchor, *args, **kwargs)
#         y += max_line_height + row_spacing * font_size
#     return image


# def background_image(width: float, height: float, side_pixels: float, alpha: float = 1) -> Image.Image:
#     return Image.new('RGBA', (round(width), round(height)), 'white')


def image_to_bytesio(img: Image.Image, format='PNG') -> BytesIO:
    bytesio = BytesIO()
    img.save(bytesio, format)
    bytesio.seek(0)
    return bytesio
