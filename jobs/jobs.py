import threading
import asyncio
from datetime import datetime
from jobs.tasks import calculate_bacs, lotterydraw, sound_alarms, cache_config


async def tasks(client):
    """
    Loops until program termination
    """
    while True:
        date = datetime.now()

        # Once per minute
        await lotterydraw.draw(date, client)
        await sound_alarms.alarm(date, client)

        # Once per five minutes
        if date.minute % 5 == 0:
            await sound_alarms.snooze(date, client)

        # Once per six minutes
        if date.minute % 6 == 0:
            await calculate_bacs.calculate_bacs()

        # Refresh config every half hours
        if date.minute % 30 == 0:
            await cache_config.config.refreshconfig()

        # Backup config every three hours
        if date.hour % 3 == 0:
            await cache_config.config.backup()

        # Sleep for a minute
        await asyncio.sleep(60)


async def startjobs(client):
    thread = threading.Thread(target=await tasks(client), daemon=True)
    thread.start()
