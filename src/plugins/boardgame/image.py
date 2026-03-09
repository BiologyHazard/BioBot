from io import BytesIO

from nonebot.adapters.onebot.v11 import MessageSegment
from PIL.Image import Image


def image_to_bytesio(image: Image, format="PNG") -> BytesIO:  # noqa: A002
    bytesio = BytesIO()
    image.save(bytesio, format)
    bytesio.seek(0)
    return bytesio


def image_to_message_segment(image: Image, format="PNG") -> MessageSegment:  # noqa: A002
    return MessageSegment.image(image_to_bytesio(image, format))
