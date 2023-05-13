import discord
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
import json
from datetime import datetime, date
from discord import app_commands as apc
from discord import ui
from jobs.database import engine, Alarms


class DaySelect(ui.Select):
    """
    This is the last Discord.UI class that is called within the /set alarm command chain, so
    upon success it updates the given times and dates into the database.

    Args:
        options (list): List of options set by class discord.SelectOption()

        time (int): The hour at which the alarm should ring
    """

    def __init__(self, options: list, time: int):
        super().__init__(options=options, min_values=1, max_values=7)
        self.time = time

    async def callback(self, ctx: discord.Interaction):
        with Session(engine) as db:
            isinanal = db.scalar(select(select(Alarms).exists()))
            if not isinanal:
                db.add(Alarms(id=ctx.user.id))
            db.execute(
                update(Alarms)
                .where(Alarms.id == ctx.user.id)
                .values(time=self.time, weekdays=json.dumps(self.values), snooze=0)
            )
            last = db.scalar(select(Alarms.last).where(id == ctx.user.id))
            if not last:
                db.execute(
                    update(Alarms)
                    .where(Alarms.id == ctx.user.id)
                    .values(last=datetime.now())
                )
            db.commit()
        await ctx.response.edit_message(content="Herätys asetettu", view=None)


class TimeSelect(ui.Select):
    def __init__(self, options: list):
        super().__init__(options=options, min_values=1, max_values=1)
        with open("slashcommands/weekdays.json", "r") as dayfile:
            self.weekdays = json.load(dayfile)

    async def callback(self, ctx: discord.Interaction):
        self.time = int(self.values[0])
        self.dayoptions = []
        for i in range(1, 8):
            self.day = self.weekdays[str(i)]
            self.dayoptions.append(discord.SelectOption(label=f"{self.day}", value=i))
        daysel = DaySelect(options=self.dayoptions, time=self.values[0])
        dayview = discord.ui.View()
        dayview.add_item(daysel)
        await ctx.response.edit_message(
            content="Aseta viikonpäivät joina haluat herätyksen:", view=dayview
        )


class SelectView(ui.View):
    def __init__(self):
        super().__init__()
        self.timeoptions = []
        for i in range(24):
            self.timeoptions.append(discord.SelectOption(label=f"{i}:00", value=i))
        self.add_item(TimeSelect(self.timeoptions))


class AlarmDelConfirm(ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def delconfirm(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        with Session(engine) as db:
            db.execute(delete(Alarms).where(Alarms.id == ctx.user.id))
            db.commit()
        await ctx.response.edit_message(content="Herätys poistettu.", view=None)

    @discord.ui.button(label="Ei", style=discord.ButtonStyle.danger)
    async def deldecline(self, ctx: discord.Interaction, button_obj: discord.ui.Button):
        await ctx.response.edit_message(content="Asia kunnossa.", view=None)


class Alarm(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @apc.command(name="set", description="Aseta itsellesi herätys.")
    async def setalarm(self, ctx: discord.Interaction):
        await ctx.response.send_message(
            "Aseta herätysaika:", view=SelectView(), ephemeral=True
        )

    @apc.command(name="remove", description="Poista herätys.")
    async def delalarm(self, ctx: discord.Interaction):
        with Session(engine) as db:
            curalarm = db.execute(select(Alarms).where(Alarms.id == ctx.user.id)).all()

        # self.con = sqlite3.connect("data/database.db")
        # self.db = self.con.cursor()
        # self.curalarm = self.db.execute(
        #    "SELECT * FROM Alarms WHERE id=?", [ctx.user.id]
        # ).fetchone()
        # self.con.close()
        if not curalarm:
            await ctx.response.send_message(
                "Sinulla ei ole herätystä jota poistaa.", ephemeral=True
            )
            return
        await ctx.response.send_message(
            "Poistetaanko varmasti herätys?", view=AlarmDelConfirm(), ephemeral=True
        )
