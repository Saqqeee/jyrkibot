import discord
import json
import os
import logging
import pytz
from datetime import datetime
handler = logging.FileHandler(filename='loki.log', encoding='utf-8', mode='w')

## Check if the configuration file exists
if os.path.isfile("cfg/cfg.json"):
    ## If it does exist, do nothing
    pass
else:
    ## If the file doesn't exist, check if the directory exists
    ## If not, make the directory
    if not os.path.exists("cfg"):
        os.makedirs("cfg")
    ## Ask the user for some configuration variables and
    ## dump them into a new config file:
    ## - TOKEN has to be set for the bot to be used
    ## - guild can be set if the commands should only be synced
    ##    to one server; leave None to sync them globally
    data = {
        "TOKEN": input("Your Discord app's auth token: "),
        "guild": None
    }
    with open("cfg/cfg.json", "w+") as confile:
        json.dump(data, confile)
## Read configurations from file and save them into variables
with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
token = config["TOKEN"]
if config["guild"] == None:
    gld = None
else:
    gld = discord.Object(id=config["guild"])

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

## Sync command tree
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync(guild=gld)
    print("Commands synced")

## Responds with "Go to work regards Jyrki" if
## someone wakes up at an unreasonable time
@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    if msg.content.lower() == "huomenta":
        aika = datetime.now(pytz.timezone('Europe/Helsinki'))
        if aika.hour <= 4 or aika.hour >= 11:
            await msg.channel.send("Mene töihin terv. Jyrki.")

## Test command for checking latency
## Also acts as a template for future slash commands
@tree.command(name = "ping", description = "Ping!", guild=gld)
async def ping(ctx):
    await ctx.response.send_message(f"Pong! {round(client.latency*1000)} ms")

client.run(token, log_handler=handler)