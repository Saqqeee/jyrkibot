import discord
from discord import app_commands as apc
from typing import Literal
from fmiopendata.wfs import download_stored_query
from datetime import datetime, timedelta
import pytz
from jobs.database import engine, Users
from sqlalchemy.orm import Session
from sqlalchemy import select
from math import isnan


async def _getweatherdata(
    querystring: str, parameters: str, place: str, time: Literal["24h", "3d", "now"]
):
    """
    Get weather data from FMI

    Parameters
    ----------
    place: `str`
        The place (city etc.) to get the data for
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
    if time == "3d":
        endtime = starttime + timedelta(hours=60)
        timestep = "360"
    if time == "now":
        endtime = None
        starttime -= timedelta(hours=1)
        timestep = None

    query = download_stored_query(
        querystring,
        args=[
            f"place={place}",
            f"parameters={parameters}",
            f"starttime={starttime}",
            f"endtime={endtime}" if endtime else "",
            f"timestep={timestep}" if timestep else "",
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
        self.forecastparams = (
            "Temperature,WindSpeedMS,WindDirection,PrecipitationAmount"
        )
        self.forecaststring = (
            "fmi::forecast::harmonie::surface::point::multipointcoverage"
        )
        self.currentweatherstring = "fmi::observations::weather::multipointcoverage"
        self.currentweatherparams = (
            "t2m,ws_10min,wg_10min,wd_10min,rh,r_1h,ri_10min,snow_aws,n_man,wawa"
        )

    @apc.command(
        name="forecast",
        description="Sääennuste haluamallesi paikkakunnalle Pohjoismaiden alueella",
    )
    @apc.describe(
        place="Haluamasi paikannimi", timespan="Kuinka pitkän ajan ennusteen haluat"
    )
    async def forecast(
        self,
        ctx: discord.Interaction,
        place: str,
        timespan: Literal["24h", "3d"] = "24h",
    ):
        forecastdata = await _getweatherdata(
            self.forecaststring, self.forecastparams, place, timespan
        )

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

    @apc.command(name="current", description="Tämän hetkinen sää Suomen alueella")
    @apc.describe(place="Paikannimi")
    async def currentweather(self, ctx: discord.Interaction, place: str):
        weatherdata = await _getweatherdata(
            self.currentweatherstring, self.currentweatherparams, place, "now"
        )

        # If weather data is not found, send an error message and return
        if not weatherdata.data:
            await ctx.response.send_message(
                content=f"Säätä ei löytynyt paikalle {place.title()}",
                ephemeral=True,
            )
            return

        # Get the latest readings
        timekey: datetime = max(weatherdata.data.keys())
        timeddata = weatherdata.data[timekey]
        locationname = list(timeddata.keys())[0]
        weathervalues = timeddata[locationname]

        # Set variables
        temp = weathervalues["Air temperature"]["value"]
        windarrow = await _getwindarrow(weathervalues["Wind direction"]["value"])
        windspeed = weathervalues["Wind speed"]["value"]
        windgust = weathervalues["Gust speed"]["value"]
        rainintensity = weathervalues["Precipitation intensity"]["value"]
        humidity = weathervalues["Relative humidity"]["value"]
        snowdepth = weathervalues["Snow depth"]["value"]
        cloudamount = weathervalues["Cloud amount"]["value"]
        cloudstrings = {
            0.0: "Selkeää",
            1.0: "Melkein selkeää",
            2.0: "Melkein selkeää",
            3.0: "Puolipilvistä",
            4.0: "Puolipilvistä",
            5.0: "Puolipilvistä",
            6.0: "Melkein pilvistä",
            7.0: "Melkein pilvistä",
            8.0: "Pilvistä",
        }

        # Initialize response embed
        embed = discord.Embed(
            color=discord.Color.dark_magenta(),
            title=f"Sää kohteessa {locationname}",
            timestamp=pytz.timezone("Europe/Helsinki").fromutc(timekey),
        )

        # Add fields to embed one by one
        if not isnan(temp):
            embed.add_field(
                name="\U0001F321 Lämpötila",
                value=f"{temp} {chr(176)}C",
                inline=True,
            )
        if not isnan(windspeed):
            embed.add_field(
                name="\U0001F4A8 Tuuli",
                value=f"{windarrow} {windspeed} ({windgust}) m/s",
                inline=True,
            )
        if not isnan(rainintensity):
            embed.add_field(
                name="\U0001F327 Sade", value=f"{rainintensity} mm", inline=True
            )
        if not isnan(humidity):
            embed.add_field(
                name="\U0001F4A6 Kosteus", value=f"{humidity} %", inline=True
            )
        if not isnan(cloudamount):
            embed.add_field(
                name="\U00002601 Pilvisyys",
                value=f"{cloudstrings[cloudamount]} ({int(cloudamount)}/8)",
            )
        if snowdepth > 0:
            embed.add_field(
                name="\U00002744 Lumensyvyys", value=f"{snowdepth} cm", inline=True
            )

        # If the embed would be empty, send an error message instead
        if not embed.fields:
            await ctx.response.send_message(
                content=f"Kohteelle {locationname} ei löydetty tuoretta säädataa",
                ephemeral=True,
            )
            return

        await ctx.response.send_message(embed=embed)
