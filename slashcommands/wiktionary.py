import discord
import langcodes
import language_data
from bs4 import BeautifulSoup
from discord import app_commands as apc
from mediawiki import MediaWiki, MediaWikiPage, VERSION, exceptions


class Wiktionary(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.lang = langcodes.Language.get("fi")
        self.mwa = MediaWiki(
            url=f"https://{self.lang}.wiktionary.org/w/api.php",
            lang=self.lang.language,
            user_agent=f"jyrkibot/0.1 (https://github.com/Saqqeee) pymediawiki/{VERSION}",
        )

    async def fetch_page(self, title: str, lang: str):
        """
        Make a MediaWiki API request for a Wiktionary page.

        ### Args:
        title `str`:
            The title of the page to look for.
        lang `str`:
            The preferred language of Wiktionary.

        Returns a tuple containing the MediaWikiPage object and the page URL
        """

        # Convert arguments into lowercase
        title = title.lower()
        lang = langcodes.Language.get(lang)

        # Update the language setting if it differs from the previous one
        if lang != self.lang:
            self.lang = lang

        # Assign variables: data for the MediaWikiPage result, url for the page URL
        data = self.mwa.page(title=title)
        url = f"https://{self.lang.language}.wiktionary.org/wiki/{data.title}"

        return data, url

    @apc.command(name="definition", description="Käytä sanakirjaa")
    async def wiktionary(
        self,
        ctx: discord.Interaction,
        title: str,
        # TODO: Find a neat way to give the user more language choices without cluttering up the code with endless lists
        ## TODO part 2: This could possibly now be easily done using langcodes
    ):
        """
        Get the Wiktionary page and return key info

        ### Args:
        ctx `discord.Interaction`:
            The Interaction returned by Discord
        title `str`:
            The title of the article to parse
        """

        # Defer the response by sending a "thinking..." message.
        # This is done to avert the 3 second timeout in interaction responses,
        # in case the API takes a long time to answer
        await ctx.response.defer(thinking=True)

        # Get the Wiktionary page
        try:
            data: MediaWikiPage
            data, url = await self.fetch_page(title, self.lang.language)

        except exceptions.PageError:
            # What to do if no page is found with the given title
            await ctx.followup.send(content=f"Sivua ei löytynyt otsikolla {title}.")
            return

        # Initialize followup embed
        embed = discord.Embed(
            title=data.title, color=discord.Color.dark_magenta(), url=url
        )

        # Parse the returned HTML and define the tags to look for
        parsed = BeautifulSoup(data.html, "html.parser")
        tags = parsed(["h2", "h3", "h4", "ol"])

        # Define empty variables for embed field title and content
        title = ""
        cont = ""
        firstfound = False

        for tag in tags:
            tag: BeautifulSoup
            # If we have a title and value for an embed field and we're already at the next heading,
            # add the field to the embed and reset the variables
            if title and cont and (tag.name in ["h2", "h3", "h4"]):
                embed.add_field(name=title, value=cont)
                title = ""
                cont = ""

            # Instantly continue if we're at a tag we don't care about
            if (
                tag.has_attr("id") and tag["id"] == "mw-toc-heading"
            ) or tag.name == "h4":
                continue

            if tag.name == "h2":
                # If we arrive at a second language heading, break the loop
                if firstfound:
                    break

                # If the language heading is the first one, set our language as found and
                # set the embed description to communicate it
                if langcodes.Language.get(
                    langcodes.Language.find(tag.span["id"])
                ).is_valid():
                    embed.description = tag.find(
                        "span", {"class": "mw-headline"}
                    ).string
                    firstfound = True
                    continue

            # <h3> tags define the parts of speech, so these become the embed field titles.
            # This assumes that a <h3> tag will be instantly followed by an ordered list.
            if tag.name == "h3":
                title = tag.span.string
                continue

            # When an ordered list is found, set the index variable to 1 and iterate the list contents.
            if tag.name == "ol":
                i = 1
                # We only care about list items at this point, so whenever one is found, look at its contents
                for subtag in tag.contents:
                    if subtag.name == "li":
                        # Add index to the field content string and increment by one
                        cont += f"\n{i}. "
                        i += 1
                        # Handle the contents of the list item element separately because of formatting stuff
                        x = subtag.contents
                        for part in x:
                            string = ""
                            # Is the item a string or a HTML tag?
                            try:
                                part.name

                            # If it is a string, add it as itself. If it is NoneType, add an empty string.
                            except AttributeError:
                                string = part or ""

                            # What to do if it is a HTML tag
                            else:
                                # If if is a description list (used for quotes and examples in Wiktionary),
                                # add the items separately as indented blockquotes
                                if part.name == "dl":
                                    for dd in part.contents:
                                        text = dd.get_text().rstrip()
                                        if not text:
                                            continue
                                        string += f"\n    > *{text}*"
                                    cont += string
                                    continue

                                # In any other case, just add the text content of the tag.
                                else:
                                    string = part.string or ""
                            cont += string.rstrip("\n")

        # Add a final field if the loop runs out. It doesn't matter if this is empty,
        # however if nothing comes after our final field, this line is necessary.
        embed.add_field(name=title, value=cont)

        await ctx.followup.send(embed=embed)
