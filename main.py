import discord
import json
import os
import logging
from datetime import datetime
handler = logging.FileHandler(filename='loki.log', encoding='utf-8', mode='w')

if os.path.isfile("cfg/cfg.json"):
    pass
else:
    data = {
        'TOKEN': input("Your Discord app's auth token: ")
    }
    with open("cfg/cfg.json", "w") as confile:
        json.dump(data, confile)
with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
token = config["TOKEN"]

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

client.run(token, log_handler=handler)