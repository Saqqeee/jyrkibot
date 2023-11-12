import json
import logging

# import asyncio
import os
import subprocess
import sys

import alembic.command
import discord
from alembic.config import Config
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from jobs.database import engine, Base, HuomentaResponses
from jobs.tasks.cache_config import config

handler = logging.FileHandler(filename="loki.log", encoding="utf-8", mode="w")
alembic_cfg = Config("alembic.ini")

# Connect into database or create one if it doesn't already exist
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists("data/files"):
    os.makedirs("data/files")

if not os.path.exists("data/database.db"):
    Base.metadata.create_all(engine)
    alembic.command.stamp(alembic_cfg, "head")

# Run database migrations
alembic.command.upgrade(alembic_cfg, "head")

# Import additional modules only after the config and database are ready
from slashcommands import (
    convert,
    huomenta,
    utils,
    lottery,
    drunk,
    alarms,
    tools,
    wiktionary,
    weather,
)
from responses import messages, voice  # , links
import minigames

# If table HuomentaResponses is empty, populate it
with Session(engine) as db:
    responseamount = db.scalars(
        select(func.count()).select_from(HuomentaResponses)
    ).one()
    if responseamount == 0:
        with open("slashcommands/huomenta.json", "r", encoding="utf-8") as hfile:
            huomenta.populatehuomenta(db, json.load(hfile))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

gld = discord.Object(id=config.guild) if config.guild else None

# Sync command tree
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await tree.sync(guild=gld)
    print("Commands synced")
    from jobs import jobs

    await jobs.startjobs(client)


@client.event
async def on_message(msg: discord.Message):
    if msg.author == client.user or msg.author.bot:
        return
    if msg.content.lower() == "huomenta":
        await messages.goodmorning(msg)
    if msg.content.lower() in ["hyvää yötä", "öitä", "gn", "öt", "kauniita unia"]:
        await messages.goodnight(msg)
    # await links.detracker(msg)


@client.event
async def on_voice_state_update(
    member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
):
    """
    What to do when a member joins or leaves a voice channel
    """

    if (
        member == client.user
        or member.bot
        or (
            config.voicechannel
            and after.channel
            and after.channel.id != config.voicechannel
        )
    ):
        # Do nothing if the event was caused by self or another bot,
        # or someone joins a different channel than which the bot is already on
        return

    if not before.channel and after.channel and not client.voice_clients:
        # If someone connects to voice and the bot doesn't have any voice connections open,
        # connect to that same channel
        await voice.joinchannel(client, after.channel)

    if (
        before.channel
        and client.voice_clients
        and client.voice_clients[0].channel.members == [client.user]
    ):
        # If someone leaves any voice channel and the bot is left alone, leave
        await voice.leavechannel(client, client.voice_clients[0])


# If this command is called by the owner set in cfg.json,
# run a script that syncs the repo with origin and restarts the bot
@tree.command(name="update", description="Owner only command", guild=gld)
async def update(ctx: discord.Interaction):
    """
    If this command is called by the owner set in cfg.json,
    run a script that syncs the repo with origin and restarts the bot
    """
    if ctx.user.id == config.owner:
        await ctx.response.send_message("Jyrki ottaa päikkärit", ephemeral=True)
        subprocess.Popen("./update.sh")
        await client.close()
        sys.exit(0)
    else:
        await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)


@tree.command(name="shutdown", guild=gld)
async def shutdown(ctx: discord.Interaction):
    if ctx.user.id == config.owner:
        await ctx.response.send_message("Jyrki kuolee", ephemeral=True)
        await client.close()
        sys.exit(0)
    else:
        await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)


@tree.command(name="ping", description="Pelaa pöytätennistä Jyrkin kanssa!", guild=gld)
async def ping(ctx: discord.Interaction):
    """Test command for checking bot latency"""
    await ctx.response.send_message(
        f"Pong! {round(client.latency * 1000)} ms", ephemeral=True
    )


# Add commands to command tree
tree.add_command(huomenta.Huomenta(client), guild=gld)
tree.add_command(lottery.Lottery(client), guild=gld)
tree.add_command(drunk.Drunk(client), guild=gld)
tree.add_command(utils.Request(client), guild=gld)
tree.add_command(alarms.Alarm(client), guild=gld)
tree.add_command(tools.Tools(client), guild=gld)
tree.add_command(utils.C7ck(client), guild=gld)
tree.add_command(wiktionary.Wiktionary(client), guild=gld)
tree.add_command(weather.Weather(), guild=gld)
tree.add_command(convert.Convert(), guild=gld)
tree.add_command(minigames.Game(), guild=gld)
tree.add_command(utils.gpmems, guild=gld)
tree.add_command(utils.timezone, guild=gld)
tree.add_command(utils.addtochannel, guild=gld)
tree.add_command(utils.addrole, guild=gld)
tree.add_command(utils.userroledel, guild=gld)

if __name__ == "__main__":
    client.run(config.token, log_handler=handler)
