import discord
from discord import app_commands as apc
import json
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from jobs.tasks.cache_config import config
from jobs.database import (
    engine,
    LotteryBets,
    CurrentLottery,
    LotteryPlayers,
    LotteryWins,
)


### TODO: Multiple lines + permaline and automatic re-entry


class LotteryNumbers(discord.ui.Select):
    def __init__(self, options: list):
        super().__init__(options=options, min_values=7, max_values=7)

    async def callback(self, ctx: discord.Interaction):
        with Session(engine) as db:
            self.roundid = db.scalar(select(CurrentLottery.id))
            db.add(
                LotteryBets(
                    uid=ctx.user.id, roundid=self.roundid, row=json.dumps(self.values)
                )
            )
            db.commit()
        await ctx.response.send_message(
            f"Rivisi on tallennettu. Onnea arvontaan!", ephemeral=True
        )


class LotteryView(discord.ui.View):
    def __init__(self, bet: int):
        super().__init__()
        self.bet = bet

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def betconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        options = []
        for i in range(1, 25):
            options.append(discord.SelectOption(label=f"{i}", value=i))

        select = LotteryNumbers(options=options)
        view_select = discord.ui.View()
        view_select.add_item(select)

        with Session(engine) as db:
            db.execute(
                update(LotteryPlayers)
                .values(credits=(LotteryPlayers.credits - self.bet))
                .where(LotteryPlayers.id == ctx.user.id)
            )
            db.execute(
                update(CurrentLottery).values(pool=(CurrentLottery.pool + self.bet))
            )
            db.commit()

        await ctx.response.edit_message(content="Valitse lottorivi", view=view_select)

    @discord.ui.button(label="Ei", style=discord.ButtonStyle.danger)
    async def betdecline(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        await ctx.response.edit_message(content="Lottoon ei osallistuttu", view=None)


class Lottery(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="bank", description="Näytä varallisuutesi")
    async def bank(self, ctx: discord.Interaction):
        with Session(engine) as db:
            tili = db.scalar(
                select(LotteryPlayers.credits).where(LotteryPlayers.id == ctx.user.id)
            )
        tili = 0 if not tili else tili

        await ctx.response.send_message(f"Tilisi saldo on {tili}", ephemeral=True)

    @apc.command(name="setchannel", description="Owner only command")
    async def lotterychannel(self, ctx: discord.Interaction):
        if ctx.user.id == config.owner:
            config.updateconfig("lotterychannel", ctx.channel.id)

            await ctx.response.send_message(
                "Lotto arvotaan jatkossa tällä kanavalla", ephemeral=True
            )

        else:
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)

    @apc.command(name="info", description="Tietoja nykyisestä lotosta")
    async def showpool(self, ctx: discord.Interaction):
        with Session(engine) as db:
            round, pool = db.execute(
                select(CurrentLottery.id, CurrentLottery.pool)
            ).fetchone()
            row = db.scalar(
                select(LotteryBets.row)
                .where(LotteryBets.uid == ctx.user.id)
                .where(LotteryBets.roundid == round)
            )
            if row:
                ownrow = (
                    f"\nOlet mukana arvonnassa rivillä **{', '.join(json.loads(row))}**"
                )
            else:
                ownrow = ""
                row = db.scalar(
                    select(LotteryBets.row)
                    .where(LotteryBets.uid == ctx.user.id)
                    .where(LotteryBets.roundid == (round - 1))
                )
                if row:
                    wins = db.scalar(
                        select(LotteryWins.payout)
                        .where(LotteryWins.uid == ctx.user.id)
                        .where(LotteryWins.roundid == (round - 1))
                    )
                    ownrow = f"\nOlit mukana viime kierroksella rivillä **{', '.join(json.loads(row))}** ja voitit **{wins}** koppelia."
        await ctx.response.send_message(
            f"Lotossa jaossa jopa **{pool}** koppelia!{ownrow}", ephemeral=True
        )

    @apc.command(
        name="place",
        description=f"Osallistu lottoarvontaan (rivin hinta {config.bet} koppelia.)",
    )
    async def makebet(self, ctx: discord.Interaction):
        with Session(engine) as db:
            tili = db.scalar(
                select(LotteryPlayers.credits).where(LotteryPlayers.id == ctx.user.id)
            )
            lastbet = db.scalar(
                select(LotteryBets.roundid)
                .where(LotteryBets.uid == ctx.user.id)
                .order_by(LotteryBets.id.desc())
                .limit(1)
            )
            currentround = db.scalar(select(CurrentLottery.id))

        if lastbet and lastbet == currentround:
            await ctx.response.send_message(
                "Olet jo osallistunut tähän lottokierrokseen!", ephemeral=True
            )
            return
        tili = 0 if not tili else tili

        if config.bet > tili:
            await ctx.response.send_message(
                f"Et ole noin rikas. Tilisi saldo on {tili}, kun osallistuminen vaatii {config.bet}.",
                ephemeral=True,
            )
            return

        await ctx.response.send_message(
            f"Arvontaan osallistuminen maksaa {config.bet} koppelia. Tilisi saldo on {tili}. Osallistutaanko lottoarvontaan?",
            view=LotteryView(config.bet),
            ephemeral=True,
        )

    @apc.command(name="gift", description="Lahjoita koppeleita jollekin toiselle.")
    async def gift(
        self,
        ctx: discord.Interaction,
        recipient: discord.Member,
        amount: apc.Range[int, 1],
    ):
        """
        Allows transferring funds from one user to another.
        """
        if recipient == ctx.user:
            await ctx.response.send_message(
                "Ei helvetti eihän se nyt noin voi mitenkään toimia että rahoja siirretään omaan taskuun.",
                ephemeral=True,
            )
            return

        with Session(engine) as db:
            tili = db.scalar(
                select(LotteryPlayers.credits).where(LotteryPlayers.id == ctx.user.id)
            )

            if not tili or tili < amount:
                await ctx.response.send_message(
                    f"Et ole noin rikas. Tilisi saldo on {0 if not tili else tili}.",
                    ephemeral=True,
                )
                return

            ignore = db.scalar(
                select(
                    select(LotteryPlayers.id)
                    .where(LotteryPlayers.id == recipient.id)
                    .exists()
                )
            )
            if not ignore:
                db.add(LotteryPlayers(id=recipient.id, credits=0))
            db.execute(
                update(LotteryPlayers)
                .values(credits=LotteryPlayers.credits + amount)
                .where(LotteryPlayers.id == recipient.id)
            )
            db.execute(
                update(LotteryPlayers)
                .values(credits=LotteryPlayers.credits - amount)
                .where(LotteryPlayers.id == ctx.user.id)
            )
            db.commit()

        await ctx.response.send_message(
            f"Käyttäjän {recipient.mention} tilille siirretty **{amount}** koppelia.",
            ephemeral=True,
        )
