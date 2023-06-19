import discord
from discord import app_commands as apc
from typing import Literal
from fmiopendata.wfs import download_stored_query
from datetime import datetime, timedelta
import pytz
from jobs.database import engine, Users
from sqlalchemy.orm import Session
from sqlalchemy import select


async def _getforecast(place: str, parameters: str, time: Literal["24h", "3d"]):
    """
    Get forecast data from FMI

    Parameters
    ----------
    place: `str`
        The place (city etc.) to get the forecast for
    parameters: `str`
        A comma-separated list in string form of weather parameters to query for: `"Temperature,WindSpeedMS,WindDirection,PrecipitationAmount"`
    time: `Literal['24h', '3d']`
        How long of a timespan to get forecast data for
    """

    # Set start and end times for the query as well as timestep according to the end time chosen
    # 24h forecast -> 1 hour timestep
    # 3d forecast -> 3 hour timestep
    starttime = datetime.utcnow()
    if time == "24h":
        endtime = starttime + timedelta(hours=24)
        timestep = "180"
    elif time == "3d":
        endtime = starttime + timedelta(hours=60)
        timestep = "360"

    query = download_stored_query(
        "fmi::forecast::harmonie::surface::point::multipointcoverage",
        args=[
            f"place={place}",
            f"parameters={parameters}",
            f"starttime={starttime}",
            f"endtime={endtime}",
            f"timestep={timestep}",
        ],
    )

    return query


async def _getwindarrow(angle):
    arrowangles = {
        "\U00002191": [-22.5, 22.5],
        "\U00002197": [22.5, 67.5],
        "\U00002192": [67.5, 112.5],
        "\U00002198": [112.5, 157.5],
        "\U00002193": [157.5, 202.5],
        "\U00002199": [202.5, 247.5],
        "\U00002190": [247.5, 292.5],
        "\U00002196": [292.5, 337.5],
    }
    if angle > 337.5:
        angle -= 360
    for key, value in arrowangles.items():
        if angle >= value[0] and angle < value[1]:
            return key


class Weather(apc.Group):
    def __init__(self):
        super().__init__()
        self.qparams = "Temperature,WindSpeedMS,WindDirection,PrecipitationAmount"

    @apc.command(name="forecast", description="Sääennuste haluamallesi paikkakunnalle")
    @apc.describe(
        place="Haluamasi paikannimi", timespan="Kuinka pitkän ajan ennusteen haluat"
    )
    async def forecast(
        self,
        ctx: discord.Interaction,
        place: str,
        timespan: Literal["24h", "3d"] = "24h",
    ):
        forecastdata = await _getforecast(place, self.qparams, timespan)

        # If forecast data is not found, send an error message and return
        if not forecastdata.data:
            await ctx.response.send_message(
                content=f"Sääennustetta ei löytynyt paikalle {place.title()}",
                ephemeral=True,
            )
            return

        # Get user timezone
        with Session(engine) as db:
            usertz = (
                db.scalar(select(Users.timezone).where(Users.id == ctx.user.id))
                or "Europe/Helsinki"
            )
        timeformat = "%d.%m. %H:%M"

        # Initialize the response embed
        embed = discord.Embed(
            color=discord.Color.dark_magenta(),
            title=f"Sääennuste paikalle {place.title()}",
            timestamp=datetime.now(pytz.timezone(usertz)),
            description=f"{timespan} ennuste, aikavyöhyke {usertz}",
        )

        # Iterate the dictionary
        for time, data in forecastdata.data.items():
            time: datetime
            timestamp = pytz.timezone(usertz).fromutc(time).strftime(timeformat)

            data: dict = data[place.title()]
            temp = data["Air temperature"]["value"]
            windarrow = await _getwindarrow(data["Wind direction"]["value"])
            wind = data["Wind speed"]["value"]
            rain = data["Precipitation amount"]["value"]

            fieldvalue = f"\U0001F321 {temp} {chr(176)}C | {windarrow} {wind} m/s | \U0001F327 {rain} mm"

            embed.add_field(name=timestamp, value=fieldvalue, inline=False)

        await ctx.response.send_message(embed=embed)
