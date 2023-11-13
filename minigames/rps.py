import discord

RPS_ICONS = {
    "rock": "\U0001FAA8",
    "paper": "\U0001F4C4",
    "scissors": "\U00002702",
}


class Rps:
    def __init__(self, ctx: discord.Interaction):
        self.ctx = ctx
        self.player1 = self.ctx.user
        self.player2 = None

    async def command(self):
        await self.ctx.response.defer(ephemeral=True, thinking=False)
        await self.find_player()

    async def find_player(self):
        button_view = PlayView(self)

        response = await self.ctx.channel.send(
            content=f"{self.player1.name} wants to play Rock, Paper, Scissors",
            view=button_view,
        )

        timed_out = await button_view.wait()
        await response.edit(view=None)

        if timed_out:
            self.ctx.followup.send(content="No playmate found :(")
            return

        self.player2 = button_view.ctx.user
        await self.ctx.channel.send(content=f"{self.player2.name} agreed to play")

        await self.game(button_view.ctx)

    async def game(self, ctx2: discord.Interaction):
        p1c = SelectView(self.ctx)
        p2c = SelectView(ctx2)

        msg1 = await self.ctx.followup.send(content="Pick one", view=p1c)
        msg2 = await ctx2.followup.send(content="Pick one", view=p2c, ephemeral=True)

        p1to = await p1c.wait()
        if not p2c.is_finished():
            p2to = await p2c.wait()

        await msg1.delete()
        await msg2.delete()

        if p1c.choice and p2c.choice:
            await self.ctx.channel.send(
                f"{self.ctx.user.mention} {RPS_ICONS[p1c.choice]} - {RPS_ICONS[p2c.choice]} {ctx2.user.mention}"
            )


class PlayView(discord.ui.View):
    def __init__(self, parent):
        super().__init__(timeout=None)

        self.parent = parent
        self.button = self.PlayButton()
        self.add_item(self.button)
        self.ctx: discord.Interaction | None = None

    async def interaction_check(self, ctx: discord.Interaction):
        if ctx.user == self.parent.player1:
            await ctx.response.send_message(
                content="You can't play with yourself", ephemeral=True
            )
            return False
        return True

    class PlayButton(discord.ui.Button):
        def __init__(self):
            super().__init__()

            self.label = "Play!"
            self.style = discord.ButtonStyle.blurple

        async def callback(self, ctx: discord.Interaction):
            self.view.ctx = ctx
            await self.view.ctx.response.defer(ephemeral=True, thinking=False)
            self.view.stop()


class SelectView(discord.ui.View):
    def __init__(self, ctx: discord.Interaction):
        super().__init__(timeout=None)
        self.ctx = ctx

        poss = ["rock", "paper", "scissors"]
        for item in poss:
            self.add_item(self.ChooseButton(item))

        self.choice: str | None = None

    def on_timeout(self):
        self.ctx.channel.send(content=f"{self.ctx.user.name} is bald")

    class ChooseButton(discord.ui.Button):
        def __init__(self, choice: str):
            super().__init__()
            self.choice = choice

            self.emoji = discord.PartialEmoji(name=RPS_ICONS[self.choice])

        async def callback(self, ctx: discord.Interaction):
            self.view.choice = self.choice
            self.view.stop()
            await ctx.response.send_message(
                content=f"You picked {self.choice} {RPS_ICONS[self.choice]}",
                ephemeral=True,
            )
