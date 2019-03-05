#Standard Imports
import asyncio
import mysql.connector
import ipaddress

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "0.0.1"
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class NoteKeeper(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3657648194, force_registration=True)