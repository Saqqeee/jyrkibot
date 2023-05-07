import threading
import asyncio
from datetime import datetime
from jobs.tasks import calculate_bacs, lotterydraw

async def tasks(client):
    timer = 0
    while True:
        date = datetime.now()
        
        # Once per minute
        await lotterydraw.draw(date, client)

        # Once per six minutes
        if timer%6==0:
            await calculate_bacs.calculate_bacs()

        if timer < 1339:
            timer += 1
        else: timer = 0
        await asyncio.sleep(60)

async def startjobs(client):
    thread = threading.Thread(target=await tasks(client), daemon=True)
    thread.start()