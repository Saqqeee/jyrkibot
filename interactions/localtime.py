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

    if not tz:
        tz = "Europe/Helsinki"

    time = datetime.now(tz=pytz.timezone(tz))

    await ctx.response.send_message(content=f"Time in {tz}: {time}")
