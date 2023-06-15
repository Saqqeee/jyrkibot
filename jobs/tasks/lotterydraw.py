import discord
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
import math
import json
import random
from datetime import datetime, timedelta
from slashcommands import lottery
from jobs.tasks.cache_config import config
from jobs.database import (
    engine,
    CurrentLottery,
    LotteryBets,
    LotteryWins,
    LotteryPlayers,
)


def calculatewinnings(amount: int):
    return 9 * (10 ** (-8 + amount))


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

        db.execute(
            update(LotteryPlayers)
            .where(LotteryPlayers.credits < config.bet)
            .values(sub=0)
        )

        round, pool = db.execute(select(CurrentLottery.id, CurrentLottery.pool)).one()

        bets = db.execute(
            select(LotteryBets.uid, LotteryBets.row).where(LotteryBets.roundid == round)
        ).all()

        recurring = db.execute(
            select(
                LotteryBets.uid.distinct(),
                LotteryBets.row,
                func.max(LotteryBets.roundid),
            )
            .join(LotteryPlayers, LotteryPlayers.id == LotteryBets.uid)
            .where(LotteryPlayers.sub)
            .group_by(LotteryPlayers.id)
        ).all()

        betids = [_[0] for _ in bets]
        for rec in recurring:
            if rec[0] not in betids:
                bets.append(rec[0:2])
                db.execute(
                    update(LotteryPlayers)
                    .where(LotteryPlayers.id == rec[0])
                    .values(credits=LotteryPlayers.credits - config.bet)
                )

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
                winners[correctamount].append(user[0])
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
        embedtitle = f"Kierroksen voittajat ({pool} koppelia)"

    embed = discord.Embed(
        title=embedtitle,
        color=discord.Color.dark_magenta(),
    )

    order = [7, 6, 5, 4, 3, 2, 1]

    for i in order:
        winmen = []

        for mies in winners[i]:
            member = discord.utils.get(channel.guild.members, id=mies)
            if member:
                winmen.append(member.display_name)

        if not winmen:
            continue

        winbyamt = math.floor(shares[i] / len(winmen))

        embed.add_field(
            name=f"**{i} oikein** | {winbyamt} koppelia",
            value=", ".join(winmen),
            inline=False,
        )

    embed.set_footer(
        text=f"Päivän rivi: {', '.join(str(e) for e in sorted(winrow))}.\nHuomisen potti: {newpool} koppelia"
    )

    await channel.send(
        content="Arvonnat suoritettu! Nähdään huomenna samaan aikaan.",
        embed=embed,
        view=lottery.RerollButton(),
    )
