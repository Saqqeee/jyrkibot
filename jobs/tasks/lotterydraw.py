import discord
from sqlalchemy import select, update
from sqlalchemy.orm import Session
import math
import json
import random
from datetime import datetime, timedelta
from jobs.tasks.cache_config import config
from jobs.database import (
    engine,
    CurrentLottery,
    LotteryBets,
    LotteryWins,
    LotteryPlayers,
)


def calculatewinnings(amount: int):
    return (math.comb(25, amount) - math.comb(25, amount - 1)) / math.comb(25, 7)


async def draw(date: datetime, client: discord.Client):
    if not config.lotterychannel:
        return

    channel = client.get_channel(config.lotterychannel)

    with Session(engine) as db:
        startdate = db.scalar(select(CurrentLottery.startdate))
        if startdate == None:
            db.add(CurrentLottery(pool=0, startdate=date))
            db.commit()
            await channel.send("Uusi lottosessio aloitettu")
            return
        if (date.hour < 17) or (date - startdate < timedelta(hours=12)):
            return

        round, pool = db.execute(select(CurrentLottery.id, CurrentLottery.pool)).one()
        bets = db.execute(
            select(LotteryBets.uid, LotteryBets.row).where(LotteryBets.roundid == round)
        ).all()

        if len(bets) == 0:
            db.execute(update(CurrentLottery).values(startdate=datetime.now()))
            db.commit()
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
                winsum = math.floor(shares[key] / len(value))
                if winsum > 0:
                    db.add(
                        LotteryWins(
                            uid=mies[0], roundid=round, payout=winsum, date=date
                        )
                    )
                    db.execute(
                        update(LotteryPlayers)
                        .where(LotteryPlayers.id == mies[0])
                        .values(credits=LotteryPlayers.credits + winsum)
                    )
                    db.execute(
                        update(CurrentLottery).values(pool=CurrentLottery.pool - winsum)
                    )
                    await client.get_user(mies[0]).send(
                        f"Voitit lotosta **{winsum}** koppelia."
                    )
        db.execute(
            update(CurrentLottery).values(
                id=CurrentLottery.id + 1, startdate=datetime.now()
            )
        )
        newpool = db.scalar(select(CurrentLottery.pool))
        db.commit()

    if len(parhaat) == 0:
        embedtitle = "Ei voittajia tällä kierroksella"
    else:
        embedtitle = f"Kierroksen parhaat rivit (Potti {pool} koppelia)"

    embed = discord.Embed(
        title=embedtitle,
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
