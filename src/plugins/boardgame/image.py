from io import BytesIO
from PIL.Image import Image
from nonebot.adapters.onebot.v11 import MessageSegment


def image_to_bytesio(image: Image, format='PNG') -> BytesIO:
    bytesio = BytesIO()
    image.save(bytesio, format)
    bytesio.seek(0)
    return bytesio


def image_to_message_segment(image: Image, format='PNG') -> MessageSegment:
    return MessageSegment.image(image_to_bytesio(image, format))
