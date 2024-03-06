import discord
from discord import app_commands as apc
from jobs.database import Users, engine
from sqlalchemy import select
from sqlalchemy.orm import Session
import pytz
from datetime import datetime


@apc.context_menu(name="Local time")
async def localtime(ctx: discord.Interaction, member: discord.Member):
    with Session(engine) as db:
        tz = db.scalar(select(Users.timezone).where(Users.id == member.id))

    msg: str
    if not tz:
        msg = f"{member.display_name} has not set their time zone"
    else:
        time = datetime.now(tz=pytz.timezone(tz)).strftime("%H:%M on %A (UTC %z)")
        msg = f"Time for {member.display_name} in {tz}: {time}"

    await ctx.response.send_message(content=msg, ephemeral=True)
