import threading
import asyncio
from datetime import datetime
from slashcommands import lottery

async def tasks(client):
    timer = 0
    while True:
        date = datetime.now()
        
        await lottery.draw(date, client)

        if timer < 1440:
            timer += 1
        else: timer = 0
        await asyncio.sleep(60)

async def startjobs(client):
    thread = threading.Thread(target=await tasks(client), daemon=True)
    thread.start()