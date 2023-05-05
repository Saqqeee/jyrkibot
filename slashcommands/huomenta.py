import discord
import json
import sqlite3
from discord import app_commands as apc

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
owner = config["owner"]
rattimes = config["rattimes"]

# This is used by the main program for populating the HuomentaResponses table
def populatehuomenta(db: sqlite3.Cursor, huomentalist: dict):
    data = []
    for x in huomentalist["normalgood"]:
        data.append((x, 0, 0))
    for x in huomentalist["normalbad"]:
        data.append((x, 0, 1))
    for x in huomentalist["raregood"]:
        data.append((x, 1, 0))
    for x in huomentalist["rarebad"]:
        data.append((x, 1, 1))
    for x in huomentalist["ultrarare"]:
        data.append((x, 2, 0))
    db.executemany("INSERT INTO HuomentaResponses(response, rarity, rat) VALUES (?, ?, ?)", data)

class Huomenta(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name = "stats", description = "Näytä omat tai jonkun muun huomenet.")
    @apc.choices(hidden=[
        apc.Choice(name="True", value=1)
    ])
    async def stats(self, ctx, user: discord.Member = None, hidden: apc.Choice[int] = None):
        if user == None:
            user = ctx.user
        embed = discord.Embed(
            title=f"Huomenta-tilastot käyttäjälle {user.display_name}:",
            color=discord.Color.dark_magenta()
        )

        hidden = True if hidden != None else False

        # Fetch information from database for formatting the response
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        userexists = db.execute("SELECT EXISTS(SELECT * FROM Users WHERE id=?)", [user.id]).fetchone()[0]
        if not userexists:
            await ctx.response.send_message("Käyttäjää ei löydetty", ephemeral=True)
            con.close()
            return
        times = db.execute("SELECT COUNT(*) FROM Huomenet WHERE uid = ?", [user.id]).fetchone()
        rats = db.execute("SELECT COUNT(hour) FROM Huomenet WHERE uid = ? AND (hour >= ? OR hour < ?)", [user.id, rattimes[0], rattimes[1]]).fetchone()
        userresponses = db.execute("SELECT foundlist, rarelist, ultralist FROM HuomentaUserStats WHERE id=?", [user.id]).fetchone()
        morosfound = len(list(json.loads(userresponses[0]))) if userresponses[0] is not None else 0
        raresfound = len(list(json.loads(userresponses[1]))) if userresponses[1] is not None else 0
        ultrasfound = len(list(json.loads(userresponses[2]))) if userresponses[2] is not None else 0
        morototal = db.execute("SELECT COUNT(*) FROM HuomentaResponses WHERE rarity=0").fetchone()[0]
        raretotal = db.execute("SELECT COUNT(*) FROM HuomentaResponses WHERE rarity=1").fetchone()[0]
        ultratotal = db.execute("SELECT COUNT(*) FROM HuomentaResponses WHERE rarity=2").fetchone()[0]

        huomentastats = f"Tavallisia huomenia {morosfound}/{morototal}\nHarvinaisia huomenia {raresfound}/{raretotal}\nULTRA-harvinaisia huomenia {ultrasfound}/{ultratotal}"

        if times[0] == 1:
            kerrat = f"kerran"
        elif times[0] > 1:
            kerrat = f"{times[0]} kertaa"
        if times == None or times[0] < 1:
            embed.add_field(name="Herätykset", value=f"{user.name} ei ole koskaan herännyt.", inline=False)
        elif rats == None or rats[0] < 1:
            embed.add_field(name="Herätykset", value=f"Herätty {kerrat} ja aina ihmisten aikoihin!", inline=False)
        else:
            embed.add_field(name="Herätykset", value=f"Herätty {kerrat}, joista {rats[0]} täysin rottamaiseen aikaan!", inline=False)
        embed.add_field(name="Jyrkin vastaukset", value=huomentastats, inline=False)
        await ctx.response.send_message(embed=embed, ephemeral=hidden)
        con.close()
    
    @apc.command(name = "leaderboard", description = "Kuka on herännyt eniten!")
    async def leaderboard(self, ctx):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        leaders = db.execute("SELECT uid, COUNT(hour) FROM Huomenet GROUP BY uid ORDER BY COUNT(hour) DESC LIMIT 5").fetchall()
        if len(leaders) == 0:
            await ctx.response.send_message("Kukaan täällä ei ole herännyt.")
            return
        embed = discord.Embed(
            title="Top 5 herääjät:",
            color=discord.Color.dark_magenta()
        )
        i = 0
        for leader in leaders:
            i += 1
            member = discord.utils.get(ctx.guild.members, id=leader[0])
            embed.add_field(name=f"**{i}.** {member.display_name}", value=f"Herätyksiä {leader[1]}", inline=False)
        await ctx.response.send_message(embed=embed)

    
    @apc.command(name = "add", description = "Owner only command")
    @apc.choices(rarity=[
        apc.Choice(name="Normal", value=0),
        apc.Choice(name="Rare", value=1),
        apc.Choice(name="Ultra rare", value=2)
    ], ratness=[
        apc.Choice(name="Lammas", value=0),
        apc.Choice(name="Rotta", value=1)
    ])
    async def addresponse(self, ctx, response: str, rarity: apc.Choice[int], ratness: apc.Choice[int]):
        if ctx.user.id == owner:
            con = sqlite3.connect("data/database.db")
            db = con.cursor()
            if rarity.value == 2:
                ratness.value = 0
            db.execute("INSERT INTO HuomentaResponses(response, rarity, rat) VALUES (?, ?, ?)", [response, rarity.value, ratness.value])
            con.commit()
            con.close()
            await ctx.response.send_message("Vastaus lisätty!", ephemeral=True)
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)