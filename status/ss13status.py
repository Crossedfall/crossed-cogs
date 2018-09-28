#Standard Imports
import asyncio
import aiohttp
import mysql.connector
import socket
import ipaddress

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "0.0.1"
__author__ = "Crossedfall"

class SS13Status:

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257193194, force_registration=True)

        default_guild = {
            "server": "127.0.0.1",
            "game_port": 7777,
            #"comms_key": "secret",
        }

        self.config.register_guild(**default_guild)
    
    @commands.guild_only()
    @commands.group()
    async def setstatus(self, ctx):
        """
        Configuration group for the SS13 status command
        """
        pass
    
    @setstatus.command(aliases=['host'])
    @checks.is_owner()
    async def server(self, ctx, host: str):
        """
        Sets the server IP used for status checks
        """
        pass
    
    @setstatus.command()
    @checks.is_owner()
    async def port(self, ctx, post: int):
        """
        Sets the port used for the status checks
        """
        pass
    
    @setstatus.command()
    @checks.admin_or_permissions(administrator=True)
    async def current(self, ctx):
        """
        Lists the current settings
        """
        pass

    @commands.guild_only()
    @commands.command()
    async def status(self, ctx):
        """
        Gets the current server status and round details
        """
        pass

    