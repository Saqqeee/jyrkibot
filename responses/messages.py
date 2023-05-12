import discord
import sqlite3
import random
import json
import pytz
from datetime import datetime, timedelta
from jobs.tasks.cache_config import config


async def goodmorning(msg: discord.Message):
    """
    Send a good morning message and do some database magic
    """
    # Connect to database and create new user if id is not found, also setting a default time zone
    con = sqlite3.connect("data/database.db")
    db = con.cursor()

    # Insert user id values into tables if they don't exist
    db.execute(
        "INSERT OR IGNORE INTO Users (id, timezone) VALUES (?, ?)",
        [msg.author.id, "Europe/Helsinki"],
    )

    # If user has an entry in HuomentaUserStats and their cooldown has not yet passed, stop execution
    lastdate = db.execute(
        "SELECT lastdate FROM HuomentaUserStats WHERE id=?", [msg.author.id]
    ).fetchone()
    if lastdate != None and datetime.fromisoformat(
        lastdate[0]
    ) > datetime.now() - timedelta(hours=config.huomentacooldown):
        await msg.add_reaction("☕")
        con.commit()
        con.close()
        return

    # Otherwise get the current hour in user's timezone as well as datetime in UTC format
    tz = db.execute(
        "SELECT timezone FROM Users WHERE id=?", [msg.author.id]
    ).fetchone()[0]
    hour = datetime.now(pytz.timezone(tz)).hour
    aika = datetime.now()

    # Check for ultra rares and regular rares
    if random.randint(1, config.ultrararechance) == 1:
        rarity = 2
        rarenotif = ":star:" * 3
        rat = 0
        earn = 50 * config.basicincome
    elif random.randint(1, config.rarechance) == 1:
        rarity = 1
        rarenotif = ":star:"
        earn = 5 * config.basicincome
    else:
        rarity = 0
        rarenotif = ""
        earn = config.basicincome
    # Rat check. Ultra rares override this
    if (hour < config.rattimes[1] or hour >= config.rattimes[0]) and rarity != 2:
        rat = 1
    else:
        rat = 0
        earn = earn * 2

    # Check list of current responses for user
    if rarity == 2:
        userresponses = db.execute(
            "SELECT ultralist FROM HuomentaUserStats WHERE id=?",
            [msg.author.id],
        ).fetchone()
    elif rarity == 1:
        userresponses = db.execute(
            "SELECT rarelist FROM HuomentaUserStats WHERE id=?", [msg.author.id]
        ).fetchone()
    else:
        userresponses = db.execute(
            "SELECT foundlist FROM HuomentaUserStats WHERE id=?",
            [msg.author.id],
        ).fetchone()
    if userresponses[0] != None:
        foundlist = list(json.loads(userresponses[0]))
    else:
        foundlist = []

    # Gather a list of available responses by rarity and ratness and choose one of them randomly,
    # saving the response and its id in separate variables
    responses = db.execute(
        "SELECT id, response FROM HuomentaResponses WHERE rarity=? and rat=?",
        [rarity, rat],
    ).fetchall()
    response = random.choice(responses)
    respid = response[0]
    respmsg = response[1]
    # If response is not yet found by user, add it to the list
    if respid not in foundlist:
        foundlist.append(respid)
        foundlist.sort()
    foundlist = json.dumps(foundlist)

    # Send response and save stuff into databases
    db.execute("INSERT INTO Huomenet (uid, hour) VALUES (?, ?)", [msg.author.id, hour])
    db.execute(
        "INSERT OR IGNORE INTO HuomentaUserStats(id) VALUES (?)",
        [msg.author.id],
    )
    if rarity == 0:
        db.execute(
            "UPDATE HuomentaUserStats SET foundlist=?, lastdate=? WHERE id=?",
            [foundlist, aika, msg.author.id],
        )
    elif rarity == 1:
        db.execute(
            "UPDATE HuomentaUserStats SET rarelist=?, lastdate=? WHERE id=?",
            [foundlist, aika, msg.author.id],
        )
    elif rarity == 2:
        db.execute(
            "UPDATE HuomentaUserStats SET ultralist=?, lastdate=? WHERE id=?",
            [foundlist, aika, msg.author.id],
        )
    db.execute(
        "INSERT OR IGNORE INTO LotteryPlayers(id, credits) VALUES (?, 0)",
        [msg.author.id],
    )
    db.execute(
        "UPDATE LotteryPlayers SET credits=credits+? WHERE id=?",
        [earn, msg.author.id],
    )
    con.commit()
    con.close()
    await msg.channel.send(rarenotif + respmsg + rarenotif)
