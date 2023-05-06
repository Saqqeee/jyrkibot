import discord
from discord import app_commands as apc
import json
import random
import sqlite3
import math
from datetime import datetime, timedelta

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
owner = config["owner"]
lotterychannel = config["lotterychannel"]

class LotteryNumbers(discord.ui.Select):
    def __init__(self, options: list, con: sqlite3.Connection):
        super().__init__(options=options, min_values=7, max_values=7)
        self.con = con
        self.db = con.cursor()

    async def callback(self, ctx: discord.Interaction):
        self.roundid = self.db.execute("SELECT id FROM CurrentLottery").fetchone()[0]
        self.db.execute("INSERT INTO LotteryBets(uid, roundid, row) VALUES (?,?,?)", [ctx.user.id, self.roundid, json.dumps(self.values)])
        await ctx.response.send_message(f"Rivisi on tallennettu. Onnea arvontaan!", ephemeral=True)
        self.con.commit()
        self.con.close()

class LotteryView(discord.ui.View):
    def __init__(self, con: sqlite3.Connection, bet: int):
        super().__init__()
        self.con = con
        self.db = con.cursor()
        self.bet = bet
    
    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def betconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        options = []
        for i in range(1,25):
            options.append(discord.SelectOption(label=f"{i}", value=i))
        select = LotteryNumbers(options=options, con=self.con)
        view_select = discord.ui.View()
        view_select.add_item(select)

        self.db.execute("UPDATE LotteryPlayers SET credits=credits-? WHERE id=?", [self.bet, ctx.user.id])
        self.db.execute("UPDATE CurrentLottery SET pool=pool+?", [self.bet])
        await ctx.response.edit_message(content="Valitse lottorivi", view=view_select)
    
    @discord.ui.button(label="Ei", style=discord.ButtonStyle.danger)
    async def betdecline(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        await ctx.response.edit_message(content="Lottoon ei osallistuttu", view=None)

def calculatewinnings(amount: int):
    return (math.comb(25, amount) - math.comb(25, amount-1))/math.comb(25, 7)

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
    if (date.hour < 20) or (date < datetime.fromisoformat(startdate[0]) + timedelta(hours=23)):
        con.close()
        return
    round, pool = db.execute("SELECT id, pool FROM CurrentLottery").fetchone()
    bets = db.execute("SELECT uid, row FROM LotteryBets WHERE roundid = ?", [round]).fetchall()
    winrow = random.sample([*range(1,25)], k=7)
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
        shares.append(math.floor(calculatewinnings(key))*pool)
        for mies in value:
            db.execute("INSERT INTO LotteryWins(uid, roundid, payout, date) VALUES (?,?,?,?)", [mies[0], round, math.floor(shares[key]/len(value)), date])
            db.execute("UPDATE LotteryPlayers SET credits = credits + ? WHERE id = ?", [math.floor(shares[key]/len(value)), mies[0]])
    for x in shares:
        pool -= x
    db.execute("UPDATE CurrentLottery SET id=id+1, pool=?, startdate=?", [pool, datetime.now()])

    embed = discord.Embed(
        title="Kierroksen voittajat",
        color=discord.Color.dark_magenta()
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
        embed.add_field(name=f"**{i}.** {member.display_name}", value=f"{mies[1]} oikein")

    con.commit()
    con.close()
    await channel.send(content="Arvonnat suoritettu! Nähdään huomenna samaan aikaan.", embed=embed)

class Lottery(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    @apc.command(name = "bank", description = "Näytä varallisuutesi")
    async def bank(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        tili = db.execute("SELECT credits FROM LotteryPlayers WHERE id=?", [ctx.user.id]).fetchone()
        tili = 0 if not tili else tili[0]
        await ctx.response.send_message(f"Tilisi saldo on {tili}", ephemeral=True)
        con.commit()
        con.close()
    
    @apc.command(name = "setchannel", description = "Owner only command")
    async def lotterychannel(self, ctx: discord.Interaction):
        if ctx.user.id == owner:
            config["lotterychannel"] = ctx.channel_id
            with open("cfg/cfg.json", "w+") as confile:
                json.dump(config, confile)
            await ctx.response.send_message("Lotto arvotaan jatkossa tällä kanavalla", ephemeral=True)
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)

    @apc.command(name = "prizepool", description = "Palkintopotti")
    @apc.checks.cooldown(1, 60, key=lambda i: (i.guild_id))
    async def showpool(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        pool = db.execute("SELECT pool FROM CurrentLottery").fetchone()[0]
        await ctx.response.send_message(f"Lotossa tänään jaossa jopa {pool} krediittiä!")
    
    @showpool.error
    async def on_test_error(self, ctx: discord.Interaction, error: apc.AppCommandError):
        if isinstance(error, apc.CommandOnCooldown):
            await ctx.response.send_message(str(error), ephemeral=True)
        
    @apc.command(name = "place", description = "Aseta panos tämän viikon lottoarvontaan (hinta 2 krediittiä)")
    async def makebet(self, ctx: discord.Interaction):
        bet = 2
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        tili = db.execute("SELECT credits FROM LotteryPlayers WHERE id=?", [ctx.user.id]).fetchone()
        lastbet = db.execute("SELECT roundid FROM LotteryBets WHERE uid=? ORDER BY id DESC LIMIT 1", [ctx.user.id]).fetchone()
        currentround = db.execute("SELECT id FROM CurrentLottery").fetchone()
        if lastbet is not None and lastbet[0] == currentround[0]:
            await ctx.response.send_message("Olet jo osallistunut tähän lottokierrokseen!", ephemeral=True)
            return
        tili = 0 if not tili else tili[0]

        if bet > tili:
            await ctx.response.send_message(f"Et ole noin rikas. Tilisi saldo on {tili}.", ephemeral=True)
            con.close()
            return

        await ctx.response.send_message(f"Arvontaan osallistuminen maksaa {bet}. Tilisi saldo on {tili}. Osallistutaanko lottoarvontaan?", view=LotteryView(con, bet), ephemeral=True)