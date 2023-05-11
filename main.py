import discord
import sqlite3
import json
import os
import logging
import subprocess
import sys

handler = logging.FileHandler(filename="loki.log", encoding="utf-8", mode="w")

# Check if the configuration file exists
if not os.path.isfile("cfg/cfg.json"):
    # If the file doesn't exist, check if the directory exists
    # If not, make the directory
    if not os.path.exists("cfg"):
        os.makedirs("cfg")
    # Ask the user for some configuration variables and
    # dump them into a new config file:
    # - TOKEN has to be set for the bot to be used
    # - guild can be set if the commands should only be synced
    #    to one server; leave None to sync them globally
    # - owner has to be set for certain commands (such as /update) to work
    # - rattimes is for determining between which hours is it appropriate to wake up
    data = {
        "TOKEN": input("Your Discord app's auth token: "),
        "guild": None,
        "owner": int(input("Your own Discord ID: ")),
    }
    with open("cfg/cfg.json", "w+") as confile:
        json.dump(data, confile)

# Read configurations from file and save them into variables
with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)

# Check again if any rows are missing and insert defaults if so
defaults = {
    "rattimes": [11, 4],
    "huomentacooldown": 12,
    "ultrararechance": 1000,
    "rarechance": 100,
    "lotterychannel": None,
    "basicincome": 10,
    "bet": 20,
    "voicechannel": None,
}
changes = False
for key, value in defaults.items():
    if key not in config:
        config.update({key: value})
        changes = True
if changes:
    with open("cfg/cfg.json", "w+") as confile:
        json.dump(config, confile)

token = config["TOKEN"]
if config["guild"] == None:
    gld = None
else:
    gld = discord.Object(id=config["guild"])
owner = config["owner"]
ratstart = config["rattimes"][0]
ratend = config["rattimes"][1]
huomentacooldown = config["huomentacooldown"]
ultrararechance = config["ultrararechance"]
rarechance = config["rarechance"]
basicincome = config["basicincome"]
voicechannel = config["voicechannel"]

# Connect into database or create one if it doesn't already exist
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists("data/files"):
    os.makedirs("data/files")
con = sqlite3.connect("data/database.db")
db = con.cursor()
# Create tables if they don't already exist
db.execute(
    "CREATE TABLE if not exists Requests(id INTEGER PRIMARY KEY, uid INTEGER, message TEXT, date TEXT, type TEXT)"
)
db.execute("CREATE TABLE if not exists Users(id INTEGER PRIMARY KEY, timezone TEXT)")
db.execute(
    "CREATE TABLE if not exists Huomenet(id INTEGER PRIMARY KEY, uid INTEGER, hour INTEGER)"
)
db.execute(
    "CREATE TABLE if not exists HuomentaResponses(id INTEGER PRIMARY KEY, response TEXT UNIQUE, rarity INTEGER, rat INTEGER)"
)
db.execute(
    "CREATE TABLE if not exists HuomentaUserStats(id INTEGER PRIMARY KEY, foundlist TEXT, rarelist TEXT, ultralist TEXT, lastdate TEXT)"
)
db.execute(
    "CREATE TABLE if not exists LotteryPlayers(id INTEGER PRIMARY KEY, credits INTEGER)"
)
db.execute(
    "CREATE TABLE if not exists LotteryBets(id INTEGER PRIMARY KEY, uid INTEGER, roundid INTEGER, row TEXT)"
)
db.execute(
    "CREATE TABLE if not exists LotteryWins(id INTEGER PRIMARY KEY, uid INTEGER, roundid INTEGER, payout INTEGER, date TEXT)"
)
db.execute(
    "CREATE TABLE if not exists CurrentLottery(id INTEGER PRIMARY KEY, pool INTEGER, startdate TEXT)"
)
db.execute(
    "CREATE TABLE if not exists Alcoholist(id INTEGER PRIMARY KEY, weight INTEGER, r REAL, bac REAL)"
)
db.execute(
    "CREATE TABLE if not exists Alarms(id INTEGER PRIMARY KEY, time INTEGER, weekdays TEXT, last TEXT, snooze INTEGER)"
)

# Import additional modules only after the config and database are ready
from slashcommands import huomenta, utils, lottery, drunk, alarms, tools
from responses import messages, voice

# If table HuomentaResponses is empty, populate it
responseamount = db.execute("SELECT COUNT(*) FROM HuomentaResponses").fetchone()[0]
if responseamount == 0:
    with open("slashcommands/huomenta.json", "r", encoding="utf-8") as hfile:
        huomenta.populatehuomenta(db, json.load(hfile))
# Commit changes and close the connection for availability for commands.
con.commit()
con.close()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# Sync command tree
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await tree.sync(guild=gld)
    print("Commands synced")
    from jobs import jobs

    await jobs.startjobs(client)
    print("Tasks started")


@client.event
async def on_message(msg: discord.Message):
    """
    Cannot respond to self or another bot. In any other case, do various thing depending to what was said.
    """
    if msg.author == client.user or msg.author.bot:
        return
    if msg.content.lower() == "huomenta":
        await messages.goodmorning(msg)


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
        or (voicechannel and after.channel and after.channel.id != voicechannel)
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
    if ctx.user.id == owner:
        await ctx.response.send_message("Jyrki ottaa päikkärit", ephemeral=True)
        subprocess.Popen("./update.sh")
        await client.close()
        sys.exit(0)
    else:
        await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)


@tree.command(name="ping", description="Pelaa pöytätennistä Jyrkin kanssa!", guild=gld)
async def ping(ctx: discord.Interaction):
    """Test command for checking bot latency"""
    await ctx.response.send_message(
        f"Pong! {round(client.latency*1000)} ms", ephemeral=True
    )


# Add commands to command tree
tree.add_command(huomenta.Huomenta(client), guild=gld)
tree.add_command(lottery.Lottery(client), guild=gld)
tree.add_command(drunk.Drunk(client), guild=gld)
tree.add_command(utils.Request(client), guild=gld)
tree.add_command(alarms.Alarm(client), guild=gld)
tree.add_command(tools.Tools(client, owner), guild=gld)
tree.add_command(utils.C7ck(client), guild=gld)
tree.add_command(utils.gpmems, guild=gld)
tree.add_command(utils.timezone, guild=gld)

if __name__ == "__main__":
    client.run(token, log_handler=handler)
