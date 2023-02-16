import base64
from io import BytesIO
from PIL.Image import Image
from nonebot.adapters.onebot.v11 import Message, MessageSegment


def image_to_base64(image: Image, format='PNG'):
    output_buffer = BytesIO()
    image.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data)
    return base64_str


def image_to_message_segment(image: Image, format='PNG'):
    return MessageSegment.image(f"base64://{str(image_to_base64(image), encoding='utf-8')}")
