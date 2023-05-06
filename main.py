import discord
import sqlite3
import json
import os
import logging
import pytz
import subprocess
import random
import sys
from datetime import datetime, timedelta
handler = logging.FileHandler(filename='loki.log', encoding='utf-8', mode='w')

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
        "owner": int(input("Your own Discord ID: "))
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
        "lotterychannel": None
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

from slashcommands import huomenta, utils, lottery

# Load defaults for populating an empty HuomentaResponses table
with open("slashcommands/huomenta.json", "r", encoding="utf-8") as hfile:
    huomentalist = json.load(hfile)

# Connect into database or create one if it doesn't already exist
if not os.path.exists("data"):
    os.makedirs("data")
con = sqlite3.connect("data/database.db")
db = con.cursor()
# Create tables if they don't already exist
db.execute("CREATE TABLE if not exists Users(id INTEGER PRIMARY KEY, timezone TEXT)")
db.execute("CREATE TABLE if not exists Huomenet(id INTEGER PRIMARY KEY, uid INTEGER, hour INTEGER)")
db.execute("CREATE TABLE if not exists HuomentaResponses(id INTEGER PRIMARY KEY, response TEXT UNIQUE, rarity INTEGER, rat INTEGER)")
db.execute("CREATE TABLE if not exists HuomentaUserStats(id INTEGER PRIMARY KEY, foundlist TEXT, rarelist TEXT, ultralist TEXT, lastdate TEXT)")
db.execute("CREATE TABLE if not exists LotteryPlayers(id INTEGER PRIMARY KEY, credits INTEGER)")
db.execute("CREATE TABLE if not exists LotteryBets(id INTEGER PRIMARY KEY, uid INTEGER, roundid INTEGER, row TEXT)")
db.execute("CREATE TABLE if not exists LotteryWins(id INTEGER PRIMARY KEY, uid INTEGER, roundid INTEGER, payout INTEGER, date TEXT)")
db.execute("CREATE TABLE if not exists CurrentLottery(id INTEGER PRIMARY KEY, pool INTEGER, startdate TEXT)")
# If table HuomentaResponses is empty, populate it
responseamount = db.execute("SELECT COUNT(*) FROM HuomentaResponses").fetchone()[0]
if responseamount == 0:
    huomenta.populatehuomenta(db, huomentalist)
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
    print(f'We have logged in as {client.user}')
    await tree.sync(guild=gld)
    print("Commands synced")
    from jobs import jobs
    await jobs.startjobs(client)
    print("Tasks started")

# Responds with something from the Huomenta list if
# someone wakes up at an unreasonable time. Also
# logs these into a database.
@client.event
async def on_message(msg):
    if msg.author == client.user or msg.author.bot:
        return
    if msg.content.lower() == "huomenta":
        # Connect to database and create new user if id is not found, also setting a default time zone
        con = sqlite3.connect("data/database.db")
        db = con.cursor()

        # Insert user id values into tables if they don't exist
        db.execute("INSERT OR IGNORE INTO Users (id, timezone) VALUES (?, ?)", [msg.author.id, "Europe/Helsinki"])
        # If user has an entry in HuomentaUserStats and their cooldown has not yet passed, stop execution
        lastdate = db.execute("SELECT lastdate FROM HuomentaUserStats WHERE id=?", [msg.author.id]).fetchone()
        if lastdate != None and datetime.fromisoformat(lastdate[0]) > datetime.now() - timedelta(hours=huomentacooldown):
            con.commit()
            con.close()
            return
        # Otherwise get the current hour in user's timezone as well as datetime in UTC format
        tz = db.execute("SELECT timezone FROM Users WHERE id=?", [msg.author.id]).fetchone()[0]
        hour = datetime.now(pytz.timezone(tz)).hour
        aika = datetime.now()
        
        # Check for ultra rares and regular rares
        if random.randint(1,ultrararechance) == 1:
            rarity = 2
            rarenotif = ":star:"*3
            rat = 0
            earn = 50
        elif random.randint(1,rarechance) == 1:
            rarity = 1
            rarenotif = ":star:"
            earn = 5
        else:
            rarity = 0
            rarenotif = ""
            earn = 1
        # Rat check. Ultra rares override this
        if (hour < ratend or hour >= ratstart) and rarity != 2:
            rat = 1
        else:
            rat = 0
            earn = earn*2

        # Check list of current responses for user
        if rarity == 2:
            userresponses = db.execute("SELECT ultralist FROM HuomentaUserStats WHERE id=?", [msg.author.id]).fetchone()
        elif rarity == 1:
            userresponses = db.execute("SELECT rarelist FROM HuomentaUserStats WHERE id=?", [msg.author.id]).fetchone()
        else:
            userresponses = db.execute("SELECT foundlist FROM HuomentaUserStats WHERE id=?", [msg.author.id]).fetchone()
        if userresponses != None:
            foundlist = list(json.loads(userresponses[0]))
        else:
            foundlist = []
        
        # Gather a list of available responses by rarity and ratness and choose one of them randomly,
        # saving the response and its id in separate variables
        responses = db.execute("SELECT id, response FROM HuomentaResponses WHERE rarity=? and rat=?", [rarity, rat]).fetchall()
        response = random.choice(responses)
        respid = response[0]
        respmsg = response[1]
        # If response is not yet found by user, add it to the list
        if respid not in foundlist:
            foundlist.append(respid)
            foundlist.sort()
        foundlist = json.dumps(foundlist)

        # Send response and save stuff into databases
        await msg.channel.send(rarenotif + respmsg + rarenotif)
        db.execute("INSERT INTO Huomenet (uid, hour) VALUES (?, ?)", [msg.author.id, hour])
        db.execute("INSERT OR IGNORE INTO HuomentaUserStats(id) VALUES (?)", [msg.author.id])
        if rarity == 0:
            db.execute("UPDATE HuomentaUserStats SET foundlist=?, lastdate=? WHERE id=?", [foundlist, aika, msg.author.id])
        elif rarity == 1:
            db.execute("UPDATE HuomentaUserStats SET rarelist=?, lastdate=? WHERE id=?", [foundlist, aika, msg.author.id])
        elif rarity == 2:
            db.execute("UPDATE HuomentaUserStats SET ultralist=?, lastdate=? WHERE id=?", [foundlist, aika, msg.author.id])
        db.execute("INSERT OR IGNORE INTO LotteryPlayers(id, credits) VALUES (?, 0)", [msg.author.id])
        db.execute("UPDATE LotteryPlayers SET credits=credits+? WHERE id=?", [earn, msg.author.id])
        con.commit()
        con.close()

# If this command is called by the owner set in cfg.json,
# run a script that syncs the repo with origin and restarts the bot
@tree.command(name = "update", description = "Owner only command", guild=gld)
async def update(ctx):
    if ctx.user.id == owner:
        await ctx.response.send_message("Jyrki ottaa päikkärit", ephemeral=True)
        subprocess.Popen("./update.sh")
        await client.close()
        sys.exit(0)
    else:
        await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)

# Test command for checking latency
# Also acts as a template for future slash commands
@tree.command(name = "ping", description = "Pelaa pöytätennistä Jyrkin kanssa!", guild=gld)
async def ping(ctx):
    await ctx.response.send_message(f"Pong! {round(client.latency*1000)} ms", ephemeral=True)

# Add commands to command tree
tree.add_command(huomenta.Huomenta(client), guild=gld)
tree.add_command(lottery.Lottery(client), guild=gld)
tree.add_command(utils.cock, guild=gld)
tree.add_command(utils.gpmems, guild=gld)
tree.add_command(utils.timezone, guild=gld)

if __name__ == "__main__":
    client.run(token, log_handler=handler)