import discord
import sqlite3
import json
import os
import logging
import pytz
from slashcommands import huomenta
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
        "guild": None,
        "owner": input("Your own Discord ID: "),
        "rattimes": [4, 11]
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
owner = config["owner"]
rattimes = config["rattimes"]

## Connect into database or create one if it doesn't already exist
con = sqlite3.connect("data/database.db")
db = con.cursor()
## Create tables if they don't already exist
db.execute("CREATE TABLE if not exists Huomenet(id INTEGER PRIMARY KEY, uid INTEGER, hour INTEGER)")
## Commit changes and close the connection for availability for commands.
con.commit()
con.close()

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

## Function for logging Huomenta-calls into the database
def ratlog(author, time):
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    db.execute("INSERT INTO Huomenet (uid, hour) VALUES (?, ?)", [author, time])
    con.commit()
    con.close()

## Responds with "Go to work regards Jyrki" if
## someone wakes up at an unreasonable time. Also
## logs these into a database.
@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    if msg.content.lower() == "huomenta":
        ratstart = rattimes[0]
        ratend = rattimes[1]
        aika = datetime.now(pytz.timezone('Europe/Helsinki'))
        if aika.hour <= ratend or aika.hour >= ratstart:
            await msg.channel.send("Mene töihin terv. Jyrki.")
        ratlog(msg.author.id, aika.hour)

## Test command for checking latency
## Also acts as a template for future slash commands
@tree.command(name = "ping", description = "Ping!", guild=gld)
async def ping(ctx):
    await ctx.response.send_message(f"Pong! {round(client.latency*1000)} ms")

## Add commands to command tree
tree.add_command(huomenta.Huomenta(client), guild=gld)

if __name__ == "__main__":
    client.run(token, log_handler=handler)