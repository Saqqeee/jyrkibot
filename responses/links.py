import discord
import validators
from urllib.parse import *

_whitelist = ["q", "t", "context"]


async def _dequery(queries: dict):
    allowed = {}

    for key, value in queries.items():
        if key in _whitelist:
            allowed[key] = value

    return allowed


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

            queriesfix = await _dequery(queries)

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
