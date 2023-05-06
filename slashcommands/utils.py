import discord
from discord import app_commands as apc
import json
import sqlite3
import random

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
owner = config["owner"]

@apc.command(name = "roleinfo", description = "Näytä roolin tiedot")
async def gpmems(ctx, role: discord.Role):
    members = ", ".join(x.display_name for x in role.members)
    embed = discord.Embed(
        color = role.color,
        title = role.name
    )
    embed.add_field(name="Jäsenet", value=members)
    await ctx.response.send_message(embed=embed)

# This allows an user to set their preferred time zone
@apc.command(name = "timezone", description = "Muuta toiselle aikavyöhykkeelle")
@discord.app_commands.choices(timezones=[
    discord.app_commands.Choice(name="Helsinki", value="Europe/Helsinki"),
    discord.app_commands.Choice(name="Tukholma", value="Europe/Stockholm"),
    discord.app_commands.Choice(name="Lontoo", value="Europe/London"),
    discord.app_commands.Choice(name="Tokio", value="Asia/Tokyo"),
    discord.app_commands.Choice(name="UTC", value="Etc/UTC")
])
async def timezone(ctx, timezones: discord.app_commands.Choice[str]):
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    db.execute("INSERT OR IGNORE INTO Users (id, timezone) VALUES (?, ?)", [ctx.user.id, timezones.value])
    db.execute("UPDATE Users SET timezone = ? WHERE id = ?", [timezones.value, ctx.user.id])
    await ctx.response.send_message(f"{ctx.user.mention}: Aikavyöhykkeeksi vaihdettu {timezones.name}.", ephemeral=True)
    con.commit()
    con.close()

@apc.command(name = "c7ck")
async def cock(ctx, user: discord.Member = None):
    random.seed(ctx.user.id if not user else user.id)
    cocklength = f"{round(random.uniform(1,30),1)}"
    if user == None or user == ctx.user:
        await ctx.response.send_message(f"Munasi on {cocklength} cm pitkä.")
    else:
        await ctx.response.send_message(f"Käyttäjän {user.display_name} muna on {cocklength} cm pitkä.")