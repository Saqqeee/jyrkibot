import discord
from discord import app_commands as apc
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from jobs.database import engine, Alcoholist


class Drunk(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    # Let the user log themselves into the table or update their information
    @apc.command(
        name="settings",
        description="Päivitä tietojasi tai luo profiili. Syötä paino kokonaislukuna.",
    )
    @apc.choices(
        sex=[apc.Choice(name="Mies", value=0.68), apc.Choice(name="Nainen", value=0.55)]
    )
    async def settings(
        self,
        ctx: discord.Interaction,
        kg: apc.Range[int, 1] = None,
        sex: apc.Choice[float] = None,
    ):
        with Session(engine) as db:
            isinalc = db.scalar(
                select(select(Alcoholist).where(Alcoholist.id == ctx.user.id).exists())
            )
            if not isinalc:
                db.add(Alcoholist(id=ctx.user.id, weight=80, r=0.68, bac=0.0))
            if kg != None:
                db.execute(
                    update(Alcoholist)
                    .where(Alcoholist.id == ctx.user.id)
                    .values(weight=kg)
                )
            if sex != None:
                db.execute(
                    update(Alcoholist)
                    .where(Alcoholist.id == ctx.user.id)
                    .values(r=sex.value)
                )
            db.commit()
        await ctx.response.send_message(
            "Tiedot päivitetty onnistuneesti.", ephemeral=True
        )

    # Add a drink to database for user
    @apc.command(
        name="drink",
        description="Juo! Oletuksena 0.33-litrainen 4.6% juoma. Syötä tilavuus litroina ja vahvuus prosentteina.",
    )
    async def drink(
        self,
        ctx: discord.Interaction,
        volume: apc.Range[float, 0.0, 10.0] = 0.33,
        content: apc.Range[float, 0.0, 96.0] = 4.6,
    ):
        with Session(engine) as db:
            info = db.execute(
                select(Alcoholist.weight, Alcoholist.r).where(
                    Alcoholist.id == ctx.user.id
                )
            ).fetchone()
            if not info:
                await ctx.response.send_message(
                    f"Käyttäjääsi ei löydetty! Aseta tietosi komennolla /{self.settings.qualified_name}",
                    ephemeral=True,
                )
                return
            grams = (volume * 1000) * (content / 100) * 0.789
            bac = grams / ((info[0] * 1000) * info[1]) * 1000
            db.execute(
                update(Alcoholist)
                .where(Alcoholist.id == ctx.user.id)
                .values(bac=Alcoholist.bac + bac)
            )
            db.commit()
        await ctx.response.send_message("Hyvin juotu!", ephemeral=True)

    # Fetch blood alcohol content from database
    @apc.command(name="check", description="Tarkista veren alkoholipitoisuus")
    async def howdrunk(self, ctx: discord.Interaction):
        with Session(engine) as db:
            bac = db.scalar(select(Alcoholist.bac).where(Alcoholist.id == ctx.user.id))
        if bac == None:
            await ctx.response.send_message(
                f"Käyttäjääsi ei löydetty! Aseta tietosi komennolla /{self.settings.qualified_name}",
                ephemeral=True,
            )
            return
        await ctx.response.send_message(
            f"Veresi alkoholipitoisuus on arviolta {round(bac, 1)} promillea.",
            ephemeral=True,
        )

    # For actual retards
    @apc.command(name="reset", description="on varmaa vitu jees olla legit retardi")
    async def bacreset(self, ctx: discord.Interaction):
        with Session(engine) as db:
            db.execute(
                update(Alcoholist).where(Alcoholist.id == ctx.user.id).values(bac=0)
            )
            db.commit()
        await ctx.response.send_message("Koeta nyt selvitä", ephemeral=True)
