#Standard Imports
import asyncio
import aiohttp
import mysql.connector
import socket

#Discord Imports
from redbot.core import commands, checks, Config, utils

__version__ = "0.0.1"
__author__ = "Crossedfall"

def is_admin():
    """
    check for administrator/owner perms
    """
    async def pred(ctx: commands.Context):
        author = ctx.author
        if await ctx.bot.is_owner(author):
            return True
        else:
            return author == ctx.guild.owner or author.guild.permissions.administrator

    return commands.check(pred)

class SS13:
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257143194, force_registration=True)

        default_guild = {
            "mysql_host": "127.0.0.1",
            "mysql_port": 3306,
            "mysql_user": "ss13",
            "mysql_password": "password",
            "mysql_db": "feedback"
        }

        self.config.register_guild(**default_guild)
    
    @commands.guild_only()
    @is_admin()
    @commands.group(autohelp=True)
    async def setdatabase(self,ctx):
        """
        SS13 MySQL databse settings
        """
        pass
    
    @setdatabase.command()
    @is_admin()
    async def host(self, ctx, db_host: str):
        """
        Sets the MySQL host, defaults to localhost (127.0.0.1)
        """
        try:
            socket.inet_aton(db_host)
            await self.config.guild(ctx.guild).mysql_host.set(db_host)
            await ctx.send(f"Database host set to: {db_host}")
        except:
            await ctx.send(f"{db_host} is not a valid ip address!")
    
    @setdatabase.command()
    @is_admin()
    async def port(self, ctx, db_port: int):
        """
        Sets the MySQL port, defaults to 3306
        """
        try:
            if 1024 <= db_port <= 65535:
                await self.config.guild(ctx.guild).mysql_port.set(db_port)
                await ctx.send(f"Database port set to: {db_port}")
            else:
                await ctx.send(f"{db_port} is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            pass 
    
    @setdatabase.command()
    @is_admin()
    async def username(self,ctx,user: str):
        """
        Sets the user that will be used with the MySQL database. Defaults to SS13

        It's recommended to ensure that this user cannot write to the database 
        """
        try:
            await self.config.guild(ctx.guild).mysql_user.set(user)
            await ctx.send(f"User set to: {user}")
        except (ValueError, KeyError, AttributeError):
            pass
    
    @setdatabase.command()
    @is_admin()
    async def password(self,ctx,passwd: str):
        """
        Sets the password for connecting to the database

        This will be stored locally, it is recommended to ensure that your user cannot write to the database
        """
        try:
            await self.config.guild(ctx.guild).mysql_user.set(passwd)
            await ctx.send("Your password has been set.")
        except (ValueError, KeyError, AttributeError):
            pass

    @setdatabase.command()
    @is_admin()
    async def database(self,ctx,db: str):
        """
        Sets the database to login to, defaults to feedback
        """
        try:
            await self.config.guild(ctx.guild).mysql_db.set(db)
            await ctx.send(f"Database set to: {db}")
        except (ValueError, KeyError, AttributeError):
            pass
