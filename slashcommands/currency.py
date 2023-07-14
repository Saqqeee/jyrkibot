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


def _convert(amount: Union[int, float], original: str, target: str) -> float:
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


class Currency(apc.Group):
    def __init__(self):
        super().__init__()

    @apc.command(name="convert", description="Valuuttamuunnos")
    @apc.rename(og="from", target="to")
    async def convert(
        self,
        ctx: discord.Interaction,
        amount: float,
        og: SUPPORTED_CURRENCIES,
        target: SUPPORTED_CURRENCIES,
    ):
        try:
            result = _convert(amount, og, target)
        except ValueError:
            await ctx.response.send_message("Tuntematon valuutta", ephemeral=True)
            return

        await ctx.response.send_message(content=f"{amount} {og} <-> {result} {target}")
