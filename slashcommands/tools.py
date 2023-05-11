import discord
from discord import app_commands as apc
import os
import asyncio
from jobs.tasks.cache_config import config


class Tools(apc.Group):
    """
    An application command group for owner/developer only commands.

    All commands in this class check the interaction and if the user is not the owner, an error message is sent.
    """

    def __init__(self, client: discord.Client):
        super().__init__(
            name="tools", description="Owner only tools for managing the bot"
        )
        self.client = client

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == config.owner

    async def on_error(self, interaction: discord.Interaction, error):
        if isinstance(error, apc.CheckFailure):
            await interaction.response.send_message(error, ephemeral=True)
        else:
            await self.client.on_error(error)

    @apc.command(name="voicechannel")
    async def setvoicechannel(
        self, ctx: discord.Interaction, channel: discord.VoiceChannel = None
    ):
        """
        Set a voice channel that the bot can join. If it is None, the bot can join all channels.
        """

        if not channel:
            # Replace set voice channel with null
            config.updateconfig("voicechannel", None)

            await ctx.response.send_message(
                "Voice channel removed from config.",
                ephemeral=True,
            )
        else:
            # Replace set voice channel with new voice channel
            config.updateconfig("voicechannel", channel.id)

            await ctx.response.send_message(
                f"Voice channel set to {channel.mention}.",
                ephemeral=True,
            )

    @apc.command(name="voicefile")
    async def setvoicefile(
        self,
        ctx: discord.Interaction,
        remove: bool = False,
    ):
        """
        Set a file for playback when the bot joins a voice channel

        If "remove" is set to True, checks if the voice file exists and removes it.
        If it is False, waits for 10 seconds for an mp3 file and saves it if a set of criteria are met.
        """

        if remove:
            if os.path.isfile("data/files/voicefile.mp3"):
                os.remove("data/files/voicefile.mp3")
            await ctx.response.send_message("Voice file removed", ephemeral=True)
            return

        # Send a thinking... message
        await ctx.response.defer(ephemeral=True, thinking=True)

        # Loop for 10 seconds, looking for an attachment in any follow-up messages
        filefound = False
        for i in range(10):
            async for msg in ctx.channel.history(after=ctx.created_at, limit=10):
                # Break both loops if an attachment is found
                # and it is sent by whoever caused the original interaction
                # (if this is not the owner, something is wrong)
                if msg.author == ctx.user and msg.attachments:
                    file = msg.attachments[0]
                    filefound = True
                    break

            if filefound:
                break

            await asyncio.sleep(1)

        # If the loop runs out and no files are sent,
        # give feedback and return
        if not filefound:
            await ctx.followup.send(f"You didn't send a file.")
            return

        # Do not accept anything but mp3 files
        if ".mp3" not in file.filename:
            await ctx.followup.send(content="The file must be mp3")
            return

        # Do not accept files that are over 8 MB
        if file.size > 8000000:
            await ctx.followup.send(content="The file you have sent is way too big")
            return

        # Check if the save folder exists and
        # delete a possible previous audio file
        if not os.path.exists("data/files"):
            os.makedirs("data/files")
        if os.path.isfile("data/files/voicefile.mp3"):
            os.remove("data/files/voicefile.mp3")

        # Save the new audio file and send a response
        kb = await file.save("data/files/voicefile.mp3")
        await ctx.followup.send(f"Saved file {file.filename} ({kb//1000} kb written)")
