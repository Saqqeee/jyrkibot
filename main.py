import discord
import dotenv
import os
import logging
from datetime import datetime
handler = logging.FileHandler(filename='loki.log', encoding='utf-8', mode='w')
dotenv.load_dotenv()
token = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync()
    print("Commands synced")

## Responds with "Go to work regards Jyrki" if
## someone wakes up at an unreasonable time
@client.event
async def on_message(msg):
    if msg.author == client.user:
        return
    if msg.content.lower() == "huomenta":
        aika = int(datetime.now().strftime("%H"))
        if aika <= 4 or aika >= 11:
            await msg.channel.send("Mene töihin terv. Jyrki.")

## Sends a picture of Jyrki when requested
@tree.command(name="jyrki", description="Jyrki")
async def _jyrki(ctx):
    await ctx.response.send_message(file=discord.File("media/jyrki.png"))

client.run(token, log_handler=handler)