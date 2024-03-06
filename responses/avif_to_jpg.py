import io

import discord
import pillow_avif  # Required as an import for Pillow to know how to process AVIF files
from PIL import Image


async def convert(image_wrapped: io.BytesIO):
    converted = io.BytesIO()
    with Image.open(image_wrapped) as image:
        image.save(converted, format="jpeg", quality=95)
    return converted


async def avif_to_jpg(msg: discord.Message):
    jpg_files: list[discord.File] = []

    for attachment in msg.attachments:
        if attachment.filename.lower().endswith(".avif"):
            image: bytes = await attachment.read()
            image_wrapped = io.BytesIO(image)

            image_converted: io.BytesIO = await convert(image_wrapped)
            image_converted.seek(0)

            image_sendable = discord.File(image_converted, filename="untitled.jpg")
            jpg_files.append(image_sendable)

            image_converted.close()

    if not jpg_files:
        return

    response: str = f"Image{'s' if len(jpg_files) > 1 else ''} by {msg.author.mention}:"

    await msg.channel.send(content=response, files=jpg_files)
