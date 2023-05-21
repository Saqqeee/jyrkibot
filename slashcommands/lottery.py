import discord
from discord import app_commands as apc
import json
import random
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


### TODO: Allow the user to select multiple lines, add possibility for subscriptions


### UI COMPONENTS ###


class RerollButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=86400)

    @discord.ui.button(
        emoji="🎲", label="Osallistu uudelleen", style=discord.ButtonStyle.blurple
    )
    async def reroll(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        """Presents the player with buttons for selecting their new line"""

        await betbuttons(ctx)


class LotteryNumbers(discord.ui.Select):
    """Select component that takes a min and max of 7 values"""

    def __init__(self, options: list):
        super().__init__(options=options, min_values=7, max_values=7)

    async def callback(self, ctx: discord.Interaction):
        await addline(ctx, self.values)


class NewLineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Uusi rivi", style=discord.ButtonStyle.blurple)

    async def callback(self, ctx: discord.Interaction):
        """Select a new line to participate with"""

        # Initialize a LotteryNumbers view for the followup
        options = []
        for i in range(1, 25):
            options.append(discord.SelectOption(label=f"{i}", value=i))
        select = LotteryNumbers(options=options)
        view_select = discord.ui.View()
        view_select.add_item(select)

        # Edit response and continue to selecting numbers
        # Change the view to LotteryNumbers
        await ctx.response.edit_message(content="Valitse lottorivi", view=view_select)


class SameLineButton(discord.ui.Button):
    """Participate with the previous line"""

    def __init__(self, line):
        super().__init__(label="Edellinen rivi", style=discord.ButtonStyle.blurple)
        self.line = json.loads(line)

    async def callback(self, ctx: discord.Interaction):
        await addline(ctx, self.line)


class RandLineButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Satunnainen rivi", style=discord.ButtonStyle.blurple)

    async def callback(self, ctx: discord.Interaction):
        """Participate with random line"""

        self.line = random.sample([*range(1, 25)], k=7)
        for i in range(len(self.line)):
            self.line[i] = str(self.line[i])
        await addline(ctx, self.line)


class LotteryView(discord.ui.View):
    """Confirmation view that gives the user 'yes' and 'no' buttons"""

    def __init__(self, bet: int):
        super().__init__()
        self.bet = bet

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def betconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        """The 'yes' button"""

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
            # Get user's previous line
            prevline = db.scalar(
                select(LotteryBets.row)
                .where(LotteryBets.uid == ctx.user.id)
                .where(LotteryBets.roundid == (CurrentLottery.id - 1))
            )

        selectbuttons = discord.ui.View()
        if prevline:
            selectbuttons.add_item(SameLineButton(line=prevline))
        selectbuttons.add_item(NewLineButton())
        selectbuttons.add_item(RandLineButton())

        await ctx.response.edit_message(content="Valitse yksi", view=selectbuttons)

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

        await betbuttons(ctx)

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


### FUNCTIONS ###


async def betbuttons(ctx: discord.Interaction):
    """Function used by the makebet command and reroll button."""

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


async def addline(ctx: discord.Interaction, line: list):
    def sortering(e):
        return int(e)

    line.sort(key=sortering)

    with Session(engine) as db:
        # Get current round id
        roundid = db.scalar(select(CurrentLottery.id))

        # Insert selected line into database
        db.add(LotteryBets(uid=ctx.user.id, roundid=roundid, row=json.dumps(line)))
        db.commit()

    # Edit the response
    await ctx.response.edit_message(
        content=f"Rivisi **{', '.join(line)}** on tallennettu. Onnea arvontaan!",
        view=None,
    )
