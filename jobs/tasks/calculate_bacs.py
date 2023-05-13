from sqlalchemy import update
from sqlalchemy.orm import Session
from jobs.database import engine, Alcoholist


async def calculate_bacs():
    with Session(engine) as db:
        db.execute(
            update(Alcoholist)
            .where(Alcoholist.bac >= 0.015)
            .values(bac=(Alcoholist.bac - 0.015))
        )
        db.execute(
            update(Alcoholist)
            .where(0.0 < Alcoholist.bac, 0.015 > Alcoholist.bac)
            .values(bac=0)
        )
        db.commit()
