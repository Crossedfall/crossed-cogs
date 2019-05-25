#Standard Imports
import asyncio
import mysql.connector
import socket
import ipaddress
from typing import Union

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
            await self.config.guild(ctx.guild).mysql_host.set(db_host)
            await ctx.send(f"Database host set to: {db_host}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the database's ip/hostname. Please check your entry and try again!")
    
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
    @commands.command()
    async def notes(self, ctx, player: str):
        """
        Gets the notes for a specific player
        """
        query = f"SELECT timestamp, adminckey, text, type FROM messages WHERE targetckey='{player.lower()}' ORDER BY timestamp DESC"
        message = await ctx.send("Getting player notes...")

        try:
            rows = await self.query_database(ctx, query)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            embed=discord.Embed(title=f"Notes for: {player}", description=f"Total notes: {len(rows)}", color=0xf1d592)
            for row in rows:
                embed.add_field(name=f'{row["timestamp"]} UTC-5 (Central Time) | {row["type"]} by {row["adminckey"]}',value=row["text"], inline=False)
            await message.edit(content=None,embed=embed)
        
        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up notes for: {player}", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")
    
    async def player_search(self, ctx, ip = None, ckey = None, cid = None) -> dict:
        """
        Runs multiple database queries to obtain the player's information
        """
        try:
            # First query is determined by the identifier given 
            if ip:
                #IPs are stored as a 32 bit integer in the databse. We need to convert it before doing the query.
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM player WHERE ip='{int(ipaddress.IPv4Address(ip))}'"
                query = await self.query_database(ctx, query)
            elif ckey:
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM player WHERE ckey='{ckey}'"
                query = await self.query_database(ctx, query)
            elif cid:
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM player WHERE computerid='{cid}'"
                query = await self.query_database(ctx, query)

            results = {}
            try:
                query = query[0] # Checks to see if a player was found, if the list is empty nothing was found so we return the empty dict.
            except IndexError:
                return results
            results['ip'] = ipaddress.IPv4Address(query['ip']) #IP's are stored as a 32 bit integer, converting it for readability
            results['cid'] = query['computerid']
            results['ckey'] = query['ckey']
            results['first'] = query['firstseen']
            results['last'] = query['lastseen']
            results['join'] = query['accountjoindate']

            #Obtain the number of total connections
            query = f"SELECT COUNT(*) FROM connection_log WHERE ckey='{results['ckey']}'"
            query = await self.query_database(ctx, query)
            results['num_connections'] = query[0]['COUNT(*)']

            #Obtain the number of bans and, if applicable, the last ban
            query = f"SELECT bantime FROM ban WHERE ckey='{results['ckey']}' ORDER BY bantime DESC"
            query = await self.query_database(ctx, query)
            results['num_bans'] = len(query)
            if results['num_bans'] > 0:
                results['latest_ban'] = list(query[0].values())[0]
            else:
                results['latest_ban'] = None

            #Obtain the total number of notes
            query = f"SELECT COUNT(*) FROM messages WHERE targetckey='{results['ckey']}'"
            query = await self.query_database(ctx, query)
            results['notes'] = query[0]['COUNT(*)']

            return results

        except:
            raise
        

    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def findplayer(self, ctx, *,player: Union[ipaddress.IPv4Address, int, str] = None):
        """
        Obtains information about a specific player.

        Will search for players using a provided IP, CID, or CKEY. 
        """

        try:
            message = await ctx.send("Looking up player....")
            async with ctx.typing():

                if type(player) is ipaddress.IPv4Address:
                    player = await self.player_search(ctx, ip=player)
                elif type(player) is int:
                    player = await self.player_search(ctx, cid=player)
                elif type(player) is str:
                    player = await self.player_search(ctx, ckey=player)
                else:
                    await message.edit(content="That doesn't look like an IP, CID, or CKEY. Please check your entry and try again!")
                    return

            if player:
                embed=discord.Embed(color=await ctx.embed_color())

                embed.add_field(name="__Identity:__",value=f"**CKEY**: {player['ckey']}\n**CID**: {player['cid']}\n**IP**: {player['ip']}\n**Account Join Date**: {player['join']}", inline=False)                    
                embed.add_field(name="__Connection Information:__", value=f"**First Seen**: {player['first']}\n**Last Seen**: {player['last']}\n**Number of Connections**: {player['num_connections']}", inline=False)
                embed.add_field(name="__Bans/Notes:__", value=f"**Number of Notes**: {player['notes']}\n**Number of Bans**: {player['num_bans']}\n**Last Ban**: {player['latest_ban']}", inline=False)

                await message.edit(content=None, embed=embed)

                # After 5-minutes redact the player's CID and IP.
                await asyncio.sleep(300)
                embed.clear_fields()
                embed.add_field(name="__Identity:__",value=f"**CKEY**: {player['ckey']}\n**CID**: `[Redacted]`\n**IP**: `[Redacted]`\n**Account Join Date**: {player['join']}", inline=False)                    
                embed.add_field(name="__Connection Information:__", value=f"**First Seen**: {player['first']}\n**Last Seen**: {player['last']}\n**Number of connections**: {player['num_connections']}", inline=False)
                embed.add_field(name="__Bans/Notes:__", value=f"**Number of notes**: {player['notes']}\n**Number of Bans**: {player['num_bans']}\n**Last Ban**: {player['latest_ban']}", inline=False)

                await message.edit(content=None, embed=embed)
            else:
                await message.edit(content="No results found.")

        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up player", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
            return
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")
            return          
        

    async def query_database(self, ctx, query: str):
        # Database options loaded from the config
        db = await self.config.guild(ctx.guild).mysql_db()
        db_host = socket.gethostbyname(await self.config.guild(ctx.guild).mysql_host())
        db_port = await self.config.guild(ctx.guild).mysql_port()
        db_user = await self.config.guild(ctx.guild).mysql_user()
        db_pass = await self.config.guild(ctx.guild).mysql_password()

        cursor = None # Since the cursor/conn variables can't actually be closed if the connection isn't properly established we set a None type here
        conn = None # ^

        try:
            # Establish a connection with the database and pull the relevant data
            conn = mysql.connector.connect(host=db_host,port=db_port,database=db,user=db_user,password=db_pass, connect_timeout=5)
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