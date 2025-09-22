import io
from pathlib import Path

import aiohttp
from nonebot import logger, on_fullmatch, on_keyword, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageEvent, MessageSegment
from nonebot.params import EventMessage
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule
from PIL import Image

__plugin_meta__ = PluginMetadata(
    name='偷表情',
    description='偷表情',
    usage='偷表情'
)


async def upload_file(bot: Bot, type: str, to: int | str, *args, **kwargs):
    if type == "group":
        return await bot.upload_group_file(group_id=to, *args, **kwargs)
    elif type == "private":
        return await bot.upload_private_file(user_id=to, *args, **kwargs)
    else:
        raise ValueError(f"Unknown upload type: {type}")


async def get_image(bot: Bot, message_segment: MessageSegment) -> MessageSegment:
    if message_segment.type != "image":
        raise ValueError(f"Message segment {message_segment} is not an image")

    data = {"file": message_segment.data["file"], "sub_type": 0, "subType": 0}
    if "url" in message_segment.data:
        data["url"] = message_segment.data["url"]
    if "summary" in message_segment.data:
        data["summary"] = message_segment.data["summary"]

    return MessageSegment(type="image", data=data)


@Rule
def should_steal(event: MessageEvent) -> bool:
    if event.reply is None:
        return False

    for message_segment in event.reply.message:
        if message_segment.type == "image":
            return True

    return False


steal = on_fullmatch(("偷", "偷表情"), rule=should_steal, priority=10, block=False)


@steal.handle()
async def steal_func(bot: Bot, event: MessageEvent) -> None:
    assert event.reply is not None

    message = Message()
    for message_segment in event.reply.message:
        if message_segment.type == "image":
            logger.debug(repr(message_segment))

            file = message_segment.data["file"]
            url = message_segment.data.get("url")

            # try:
            #     get_image_result = await bot.get_image(file=message_segment.data["file"])
            #     logger.debug(f"get_image succeeded, returned {get_image_result}")
            #     file = get_image_result["file"]
            #     url = get_image_result["url"]
            # except Exception as e:
            #     logger.warning(f"get_image_failed, raised {e!r}")

            if url is not None:
                try:
                    async with aiohttp.request("GET", url) as response:
                        response.raise_for_status()

                        logger.debug(f"Successfully downloaded image: {response}")

                        file = await response.read()
                        with open(f"data/steal/images/{message_segment.data["file"]}", "wb") as f:
                            f.write(file)
                        file = Path(f"data/steal/images/{message_segment.data["file"]}").resolve().as_posix()

                        # output = io.BytesIO()
                        # Image.open(io.BytesIO(file)).convert("RGBA").save(output, format="PNG")
                        # file = output.getvalue()

                        try:
                            await upload_file(bot,
                                              event.message_type, getattr(event, "group_id", event.user_id),
                                              file=file,
                                              name=message_segment.data["file"])
                        except Exception as e:
                            logger.warning(f"Failed to upload image: {e!r}")

                except Exception as e:
                    logger.warning(f"Failed to download image: {e!r}")
                    file = url
            else:
                logger.warning(f"No URL found in image message segment ({message_segment}).")
                file = message_segment.data["file"]

            message.append(MessageSegment(type="image", data={"file": file}))

    await steal.finish(message)
