import discord
import json
from datetime import datetime, timedelta
import pytz
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from jobs.database import engine, Alarms, Users

timeout = 300


class SnoozeButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def wakeupbutton(
        self, ctx: discord.Interaction, button_obj: discord.ui.Button
    ):
        with Session(engine) as db:
            db.execute(update(Alarms).where(Alarms.id == ctx.user.id).values(snooze=0))
            db.commit()
        await ctx.message.delete()


async def snooze(date: datetime, client: discord.Client):
    with Session(engine) as db:
        allalarms = db.execute(
            select(Alarms.id, Alarms.last).where(Alarms.snooze == 1)
        ).fetchall()
    for row in allalarms:
        id = row[0]
        last = row[1]
        if date - last < timedelta(minutes=1):
            continue
        user = client.get_user(id)
        msg = await user.send(
            content=f"ootko jo ylhäällä vitun vätys?", view=SnoozeButton()
        )
        await msg.delete(delay=timeout)


async def alarm(date: datetime, client: discord.Client):
    with Session(engine) as db:
        allalarms = db.execute(
            select(Alarms.id, Alarms.time, Alarms.weekdays, Alarms.last, Alarms.snooze)
        ).fetchall()
        for row in allalarms:
            id = row[0]
            time = row[1]
            weekdays = json.loads(row[2])
            last = row[3]
            snoozer = row[4]
            tz = db.scalar(select(Users.timezone).where(Users.id == id))
            if not tz:
                tz = "Etc/UTC"
            currenthour = datetime.now(pytz.timezone(tz)).hour
            if (
                currenthour < time
                or currenthour >= time + 1
                or (str(date.isoweekday()) not in weekdays)
                or snoozer == 1
                or (date - last < timedelta(minutes=1))
            ):
                continue
            else:
                user = client.get_user(id)
                db.execute(
                    update(Alarms).where(Alarms.id == id).values(last=date, snooze=1)
                )
                db.commit()
                await user.send(
                    content=f"ootko jo ylhäällä vitun vätys?",
                    view=SnoozeButton(),
                    delete_after=timeout,
                )
