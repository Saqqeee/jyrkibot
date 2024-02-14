import discord
from discord import app_commands as apc

from minigames.rps import Rps


class Game(apc.Group):
    def __init__(self):
        super().__init__()

    @apc.command(name="rps", description="Rock, Paper, Scissors")
    async def rps(self, ctx: discord.Interaction):
        rps_instance = Rps(ctx)
        await rps_instance.command()
