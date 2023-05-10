import discord
from discord import app_commands as apc
import json
import os
import asyncio


class Tools(apc.Group):
    def __init__(self, client: discord.Client, owner):
        super().__init__(
            name="tools", description="Owner only tools for managing the bot"
        )
        self.client = client
        self.owner = owner

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.owner

    async def on_error(self, interaction: discord.Interaction, error):
        if isinstance(error, apc.CheckFailure):
            await interaction.response.send_message(error, ephemeral=True)
        else:
            await self.client.on_error(error)

    @apc.command(name="voicechannel")
    async def setvoicechannel(
        self, ctx: discord.Interaction, channel: discord.VoiceChannel = None
    ):
        if not channel:
            with open("cfg/cfg.json", "r") as confile:
                config = json.load(confile)
            config.update({"voicechannel": None})
            with open("cfg/cfg.json", "w") as confile:
                json.dump(config, confile)
            await ctx.response.send_message(
                "Voice channel removed from config. Wait for bot refresh.",
                ephemeral=True,
            )
        else:
            with open("cfg/cfg.json", "r") as confile:
                config = json.load(confile)
            config.update({"voicechannel": channel.id})
            with open("cfg/cfg.json", "w") as confile:
                json.dump(config, confile)
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
        if remove:
            if os.path.isfile("data/files/voicefile.mp3"):
                os.remove("data/files/voicefile.mp3")
            await ctx.response.send_message("Voice file removed", ephemeral=True)
            return

        await ctx.response.defer(ephemeral=True, thinking=True)

        filefound = False
        for i in range(10):
            async for msg in ctx.channel.history(after=ctx.created_at, limit=10):
                if msg.author == ctx.user and msg.attachments:
                    file = msg.attachments[0]
                    filefound = True
                    break

            if filefound:
                break

            await asyncio.sleep(1)

        if not filefound:
            await ctx.followup.send(f"You didn't send a file.")
            return

        if ".mp3" not in file.filename:
            await ctx.followup.send(content="The file must be mp3")
            return

        if file.size > 10000000:
            await ctx.followup.send(content="The file you have sent is way too big")
            return

        if not os.path.exists("data/files"):
            os.makedirs("data/files")
        if os.path.isfile("data/files/voicefile.mp3"):
            os.remove("data/files/voicefile.mp3")

        kb = await file.save("data/files/voicefile.mp3")

        await ctx.followup.send(f"Saved file {file.filename} ({kb//1000} kb written)")
