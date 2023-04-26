import discord
from discord.ext import commands
import json
import sqlite3
from discord import app_commands as apc

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
owner = config["owner"]
rattimes = config["rattimes"]

class Huomenta(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name = "huomenta", description = "Huomenta.")
    async def huomenta(self, ctx):
        await ctx.response.send_message("Huomenta.")

    @apc.command(name = "stats", description = "Näytä omat tai jonkun muun huomenet.")
    async def stats(self, ctx, user: discord.Member = None):
        if user == None:
            user = ctx.user
            alku = "Olet"
        else: alku = f"{user.mention} on"
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        times = db.execute("SELECT COUNT(*) FROM Huomenet WHERE uid = ?", [user.id]).fetchone()
        rats = db.execute("SELECT COUNT(*) FROM Huomenet WHERE uid = ? GROUP BY uid HAVING hour >= ? OR hour <= ?", [user.id, rattimes[0], rattimes[1]]).fetchone()
        if times[0] == 1:
            kerrat = f"kerran"
        else:
            kerrat = f"{times[0]} kertaa"
        if times == None or times[0] < 1:
            await ctx.response.send_message(f"{user.mention} ei ole ikinä herännyt.")
        elif rats == None or rats[0] < 1:
            await ctx.response.send_message(f"{alku} herännyt {kerrat}, ja aina ihmisten aikoihin.")
        else:
            await ctx.response.send_message(f"{alku} herännyt {kerrat}, joista {rats[0]} on mennyt rottailuksi.")
        con.close()