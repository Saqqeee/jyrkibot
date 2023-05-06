import discord
from discord import app_commands as apc
import json
import random
import sqlite3

with open("cfg/cfg.json", "r") as confile:
    config = json.load(confile)
owner = config["owner"]

class Lottery(apc.Group):
    def __init__(self, client):
        super().__init__()
        self.client = client