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
    def __init__(self, options: list):
        super().__init__(options=options, min_values=7, max_values=7)
        self.con = sqlite3.connect("data/database.db")
        self.db = self.con.cursor()

    async def callback(self, ctx: discord.Interaction):
        self.roundid = self.db.execute("SELECT id FROM CurrentLottery").fetchone()[0]
        self.db.execute("INSERT INTO LotteryBets(uid, roundid, row) VALUES (?,?,?)", [ctx.user.id, self.roundid, json.dumps(self.values)])
        self.con.commit()
        self.con.close()
        await ctx.response.send_message(f"Rivisi on tallennettu. Onnea arvontaan!", ephemeral=True)

class LotteryView(discord.ui.View):
    def __init__(self, bet: int):
        super().__init__()
        self.con = sqlite3.connect("data/database.db")
        self.db = self.con.cursor()
        self.bet = bet
    
    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def betconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        options = []
        for i in range(1,25):
            options.append(discord.SelectOption(label=f"{i}", value=i))
        select = LotteryNumbers(options=options)
        view_select = discord.ui.View()
        view_select.add_item(select)

        self.db.execute("UPDATE LotteryPlayers SET credits=credits-? WHERE id=?", [self.bet, ctx.user.id])
        self.db.execute("UPDATE CurrentLottery SET pool=pool+?", [self.bet])
        self.con.commit()
        self.con.close()
        await ctx.response.edit_message(content="Valitse lottorivi", view=view_select)
    
    @discord.ui.button(label="Ei", style=discord.ButtonStyle.danger)
    async def betdecline(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        self.con.close()
        await ctx.response.edit_message(content="Lottoon ei osallistuttu", view=None)

class Lottery(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    @apc.command(name = "bank", description = "Näytä varallisuutesi")
    async def bank(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        tili = db.execute("SELECT credits FROM LotteryPlayers WHERE id=?", [ctx.user.id]).fetchone()
        con.close()
        tili = 0 if not tili else tili[0]
        await ctx.response.send_message(f"Tilisi saldo on {tili}", ephemeral=True)
    
    @apc.command(name = "setchannel", description = "Owner only command")
    async def lotterychannel(self, ctx: discord.Interaction):
        if ctx.user.id == owner:
            config["lotterychannel"] = ctx.channel_id
            with open("cfg/cfg.json", "w+") as confile:
                json.dump(config, confile)
            await ctx.response.send_message("Lotto arvotaan jatkossa tällä kanavalla", ephemeral=True)
        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)

    @apc.command(name = "info", description = "Tietoja nykyisestä lotosta")
    async def showpool(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        round, pool = db.execute("SELECT id, pool FROM CurrentLottery").fetchone()
        row = db.execute("SELECT row FROM LotteryBets WHERE uid=? AND roundid=?", [ctx.user.id, round]).fetchone()
        ownrow = ""
        if row is not None:
            ownrow = f"\nOlet mukana arvonnassa rivillä **{', '.join(json.loads(row[0]))}**"
        else:
            row = db.execute("SELECT row FROM LotteryBets WHERE uid=? AND roundid=?", [ctx.user.id, round-1]).fetchone()
            if row is not None:
                wins = db.execute("SELECT payout FROM LotteryWins WHERE uid=? AND roundid=?", [ctx.user.id, round-1]).fetchone()
                ownrow = f"\nOlit mukana viime kierroksella rivillä **{', '.join(json.loads(row[0]))}** ja voitit **{wins[0]}** koppelia"
        con.close()
        await ctx.response.send_message(f"Lotossa jaossa jopa **{pool}** koppelia!{ownrow}.", ephemeral=True)
        
    @apc.command(name = "place", description = "Aseta panos tämän viikon lottoarvontaan (hinta 2 koppeli)")
    async def makebet(self, ctx: discord.Interaction):
        bet = 2
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        tili = db.execute("SELECT credits FROM LotteryPlayers WHERE id=?", [ctx.user.id]).fetchone()
        lastbet = db.execute("SELECT roundid FROM LotteryBets WHERE uid=? ORDER BY id DESC LIMIT 1", [ctx.user.id]).fetchone()
        currentround = db.execute("SELECT id FROM CurrentLottery").fetchone()
        con.close()

        if lastbet is not None and lastbet[0] == currentround[0]:
            await ctx.response.send_message("Olet jo osallistunut tähän lottokierrokseen!", ephemeral=True)
            return
        tili = 0 if not tili else tili[0]

        if bet > tili:
            await ctx.response.send_message(f"Et ole noin rikas. Tilisi saldo on {tili}, kun osallistuminen vaatii {bet}.", ephemeral=True)
            return

        await ctx.response.send_message(f"Arvontaan osallistuminen maksaa {bet} koppelia. Tilisi saldo on {tili}. Osallistutaanko lottoarvontaan?", view=LotteryView(bet), ephemeral=True)