from typing import Union, Literal
import discord
from discord import app_commands as apc
from urllib.request import urlopen
import xmltodict


# List of supported currencies. Due to Discord limitations the maximum length is 25.
SUPPORTED_CURRENCIES = Literal[
    "AUD",
    "BGN",
    "BRL",
    "CAD",
    "CHF",
    "CNY",
    "CZK",
    "DKK",
    "EUR",
    "GBP",
    "HKD",
    "HUF",
    "IDR",
    "ILS",
    "ISK",
    "JPY",
    "KRW",
    "MXN",
    "NOK",
    "NZD",
    "PLN",
    "SEK",
    "THB",
    "TRY",
    "USD",
]


def _getrates() -> dict:
    """
    Fetch the most recent euro foreign exchange reference rates from the [European Central Bank](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml)
    and clean them up into a more easily accessed dictionary.
    """

    rates = {}

    # Open the XML file and parse it into a dictionary
    with urlopen(
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    ) as site:
        data = xmltodict.parse(site.read())
        rawrates = data["gesmes:Envelope"]["Cube"]["Cube"]["Cube"]

    # Clean up the parsed XML into a new dictionary
    for _ in rawrates:
        rates[_["@currency"]] = float(_["@rate"])

    rates["EUR"] = 1.0

    return rates


def _convertcurrency(amount: Union[int, float], original: str, target: str) -> float:
    """
    Do the conversion from currency to currency
    """

    rates = _getrates()
    original = original.upper()
    target = target.upper()

    # If we somehow get a currency that is not recognized, raise ValueError
    if original not in rates.keys() or target not in rates.keys():
        raise ValueError("Invalid currency code")

    # Convert from the original currency to EUR and then the target currency.
    truerate = rates[target] / rates[original]

    return amount * truerate


def _convertspeed(value: float, og: str, target: str) -> float:
    """
    Do the conversion from one unit of velocity to another
    """

    conversions = {"m/s": 1.0, "km/h": 3.6, "mph": 2.236936, "kn": 1.943844}

    result = conversions[target] / conversions[og]

    return value * result


def _convertlength(value: float, og: str, target: str) -> float:
    """
    Do the conversion from one unit of length to another
    """

    conversions = {
        "meters": 1.0,
        "inches": 1 / 0.0254,
        "feet": 1 / 0.3048,
        "yards": 1 / 0.9144,
        "miles": 1 / 1609.344,
    }

    result = conversions[target] / conversions[og]

    return value * result


class Convert(apc.Group):
    def __init__(self):
        super().__init__()

    @apc.command(name="currency", description="Valuuttamuunnos")
    @apc.rename(og="from", target="to")
    async def currency(
        self,
        ctx: discord.Interaction,
        amount: float,
        og: SUPPORTED_CURRENCIES,
        target: SUPPORTED_CURRENCIES,
    ):
        try:
            result = _convertcurrency(amount, og, target)
        except ValueError:
            await ctx.response.send_message("Tuntematon valuutta", ephemeral=True)
            return

        await ctx.response.send_message(
            content=f"{round(amount, 2)} {og} <-> {round(result, 2)} {target}"
        )

    @apc.command(name="velocity", description="Nopeusyksikön muunnos")
    @apc.rename(og="from", target="to")
    async def velocity(
        self,
        ctx: discord.Interaction,
        value: float,
        og: Literal["m/s", "km/h", "mph", "kn"],
        target: Literal["m/s", "km/h", "mph", "kn"],
    ):
        try:
            result = _convertspeed(value, og, target)
        except:
            await ctx.response.send_message("Jokin virhe tapahtui", ephemeral=True)
            return

        await ctx.response.send_message(
            content=f"{round(value, 6)} {og} <-> {round(result, 6)} {target}"
        )

    @apc.command(name="length", description="Nopeusyksikön muunnos")
    @apc.rename(og="from", target="to")
    async def length(
        self,
        ctx: discord.Interaction,
        value: float,
        og: Literal["meters", "inches", "feet", "yards", "miles"],
        target: Literal["meters", "inches", "feet", "yards", "miles"],
    ):
        try:
            result = _convertlength(value, og, target)
        except:
            await ctx.response.send_message("Jokin virhe tapahtui", ephemeral=True)
            return

        await ctx.response.send_message(
            content=f"{round(value, 6)} {og} <-> {round(result, 6)} {target}"
        )
