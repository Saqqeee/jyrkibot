import discord
import nacl  # DO NOT remove this import, even if it is unused! It is used by Discord for the voice connection.
import os


async def joinchannel(client: discord.Client, channel: discord.VoiceChannel):
    """
    Join voice channel and start playing audio if the audio file exists.

    ffmpeg has to be in the bot's main directory for this to work
    """

    vc = await channel.connect()

    if os.path.isfile("data/files/voicefile.mp3"):
        audio = discord.FFmpegPCMAudio(source="data/files/voicefile.mp3")
        vc.play(audio)


async def leavechannel(client: discord.Client, vc: discord.VoiceClient):
    """
    Stop playing audio and leave the voice channel
    """

    if vc.is_playing():
        vc.stop()

    await vc.disconnect()
