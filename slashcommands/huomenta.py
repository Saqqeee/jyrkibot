import discord
import json
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from discord import app_commands as apc
from jobs.tasks.cache_config import config
from jobs.database import engine, HuomentaResponses, Huomenet, HuomentaUserStats, Users


# This is used by the main program for populating the HuomentaResponses table
def populatehuomenta(db: Session, huomentalist: dict):
    data = []
    for x in huomentalist["normalgood"]:
        data.append(HuomentaResponses(response=x, rarity=0, rat=0))
    for x in huomentalist["normalbad"]:
        data.append(HuomentaResponses(response=x, rarity=0, rat=1))
    for x in huomentalist["raregood"]:
        data.append(HuomentaResponses(response=x, rarity=1, rat=0))
    for x in huomentalist["rarebad"]:
        data.append(HuomentaResponses(response=x, rarity=1, rat=1))
    for x in huomentalist["ultrarare"]:
        data.append(HuomentaResponses(response=x, rarity=2, rat=0))
    db.add_all(data)
    db.commit()


class Huomenta(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="stats", description="Näytä omat tai jonkun muun huomenet.")
    @apc.choices(hidden=[apc.Choice(name="False", value=1)])
    async def stats(
        self,
        ctx: discord.Interaction,
        user: discord.Member = None,
        hidden: apc.Choice[int] = None,
    ):
        if user == None:
            user = ctx.user
        embed = discord.Embed(
            title=f"Huomenta-tilastot käyttäjälle {user.display_name}:",
            color=discord.Color.dark_magenta(),
        )

        hidden = False if hidden != None else True

        # Fetch information from database for formatting the response
        with Session(engine) as db:
            userexists = db.scalar(
                select(select(Users).where(Users.id == user.id).exists())
            )
            if not userexists:
                await ctx.response.send_message("Käyttäjää ei löydetty", ephemeral=True)
                return

            times = db.scalar(
                select(func.count())
                .select_from(Huomenet)
                .where(Huomenet.uid == user.id)
            )

            rats = db.scalar(
                select(func.count())
                .select_from(Huomenet)
                .where(Huomenet.uid == user.id)
                .filter(
                    (Huomenet.hour >= config.rattimes[0])
                    | (Huomenet.hour < config.rattimes[1])
                )
            )

            userresponses = db.execute(
                select(
                    HuomentaUserStats.foundlist,
                    HuomentaUserStats.rarelist,
                    HuomentaUserStats.ultralist,
                ).where(HuomentaUserStats.id == user.id)
            ).one()

            morosfound = (
                len(list(json.loads(userresponses[0])))
                if userresponses[0] is not None
                else 0
            )
            raresfound = (
                len(list(json.loads(userresponses[1])))
                if userresponses[1] is not None
                else 0
            )
            ultrasfound = (
                len(list(json.loads(userresponses[2])))
                if userresponses[2] is not None
                else 0
            )

            morototal = db.scalar(
                select(func.count())
                .select_from(HuomentaResponses)
                .where(HuomentaResponses.rarity == 0)
            )
            raretotal = db.scalar(
                select(func.count())
                .select_from(HuomentaResponses)
                .where(HuomentaResponses.rarity == 1)
            )
            ultratotal = db.scalar(
                select(func.count())
                .select_from(HuomentaResponses)
                .where(HuomentaResponses.rarity == 2)
            )

        huomentastats = f"Tavallisia huomenia {morosfound}/{morototal}\nHarvinaisia huomenia {raresfound}/{raretotal}\nULTRA-harvinaisia huomenia {ultrasfound}/{ultratotal}"

        if times == 1:
            kerrat = f"kerran"
        elif times > 1:
            kerrat = f"{times} kertaa"
        if times == None or times < 1:
            embed.add_field(
                name="Herätykset",
                value=f"{user.display_name} ei ole koskaan herännyt.",
                inline=False,
            )
        elif rats == None or rats < 1:
            embed.add_field(
                name="Herätykset",
                value=f"Herätty {kerrat} ja aina ihmisten aikoihin!",
                inline=False,
            )
        else:
            embed.add_field(
                name="Herätykset",
                value=f"Herätty {kerrat}, joista {rats} täysin rottamaiseen aikaan!",
                inline=False,
            )
        embed.add_field(name="Jyrkin vastaukset", value=huomentastats, inline=False)
        embed.set_thumbnail(url=user.display_avatar)
        await ctx.response.send_message(embed=embed, ephemeral=hidden)

    @apc.command(name="leaderboard", description="Kuka on herännyt eniten!")
    async def leaderboard(self, ctx: discord.Interaction):
        with Session(engine) as db:
            selection = (
                select(Huomenet.uid, func.count(Huomenet.hour))
                .group_by(Huomenet.uid)
                .order_by(func.count(Huomenet.hour).desc())
            )
            leaders = db.execute(selection.limit(5)).fetchall()
        if len(leaders) == 0:
            await ctx.response.send_message("Kukaan täällä ei ole herännyt.")
            return
        embed = discord.Embed(
            title="Top 5 herääjät:", color=discord.Color.dark_magenta()
        )
        i = 0
        for leader in leaders:
            i += 1
            member = discord.utils.get(ctx.guild.members, id=leader[0])
            embed.add_field(
                name=f"**{i}.** {member.display_name}",
                value=f"Herätyksiä {leader[1]}",
                inline=False,
            )
        await ctx.response.send_message(embed=embed)

    @apc.command(name="add", description="Owner only command")
    @apc.choices(
        rarity=[
            apc.Choice(name="Normal", value=0),
            apc.Choice(name="Rare", value=1),
            apc.Choice(name="Ultra rare", value=2),
        ],
        ratness=[apc.Choice(name="Lammas", value=0), apc.Choice(name="Rotta", value=1)],
    )
    async def addresponse(
        self,
        ctx: discord.Interaction,
        response: str,
        rarity: apc.Choice[int],
        ratness: apc.Choice[int],
    ):
        if ctx.user.id == config.owner:
            if rarity.value == 2:
                ratness.value = 0
            with Session(engine) as db:
                insert = HuomentaResponses(
                    response=response, rarity=rarity.value, rat=ratness.value
                )
                db.add(insert)
                db.commit()
            await ctx.response.send_message("Vastaus lisätty!", ephemeral=True)
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)
