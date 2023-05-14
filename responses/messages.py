import discord
import random
import json
import pytz
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jobs.tasks.cache_config import config
from jobs.database import (
    engine,
    Users,
    HuomentaUserStats,
    HuomentaResponses,
    Huomenet,
    LotteryPlayers,
)


async def goodmorning(msg: discord.Message):
    """
    Send a good morning message and do some database magic
    """
    # Connect to database and create new user if id is not found, also setting a default time zone
    # Insert user id values into tables if they don't exist
    with Session(engine) as db:
        userexists = db.scalar(
            select(select(Users).where(Users.id == msg.author.id).exists())
        )
        if not userexists:
            db.add(Users(id=msg.author.id, timezone="Europe/Helsinki"))
        db.commit()

        # While the connection is open, select the last Good Morning and the user's time zone
        lastdate = db.scalar(
            select(HuomentaUserStats.lastdate).where(
                HuomentaUserStats.id == msg.author.id
            )
        )
        tz = db.scalar(select(Users.timezone).where(Users.id == msg.author.id))

    # If user has an entry in HuomentaUserStats and their cooldown has not yet passed, stop execution
    if lastdate != None and lastdate > datetime.now() - timedelta(
        hours=config.huomentacooldown
    ):
        await msg.add_reaction("☕")
        return

    # Otherwise get the current hour in user's timezone as well as datetime in UTC format
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
    with Session(engine) as db:
        if rarity == 2:
            userresponses = db.scalar(
                select(HuomentaUserStats.ultralist).where(
                    HuomentaUserStats.id == msg.author.id
                )
            )
        elif rarity == 1:
            userresponses = db.scalar(
                select(HuomentaUserStats.rarelist).where(
                    HuomentaUserStats.id == msg.author.id
                )
            )
        else:
            userresponses = db.scalar(
                select(HuomentaUserStats.foundlist).where(
                    HuomentaUserStats.id == msg.author.id
                )
            )
        responses = db.execute(
            select(HuomentaResponses.id, HuomentaResponses.response)
            .where(HuomentaResponses.rarity == rarity)
            .where(HuomentaResponses.rat == rat)
        ).all()

    if userresponses != None:
        foundlist = list(json.loads(userresponses))
    else:
        foundlist = []

    # Gather a list of available responses by rarity and ratness and choose one of them randomly,
    # saving the response and its id in separate variables
    response = random.choice(responses)
    respid = response[0]
    respmsg = response[1]
    # If response is not yet found by user, add it to the list
    if respid not in foundlist:
        foundlist.append(respid)
        foundlist.sort()
    foundlist = json.dumps(foundlist)

    # Send response and save stuff into databases
    with Session(engine) as db:
        db.add(Huomenet(uid=msg.author.id, hour=hour))
        ifinhus = db.scalar(select(select(HuomentaUserStats.id).exists()))
        if not ifinhus:
            db.add(HuomentaUserStats(id=msg.author.id))
        if rarity == 0:
            db.execute(
                update(HuomentaUserStats)
                .where(HuomentaUserStats.id == msg.author.id)
                .values(foundlist=foundlist, lastdate=aika)
            )
        elif rarity == 1:
            db.execute(
                update(HuomentaUserStats)
                .where(HuomentaUserStats.id == msg.author.id)
                .values(rarelist=foundlist, lastdate=aika)
            )
        elif rarity == 2:
            db.execute(
                update(HuomentaUserStats)
                .where(HuomentaUserStats.id == msg.author.id)
                .values(ultralist=foundlist, lastdate=aika)
            )
        isinlp = db.scalar(select(select(LotteryPlayers.id).exists()))
        if not isinlp:
            db.add(LotteryPlayers(id=msg.author.id, credits=0))
        else:
            db.execute(
                update(LotteryPlayers)
                .where(LotteryPlayers.id == msg.author.id)
                .values(credits=LotteryPlayers.credits + earn)
            )
        db.commit()
    await msg.channel.send(rarenotif + respmsg + rarenotif)
