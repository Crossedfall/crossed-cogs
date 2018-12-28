#Standard Imports
import asyncio
import mysql.connector
import ipaddress

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "1.0.0"
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class GetNotes(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3257143194, force_registration=True)

        default_guild = {
            "mysql_host": "127.0.0.1",
            "mysql_port": 3306,
            "mysql_user": "ss13",
            "mysql_password": "password",
            "mysql_db": "feedback",
            "admin_ckey": {}
        }

        self.config.register_guild(**default_guild)
    
    @commands.guild_only()
    @commands.group()
    async def setnotes(self,ctx): 
        """
        SS13 MySQL database settings
        """
        pass
    
    @setnotes.command()
    @checks.is_owner()
    async def host(self, ctx, db_host: str):
        """
        Sets the MySQL host, defaults to localhost (127.0.0.1)
        """
        try:
            ipaddress.ip_address(db_host) # Confirms that the IP provided is valid. If the IP is not valid, a ValueError is thrown.
            await self.config.guild(ctx.guild).mysql_host.set(db_host)
            await ctx.send(f"Database host set to: {db_host}")
        except(ValueError):
            await ctx.send(f"{db_host} is not a valid ip address!")
    
    @setnotes.command()
    @checks.is_owner()
    async def port(self, ctx, db_port: int):
        """
        Sets the MySQL port, defaults to 3306
        """
        try:
            if 1024 <= db_port <= 65535: # We don't want to allow reserved ports to be set
                await self.config.guild(ctx.guild).mysql_port.set(db_port)
                await ctx.send(f"Database port set to: {db_port}")
            else:
                await ctx.send(f"{db_port} is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535") 
    
    @setnotes.command(aliases=['name', 'user'])
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
    
    @setnotes.command()
    @checks.is_owner()
    async def password(self,ctx,passwd: str):
        """
        Sets the password for connecting to the database

        This will be stored locally, it is recommended to ensure that your user cannot write to the database
        """
        try:
            await self.config.guild(ctx.guild).mysql_password.set(passwd)
            await ctx.send("Your password has been set.")
            try:
                await ctx.message.delete()
            except(discord.DiscordException):
                await ctx.send("I do not have the required permissions to delete messages, please remove/edit the password manually.")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the password for your database.")

    @setnotes.command(aliases=["db"])
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
    
    @setnotes.command()
    @checks.admin_or_permissions(administrator=True)
    async def current(self,ctx):
        """
        Gets the current settings for the notes database
        """
        settings = await self.config.guild(ctx.guild).all()
        embed=discord.Embed(title="__Current settings:__")
        for k, v in settings.items():
            if k is not "admin_ckey":
                if k is not "mysql_password": # Ensures that the database password is not sent
                    embed.add_field(name=f"{k}:",value=v,inline=False)
                else:
                    embed.add_field(name=f"{k}:",value="`redacted`",inline=False)
        await ctx.send(embed=embed)
    
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    @commands.group(autohelp=False)
    async def registerckey(self, ctx, ckey: str):
        """
        Allows admins to register their ckey and perform admin actions from discord
        """
        admins = await self.config.guild(ctx.guild).admin_ckey()
        if ckey in admins:
            await ctx.send("Ckey already registered!")
        else:
            if ctx.message.author.id not in admins.values():
                admins[ckey] = ctx.message.author.id
                await ctx.send(f"Your ckey has been set to: `{ckey}`")
                await self.config.guild(ctx.guild).admin_ckey.set(admins)
            else:
                await ctx.send("You already have a ckey registered to your user!")

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def notes(self, ctx, player: str):
        """
        Gets the notes for a specific player
        """
        query = f"SELECT timestamp, adminckey, text, type FROM messages WHERE targetckey='{player.lower()}'"
        message = await ctx.send("Getting player notes...")

        try:
            rows = await self.query_database(ctx, query)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            embed=discord.Embed(title=f"Notes for: {player}", description=f"Total notes: {len(rows)}", color=0xf1d592)
            for row in rows:
                embed.add_field(name=f'{row["timestamp"]} UTC-5 (Central Time) | {row["type"]} by {row["adminckey"]}',value=row["text"])
            await message.edit(content=None,embed=embed)
        
        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up notes for: {player}", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")


    async def query_database(self, ctx, query: str):
        # Database options loaded from the config
        db = await self.config.guild(ctx.guild).mysql_db()
        db_host = await self.config.guild(ctx.guild).mysql_host()
        db_port = await self.config.guild(ctx.guild).mysql_port()
        db_user = await self.config.guild(ctx.guild).mysql_user()
        db_pass = await self.config.guild(ctx.guild).mysql_password()

        cursor = None # Since the cursor/conn variables can't actually be closed if the connection isn't properly established we set a None type here
        conn = None # ^

        try:
            # Establish a connection with the database and pull the relevant data
            conn = mysql.connector.connect(host=db_host,port=db_port,database=db,user=db_user,password=db_pass, connect_timeout=2)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()

            return rows
        
        except:
            raise 

        finally:
            if cursor is not None:
                cursor.close()  
            if conn is not None:
                conn.close()