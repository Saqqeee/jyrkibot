import discord
from discord import app_commands as apc
import sqlite3

class Drunk(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    # Let the user log themselves into the table or update their information
    @apc.command(name="settings", description="Päivitä tietojasi tai luo profiili. Syötä paino kokonaislukuna.")
    @apc.choices(sex=[
        apc.Choice(name="Mies", value=0.68),
        apc.Choice(name="Nainen", value=0.55)
    ])
    async def settings(self, ctx: discord.Interaction, kg: int = None, sex: apc.Choice[float] = None):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        db.execute("INSERT OR IGNORE INTO Alcoholist (id, weight, r, bac) VALUES (?, 80, 0.68, 0.0)", [ctx.user.id])
        if kg != None:
            db.execute("UPDATE Alcoholist SET weight=? WHERE id=?", [kg, ctx.user.id])
        if sex != None:
            db.execute("UPDATE Alcoholist SET r=? WHERE id=?", [sex.value, ctx.user.id])
        con.commit()
        con.close()
        await ctx.response.send_message("Tiedot päivitetty onnistuneesti.", ephemeral=True)

    # Add a drink to database for user
    @apc.command(name="drink", description="Juo! Oletuksena 0.33-litrainen 4.7% juoma. Syötä tilavuus litroina ja vahvuus prosentteina.")
    async def drink(self, ctx: discord.Interaction, volume: float = 0.33, content: float = 4.6):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        info = db.execute("SELECT weight, r FROM Alcoholist WHERE id=?", [ctx.user.id]).fetchone()
        if not info:
            con.close()
            await ctx.response.send_message(f"Käyttäjääsi ei löydetty! Aseta tietosi komennolla /{self.settings.qualified_name}", ephemeral=True)
            return
        grams = (volume*1000)*(content/100)*0.789
        bac = grams/((info[0]*1000)*info[1])*100
        db.execute("UPDATE Alcoholist SET bac=bac+? WHERE id=?", [bac, ctx.user.id])
        con.commit()
        con.close()
        await ctx.response.send_message("Hyvin juotu!", ephemeral=True)
    
    # Feth blood alcohol content from database
    @apc.command(name="check", description="Tarkista veren alkoholipitoisuus")
    async def howdrunk(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        bac = db.execute("SELECT bac FROM Alcoholist WHERE id=?", [ctx.user.id]).fetchone()
        con.close()
        if not bac:
            await ctx.response.send_message(f"Käyttäjääsi ei löydetty! Aseta tietosi komennolla /{self.settings.qualified_name}", ephemeral=True)
            return
        await ctx.response.send_message(f"Veresi alkoholipitoisuus on arviolta {round(bac[0]*10, 1)} promillea.", ephemeral=True)
    
    # For actual retards
    @apc.command(name="reset", description="on varmaa vitu jees olla legit retardi")
    async def bacreset(self, ctx: discord.Interaction):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        db.execute("UPDATE Alcoholist SET bac=0 WHERE id=?", [ctx.user.id])
        con.commit()
        con.close()
        await ctx.response.send_message("Koeta nyt selvitä", ephemeral=True)
