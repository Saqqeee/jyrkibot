import discord
from discord import app_commands as apc
from sqlalchemy import select, update
from sqlalchemy.orm import Session
import random
from datetime import datetime
from jobs.tasks.cache_config import config
from jobs.database import engine, Users, Requests


@apc.command(name="roleinfo", description="Näytä roolin tiedot")
async def gpmems(ctx: discord.Interaction, role: discord.Role):
    members = ", ".join(x.display_name for x in role.members)
    embed = discord.Embed(color=role.color, title=role.name)
    embed.add_field(name="Jäsenet", value=members)
    await ctx.response.send_message(embed=embed)


# This allows an user to set their preferred time zone
@apc.command(name="timezone", description="Muuta toiselle aikavyöhykkeelle")
@discord.app_commands.choices(
    timezones=[
        discord.app_commands.Choice(name="Helsinki", value="Europe/Helsinki"),
        discord.app_commands.Choice(name="Tukholma", value="Europe/Stockholm"),
        discord.app_commands.Choice(name="Lontoo", value="Europe/London"),
        discord.app_commands.Choice(name="Tokio", value="Asia/Tokyo"),
        discord.app_commands.Choice(name="UTC", value="Etc/UTC"),
    ]
)
async def timezone(
    ctx: discord.Interaction, timezones: discord.app_commands.Choice[str]
):
    with Session(engine) as db:
        userexists = db.scalar(
            select(select(Users).where(Users.id == ctx.user.id).exists())
        )
        if not userexists:
            db.add(Users(id=ctx.user.id, timezone=timezones.value))
        else:
            db.execute(
                update(Users)
                .where(Users.id == ctx.user.id)
                .values(timezone=timezones.value)
            )
        db.commit()
    await ctx.response.send_message(
        f"{ctx.user.mention}: Aikavyöhykkeeksi vaihdettu {timezones.name}.",
        ephemeral=True,
    )


class C7ck(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="length")
    async def cock(
        self, ctx: discord.Interaction, user: discord.Member = None, custom: str = None
    ):
        random.seed(custom or ctx.user.id if not user else user.id)
        cocklength = f"{round(random.gauss(15,3),2)}"

        if custom:
            await ctx.response.send_message(
                f"Henkilön {custom.title()} muna on {cocklength} cm pitkä."
            )
        elif user == None or user == ctx.user:
            await ctx.response.send_message(f"Munasi on {cocklength} cm pitkä.")
        else:
            await ctx.response.send_message(
                f"Käyttäjän {user.display_name} muna on {cocklength} cm pitkä."
            )

    @apc.command(name="balls")
    async def balls(
        self, ctx: discord.Interaction, user: discord.Member = None, custom: str = None
    ):
        random.seed(custom or ctx.user.id if not user else user.id)
        ballweight = f"{round(abs(random.gauss(35,50)),1)}"

        if custom:
            await ctx.response.send_message(
                f"Henkilön {custom.title()} pallit painavat {ballweight} g."
            )
        elif user == None or user == ctx.user:
            await ctx.response.send_message(f"Pallisi painavat {ballweight} g.")
        else:
            await ctx.response.send_message(
                f"Käyttäjän {user.display_name} pallit painavat {ballweight} g."
            )


class Request(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="add", description="Pyydä toimintoa")
    async def requestadd(self, ctx: discord.Interaction, msg: apc.Range[str, 1, 100]):
        date = datetime.now()
        with Session(engine) as db:
            db.add(Requests(uid=ctx.user.id, message=msg, date=date, type="new"))
            reqid = db.scalar(select(Requests.id).order_by(Requests.id.desc()).limit(1))
            db.commit()
        await ctx.response.send_message(f"Lisätty pyyntö `{reqid}`:\n> {msg}")

    @apc.command(name="list", description="Näytä kaikki pyynnöt")
    @apc.choices(
        type=[
            apc.Choice(name="Uusi", value="new"),
            apc.Choice(name="Hylätty", value="declined"),
            apc.Choice(name="Työn alla", value="indev"),
            apc.Choice(name="Tehty", value="done"),
        ]
    )
    async def requestlist(self, ctx: discord.Interaction, type: apc.Choice[str] = None):
        embed = discord.Embed(
            title="Pyydetyt ominaisuudet", color=discord.Color.dark_magenta()
        )
        with Session(engine) as db:
            if not type:
                frlist = select(
                    Requests.id,
                    Requests.uid,
                    Requests.message,
                    Requests.date,
                    Requests.type,
                )
            else:
                frlist = select(
                    Requests.id,
                    Requests.uid,
                    Requests.message,
                    Requests.date,
                    Requests.type,
                ).where(Requests.type == type.value)
            for req in db.execute(frlist).fetchall():
                print(req)
                embed.add_field(
                    name=f"**{req[0]}**, **{discord.utils.get(ctx.guild.members, id=req[1]).display_name}**: {req[3]} ({req[4]})",
                    value=req[2],
                    inline=False,
                )
        await ctx.response.send_message(embed=embed, ephemeral=True)

    @apc.command(name="update", description="Owner only command")
    @apc.choices(
        type=[
            apc.Choice(name="Uusi", value="new"),
            apc.Choice(name="Hylätty", value="declined"),
            apc.Choice(name="Työn alla", value="indev"),
            apc.Choice(name="Tehty", value="done"),
        ]
    )
    async def updaterequest(
        self, ctx: discord.Interaction, id: int, type: apc.Choice[str]
    ):
        if ctx.user.id == config.owner:
            with Session(engine) as db:
                db.execute(
                    update(Requests).where(Requests.id == id).values(type=type.value)
                )
                db.commit()
            await ctx.response.send_message(
                f"Updated request `{id}` to type {type.name}."
            )
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)
