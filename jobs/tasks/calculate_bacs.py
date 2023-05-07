import sqlite3

async def calculate_bacs():
    con = sqlite3.connect("data/database.db")
    db = con.cursor()
    db.execute("UPDATE Alcoholist SET bac=(bac-0.0015) WHERE bac>=0.0015")
    db.execute("UPDATE Alcoholist SET bac=0 WHERE bac BETWEEN 0 AND 0.0015")
    con.commit()
    con.close()