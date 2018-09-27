#Standard Imports
import asyncio
import mysql.connector
import socket

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "1.0.0"
__author__ = "Crossedfall"

class GetNotes:
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
    @commands.group()
    async def setnotesdatabase(self,ctx):
        """
        SS13 MySQL databse settings
        """
        pass
    
    @setnotesdatabase.command()
    @checks.is_owner()
    async def host(self, ctx, db_host: str):
        """
        Sets the MySQL host, defaults to localhost (127.0.0.1)
        """
        try:
            socket.inet_aton(db_host)
            await self.config.guild(ctx.guild).mysql_host.set(db_host)
            await ctx.send(f"Database host set to: {db_host}")
        except(AttributeError, OSError):
            await ctx.send(f"{db_host} is not a valid ip address!")
    
    @setnotesdatabase.command()
    @checks.is_owner()
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
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535") 
    
    @setnotesdatabase.command(aliases=['name', 'user'])
    @checks.is_owner()
    async def username(self,ctx,user: str):
        """
        Sets the user that will be used with the MySQL database. Defaults to SS13

        It's recommended to ensure that this user cannot write to the database 
        """
        try:
            await self.config.guild(ctx.guild).mysql_user.set(user)
            await ctx.send(f"User set to: {user}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the username for your database.")
    
    @setnotesdatabase.command()
    @checks.is_owner()
    async def password(self,ctx,passwd: str):
        """
        Sets the password for connecting to the database

        This will be stored locally, it is recommended to ensure that your user cannot write to the database
        """
        try:
            await self.config.guild(ctx.guild).mysql_password.set(passwd)
            await ctx.send("Your password has been set.")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the password for your database.")

    @setnotesdatabase.command(aliases=["db"])
    @checks.is_owner()
    async def database(self,ctx,db: str):
        """
        Sets the database to login to, defaults to feedback
        """
        try:
            await self.config.guild(ctx.guild).mysql_db.set(db)
            await ctx.send(f"Database set to: {db}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send ("There was a problem setting your notes database.")
    
    @setnotesdatabase.command()
    @checks.admin_or_permissions(administrator=True)
    async def current(self,ctx):
        """
        Gets the current settings for the notes database
        """
        settings = await self.config.guild(ctx.guild).all()
        embed=discord.Embed(title="__Current settings:__")
        for k, v in settings.items():
            if k is not "mysql_password":
                embed.add_field(name=f"{k}:",value=v,inline=False)
            else:
                embed.add_field(name=f"{k}:",value="`redacted`",inline=False)
        await ctx.send(embed=embed)


    @checks.mod_or_permissions(administrator=True)
    @commands.group(autohelp=False)
    async def notes(self, ctx, player: str):
        """
        Gets the notes for a specific player
        """
        db = await self.config.guild(ctx.guild).mysql_db()
        db_host = await self.config.guild(ctx.guild).mysql_host()
        db_port = await self.config.guild(ctx.guild).mysql_port()
        db_user = await self.config.guild(ctx.guild).mysql_user()
        db_pass = await self.config.guild(ctx.guild).mysql_password()
        target = player.lower()
        cursor = None
        conn = None

        try:
            conn = mysql.connector.connect(host=db_host,port=db_port,database=db,user=db_user,password=db_pass)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SELECT timestamp, adminckey, text, type FROM messages WHERE targetckey='{target}'")
            rows = cursor.fetchall()

            embed=discord.Embed(title=f"Notes for: {target}", description=f"Total notes: {cursor.rowcount}", color=0xf1d592)
            for row in rows:
                embed.add_field(name=f'{row["timestamp"]} UTC-5 (Central Time) | {row["type"]} by {row["adminckey"]}',value=row["text"])
            await ctx.send(embed=embed)

        except():
            await ctx.send(f"There was an error getting the notes for {target}")
        finally:
            if cursor is not None:
                cursor.close()  
            if conn is not None:
                conn.close()