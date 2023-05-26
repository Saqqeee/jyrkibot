import discord
import validators
import urllib
import tldextract
from urllib.parse import *

dequery = ["twitter", "instagram", "spotify", "aliexpress"]


async def detracker(msg: discord.Message):
    """
    Link cleanup duty
    """

    badlinks = []

    # Split message content by whitespaces
    content = msg.content.split()

    # Check for valid URLs word for word
    for word in content:
        try:
            validators.url(word)
        except validators.ValidationFailure:
            continue
        else:
            url = urlparse(word)
            queries = parse_qs(url.query)

            # No point in continuing if there's nothing to clean up
            if not queries:
                continue

            site = tldextract.extract(url.hostname).domain

            if site in dequery:
                queriesfix = await detwitter(queries)
            elif site == "google":
                queriesfix = await degoogle(queries)
            else:
                queriesfix = await deutm(queries)

            # Don't continue if nothing was changed
            if queriesfix == queries:
                continue

            # Rebuild URL string and add it to the list of cleaned links
            queryfix = urlencode(queriesfix, quote_via=quote, doseq=True)
            urlfix = url._replace(query=queryfix)

            badlinks.append(urlunparse(urlfix))

    # Don't post anything if no link was cleaned
    if not badlinks:
        return

    # Format response message
    response = f"Linkkisi putsattuna: <{'>, <'.join(badlinks)}>"

    await msg.reply(content=response, mention_author=False)


### SEPARATE QUERY MANIPULATION FUNCTIONS FOR DIFFERENT WEBSITES


async def detwitter(queries: dict):
    """Remove everything"""
    return {}


async def degoogle(queries: dict):
    """Remove all but the query itself"""
    result = {"q": queries["q"]}
    return result


async def deutm(queries: dict):
    """Remove UTM parameters"""

    utm_params = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]
    result = {}

    for key, value in queries.items():
        if key not in utm_params:
            result[key] = value

    return result
