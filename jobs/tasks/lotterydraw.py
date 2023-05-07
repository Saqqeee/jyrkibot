import discord
import sqlite3
import math
import json
import random
from datetime import datetime, timedelta

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
lotterychannel = config["lotterychannel"]


def calculatewinnings(amount: int):
    return (math.comb(25, amount) - math.comb(25, amount - 1)) / math.comb(25, 7)


async def draw(date: datetime, client: discord.Client):
    channel = client.get_channel(lotterychannel)
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    startdate = db.execute("SELECT startdate FROM CurrentLottery").fetchone()
    if startdate == None:
        db.execute("INSERT INTO CurrentLottery(pool, startdate) VALUES (0, ?)", [date])
        await channel.send("Uusi lottosessio aloitettu")
        con.commit()
        con.close()
        return
    if (date.hour < 17) or (
        date < datetime.fromisoformat(startdate[0]) + timedelta(hours=12)
    ):
        con.close()
        return
    round, pool = db.execute("SELECT id, pool FROM CurrentLottery").fetchone()
    bets = db.execute(
        "SELECT uid, row FROM LotteryBets WHERE roundid = ?", [round]
    ).fetchall()
    if len(bets) == 0:
        db.execute("UPDATE CurrentLottery SET startdate=?", [datetime.now()])
        con.close()
        return
    winrow = random.sample([*range(1, 25)], k=7)
    winners = {
        1: [],
        2: [],
        3: [],
        4: [],
        5: [],
        6: [],
        7: [],
    }

    shares = [0]
    parhaat = []
    for user in bets:
        correctamount = 0
        for x in json.loads(user[1]):
            if int(x) in winrow:
                correctamount += 1
        if correctamount > 0:
            winners[correctamount].append([user[0]])
            parhaat.append([user[0], correctamount])
    for key, value in winners.items():
        shares.append(math.floor(calculatewinnings(key) * pool))
        for mies in value:
            db.execute(
                "INSERT INTO LotteryWins(uid, roundid, payout, date) VALUES (?,?,?,?)",
                [mies[0], round, math.floor(shares[key] / len(value)), date],
            )
            db.execute(
                "UPDATE LotteryPlayers SET credits = credits + ? WHERE id = ?",
                [math.floor(shares[key] / len(value)), mies[0]],
            )
            db.execute(
                "UPDATE CurrentLottery SET pool=pool-?",
                [math.floor(shares[key] / len(value))],
            )
    db.execute("UPDATE CurrentLottery SET id=id+1, startdate=?", [datetime.now()])
    newpool = db.execute("SELECT pool FROM CurrentLottery").fetchone()[0]
    con.commit()
    con.close()

    embed = discord.Embed(
        title=f"Kierroksen voittajat (Potti {pool} koppelia)",
        color=discord.Color.dark_magenta(),
    )

    def sortink(e):
        return e[1]

    parhaat.sort(reverse=True, key=sortink)
    i = 0
    for mies in parhaat:
        i += 1
        if i > 5:
            break
        member = discord.utils.get(channel.guild.members, id=mies[0])
        embed.add_field(
            name=f"**{i}.** {member.display_name}",
            value=f"{mies[1]} oikein",
            inline=False,
        )

    embed.set_footer(
        text=f"Päivän rivi: {', '.join(str(e) for e in sorted(winrow))}.\nHuomisen potti: {newpool} koppelia"
    )

    await channel.send(
        content="Arvonnat suoritettu! Nähdään huomenna samaan aikaan.", embed=embed
    )
