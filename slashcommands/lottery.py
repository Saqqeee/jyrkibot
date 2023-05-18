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


### TODO: Allow the user to select multiple lines, allow the user to subscribe for a period of time


### UI COMPONENTS ###


class RerollButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(
        emoji="🎲", label="Osallistu uudelleen", style=discord.ButtonStyle.blurple
    )
    async def reroll(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        """This should be the same as the makebet command"""
        # Get user's balance, user's last participated round and current round
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

        # If user is already participating in this round, send an error message and return
        if lastbet and lastbet == currentround:
            await ctx.response.send_message(
                "Olet jo osallistunut tähän lottokierrokseen!", ephemeral=True
            )
            return

        tili = 0 if not tili else tili

        # If balance is not enough, send an error message and return
        if config.bet > tili:
            await ctx.response.send_message(
                f"Et ole noin rikas. Tilisi saldo on {tili}, kun osallistuminen vaatii {config.bet}.",
                ephemeral=True,
            )
            return

        # Send a UI component for confirming participation
        # The UI component LotteryView handles the rest of this interaction
        await ctx.response.send_message(
            f"Arvontaan osallistuminen maksaa {config.bet} koppelia. Tilisi saldo on {tili}. Osallistutaanko lottoarvontaan?",
            view=LotteryView(config.bet),
            ephemeral=True,
        )


class LotteryNumbers(discord.ui.Select):
    """Select component that takes a min and max of 7 values"""

    def __init__(self, options: list):
        super().__init__(options=options, min_values=7, max_values=7)

    async def callback(self, ctx: discord.Interaction):
        with Session(engine) as db:
            # Get current round id
            self.roundid = db.scalar(select(CurrentLottery.id))

            # Insert selected line into database
            db.add(
                LotteryBets(
                    uid=ctx.user.id, roundid=self.roundid, row=json.dumps(self.values)
                )
            )
            db.commit()

        # Edit the response
        await ctx.response.edit_message(
            content=f"Rivisi **{', '.join(self.values)}** on tallennettu. Onnea arvontaan!",
            view=None,
        )


class LotteryView(discord.ui.View):
    """Confirmation view that gives the user 'yes' and 'no' buttons"""

    def __init__(self, bet: int):
        super().__init__()
        self.bet = bet

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def betconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        """The 'yes' button"""

        # Initialize a LotteryNumbers view for the followup
        options = []
        for i in range(1, 25):
            options.append(discord.SelectOption(label=f"{i}", value=i))
        select = LotteryNumbers(options=options)
        view_select = discord.ui.View()
        view_select.add_item(select)

        with Session(engine) as db:
            # Reduce user's balance by a set amount
            db.execute(
                update(LotteryPlayers)
                .values(credits=(LotteryPlayers.credits - self.bet))
                .where(LotteryPlayers.id == ctx.user.id)
            )
            # Add the amount to the prize pool
            db.execute(
                update(CurrentLottery).values(pool=(CurrentLottery.pool + self.bet))
            )
            db.commit()

        # Edit response and continue to selecting numbers
        # Change the view to LotteryNumbers
        await ctx.response.edit_message(content="Valitse lottorivi", view=view_select)

    @discord.ui.button(label="Ei", style=discord.ButtonStyle.danger)
    async def betdecline(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        """The 'no' button"""

        # Edit response
        await ctx.response.edit_message(content="Lottoon ei osallistuttu", view=None)


### SLASH COMMANDS ###


class Lottery(apc.Group):
    """Command group containing slash commands related to the lottery system"""

    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="bank", description="Näytä varallisuutesi")
    async def bank(self, ctx: discord.Interaction):
        """Slash command allowing the user to check their own balance"""

        # Get balance or set it to 0 if the user has no account in the database
        with Session(engine) as db:
            tili = db.scalar(
                select(LotteryPlayers.credits).where(LotteryPlayers.id == ctx.user.id)
            )
        tili = 0 if not tili else tili

        # Send response
        await ctx.response.send_message(f"Tilisi saldo on {tili}", ephemeral=True)

    @apc.command(name="setchannel", description="Owner only command")
    async def lotterychannel(self, ctx: discord.Interaction):
        """Owner-only slash command for setting the lottery channel"""

        # Check if command user is the owner set in the config
        if ctx.user.id == config.owner:
            # Update interaction channel to config as the lottery channel and send response
            config.updateconfig("lotterychannel", ctx.channel.id)
            await ctx.response.send_message(
                "Lotto arvotaan jatkossa tällä kanavalla", ephemeral=True
            )

        else:
            # For users other than the owner, send an error message
            await ctx.response.send_message("Et voi tehdä noin!", ephemeral=True)

    @apc.command(name="info", description="Tietoja nykyisestä lotosta")
    async def showpool(self, ctx: discord.Interaction):
        """Slash command for getting some information about the current state of lottery"""

        with Session(engine) as db:
            # Get current round and prizepool
            round, pool = db.execute(
                select(CurrentLottery.id, CurrentLottery.pool)
            ).fetchone()

            # Get user's line in this round
            row = db.scalar(
                select(LotteryBets.row)
                .where(LotteryBets.uid == ctx.user.id)
                .where(LotteryBets.roundid == round)
            )

            ownrow = ""
            if row:
                # If the user has a line in, remind them of it
                ownrow = (
                    f"\nOlet mukana arvonnassa rivillä **{', '.join(json.loads(row))}**"
                )
            else:
                # Else get last round's line and winnings
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
                    # Append to response
                    ownrow = f"\nOlit mukana viime kierroksella rivillä **{', '.join(json.loads(row))}** ja voitit **{wins}** koppelia."

        # Send response
        await ctx.response.send_message(
            f"Lotossa jaossa jopa **{pool}** koppelia!{ownrow}", ephemeral=True
        )

    @apc.command(
        name="place",
        description=f"Osallistu lottoarvontaan (rivin hinta {config.bet} koppelia.)",
    )
    async def makebet(self, ctx: discord.Interaction):
        """Slash command for participating in the ongoing round of lottery"""

        # Get user's balance, user's last participated round and current round
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

        # If user is already participating in this round, send an error message and return
        if lastbet and lastbet == currentround:
            await ctx.response.send_message(
                "Olet jo osallistunut tähän lottokierrokseen!", ephemeral=True
            )
            return

        tili = 0 if not tili else tili

        # If balance is not enough, send an error message and return
        if config.bet > tili:
            await ctx.response.send_message(
                f"Et ole noin rikas. Tilisi saldo on {tili}, kun osallistuminen vaatii {config.bet}.",
                ephemeral=True,
            )
            return

        # Send a UI component for confirming participation
        # The UI component LotteryView handles the rest of this interaction
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
        """Slash command for transferring funds from one user to another"""

        # Send an error message and return if a user tries to gift credits to themself
        if recipient == ctx.user:
            await ctx.response.send_message(
                "Ei helvetti eihän se nyt noin voi mitenkään toimia että rahoja siirretään omaan taskuun.",
                ephemeral=True,
            )
            return

        with Session(engine) as db:
            # Get user's current balance
            tili = db.scalar(
                select(LotteryPlayers.credits).where(LotteryPlayers.id == ctx.user.id)
            )

            # If balance is not enough, send an error message and return
            if not tili or tili < amount:
                await ctx.response.send_message(
                    f"Et ole noin rikas. Tilisi saldo on {0 if not tili else tili}.",
                    ephemeral=True,
                )
                return

            # Check if the recipient has an account in the database
            ignore = db.scalar(
                select(
                    select(LotteryPlayers.id)
                    .where(LotteryPlayers.id == recipient.id)
                    .exists()
                )
            )

            # If the recipient has no account, create one
            if not ignore:
                db.add(LotteryPlayers(id=recipient.id, credits=0))

            # Add credits to recipient's account
            db.execute(
                update(LotteryPlayers)
                .values(credits=LotteryPlayers.credits + amount)
                .where(LotteryPlayers.id == recipient.id)
            )
            # Remove credits from sender's account
            db.execute(
                update(LotteryPlayers)
                .values(credits=LotteryPlayers.credits - amount)
                .where(LotteryPlayers.id == ctx.user.id)
            )
            db.commit()

        # Send success message
        await ctx.response.send_message(
            f"Käyttäjän {recipient.mention} tilille siirretty **{amount}** koppelia.",
            ephemeral=True,
        )
