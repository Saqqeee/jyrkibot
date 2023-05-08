import discord
import sqlite3
import json
from datetime import datetime, timedelta
import pytz

timeout = 300


class SnoozeButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="Kyllä", style=discord.ButtonStyle.success)
    async def wakeupbutton(
        self, ctx: discord.Interaction, button_obj: discord.ui.Button
    ):
        con = sqlite3.connect("data/database.db")
        db = con.cursor()
        db.execute("UPDATE Alarms SET snooze=0 WHERE id=?", [ctx.user.id])
        con.commit()
        con.close()
        await ctx.message.delete()


async def snooze(date: datetime, client: discord.Client):
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    allalarms = db.execute("SELECT * FROM Alarms WHERE snooze=1").fetchall()
    for row in allalarms:
        id = row[0]
        last = row[3]
        if date - datetime.fromisoformat(last) < timedelta(minutes=1):
            continue
        user = client.get_user(id)
        msg = await user.send(
            content=f"ootko jo ylhäällä vitun vätys?", view=SnoozeButton()
        )
        await msg.delete(delay=timeout)


async def alarm(date: datetime, client: discord.Client):
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    allalarms = db.execute("SELECT * FROM Alarms").fetchall()

    for row in allalarms:
        id = row[0]
        time = row[1]
        weekdays = json.loads(row[2])
        last = row[3]
        snoozer = row[4]
        tz = db.execute("SELECT timezone FROM Users WHERE id=?", [id]).fetchone()
        if not tz:
            tz = "Etc/UTC"
        else:
            tz = tz[0]
        currenthour = datetime.now(pytz.timezone(tz)).hour
        if (
            currenthour < time
            or currenthour >= time + 1
            or (str(date.isoweekday()) not in weekdays)
            or snoozer == 1
            or (date - datetime.fromisoformat(last) < timedelta(hours=1))
        ):
            continue
        else:
            user = client.get_user(id)
            db.execute("UPDATE Alarms SET last=?, snooze=1 WHERE id=?", [date, id])
            con.commit()
            con.close()
            msg = await user.send(
                content=f"ootko jo ylhäällä vitun vätys?", view=SnoozeButton()
            )
            await msg.delete(delay=timeout)
