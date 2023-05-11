import discord
from discord import app_commands as apc
import sqlite3
import random
from datetime import datetime
from jobs.tasks.cache_config import config


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
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    db.execute(
        "INSERT OR IGNORE INTO Users (id, timezone) VALUES (?, ?)",
        [ctx.user.id, timezones.value],
    )
    db.execute(
        "UPDATE Users SET timezone = ? WHERE id = ?", [timezones.value, ctx.user.id]
    )
    con.commit()
    con.close()
    await ctx.response.send_message(
        f"{ctx.user.mention}: Aikavyöhykkeeksi vaihdettu {timezones.name}.",
        ephemeral=True,
    )


class C7ck(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="length")
    async def cock(self, ctx: discord.Interaction, user: discord.Member = None):
        random.seed(ctx.user.id if not user else user.id)
        cocklength = f"{round(random.gauss(15,10),2)}"
        if user == None or user == ctx.user:
            await ctx.response.send_message(f"Munasi on {cocklength} cm pitkä.")
        else:
            await ctx.response.send_message(
                f"Käyttäjän {user.display_name} muna on {cocklength} cm pitkä."
            )

    @apc.command(name="balls")
    async def balls(self, ctx: discord.Interaction, user: discord.Member = None):
        random.seed(ctx.user.id if not user else user.id)
        ballweight = f"{round(abs(random.gauss(48,100)),1)}"
        if user == None or user == ctx.user:
            await ctx.response.send_message(f"Pallisi painavat {ballweight} kg.")
        else:
            await ctx.response.send_message(
                f"Käyttäjän {user.display_name} pallit painavat {ballweight} kg."
            )


class Request(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="add", description="Pyydä toimintoa")
    async def requestadd(self, ctx: discord.Interaction, msg: apc.Range[str, 1, 100]):
        date = datetime.now()
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        req = db.execute(
            "INSERT INTO Requests(uid, message, date, type) VALUES(?, ?, ?, 'new')",
            [ctx.user.id, msg, date],
        )
        con.commit()
        con.close()
        await ctx.response.send_message(f"Lisätty pyyntö `{req.lastrowid}`:\n> {msg}")

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
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        if not type:
            frlist = db.execute(
                "SELECT id, uid, message, date, type FROM Requests"
            ).fetchall()
        else:
            frlist = db.execute(
                "SELECT id, uid, message, date, type FROM Requests WHERE type=?",
                [type.value],
            ).fetchall()
        con.close()
        embed = discord.Embed(
            title="Pyydetyt ominaisuudet", color=discord.Color.dark_magenta()
        )
        for req in frlist:
            date = datetime.fromisoformat(req[3])
            embed.add_field(
                name=f"**{req[0]}**, **{discord.utils.get(ctx.guild.members, id=req[1]).display_name}**: {date.strftime('%d.%m.%Y')} ({req[4]})",
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
            con = sqlite3.connect("data/database.db")
            db = con.cursor()
            check = db.execute("SELECT * FROM Requests WHERE id=?", [id]).fetchone()
            if not check:
                await ctx.response.send_message(
                    "Ei ole tuollaista id:tä.", ephemeral=True
                )
                return
            db.execute("UPDATE Requests SET type=? WHERE id=?", [type.value, id])
            con.commit()
            con.close()
            await ctx.response.send_message(
                f"Updated request `{id}` to type {type.name}."
            )
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)
