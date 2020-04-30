#Standard Imports
import asyncio
import mysql.connector
import socket
import ipaddress
import re
from typing import Union

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import pagify, box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

#Util Imports
from .util import key_to_ckey

__version__ = "1.1.0"
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
            "mysql_prefix": "",
            "currency_name": "Currency",
            "admin_ckey": {} #Future thing, not currently used
        }

        self.config.register_guild(**default_guild)
    

    @commands.guild_only()
    @commands.group()
    @checks.admin_or_permissions(administrator=True)
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
            await ctx.send(f"Database host set to: `{db_host}`")
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
                await ctx.send(f"Database port set to: `{db_port}`")
            else:
                await ctx.send(f"{db_port} is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535") 
    

    @setnotes.command(aliases=['name', 'user'])
    @checks.is_owner()
    async def username(self, ctx, user: str):
        """
        Sets the user that will be used with the MySQL database. Defaults to SS13

        It's recommended to ensure that this user cannot write to the database 
        """
        try:
            await self.config.guild(ctx.guild).mysql_user.set(user)
            await ctx.send(f"User set to: `{user}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the username for your database.")
    

    @setnotes.command()
    @checks.is_owner()
    async def password(self, ctx, passwd: str):
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
    async def database(self, ctx, db: str):
        """
        Sets the database to login to, defaults to feedback
        """
        try:
            await self.config.guild(ctx.guild).mysql_db.set(db)
            await ctx.send(f"Database set to: `{db}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send ("There was a problem setting your notes database.")
    

    @setnotes.command()
    @checks.is_owner()
    async def prefix(self, ctx, prefix: str = None):
        """
        Sets the database prefix (if applicable)

        Leave blank to remove this option
        """
        try:
            if prefix is None:
                await self.config.guild(ctx.guild).mysql_prefix.set("")
                await ctx.send(f"Database prefix removed!")
            else:
                await self.config.guild(ctx.guild).mysql_prefix.set(prefix)
                await ctx.send(f"Database prefix set to: `{prefix}`")
        
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your database prefix")
    

    @setnotes.command()
    @checks.is_owner()
    async def currencyname(self, ctx, name: str = None):
        """
        Set the name of your meta currency

        Leave blank to reset this option back to the default
        """
        try:
            if name is None:
                await self.config.guild(ctx.guild).currency_name.set("Currency")
                await ctx.send(f"Metacurrency name reset to `Currency`")
            else:
                await self.config.guild(ctx.guild).currency_name.set(str(name).title())
                await ctx.send(f"Metacurrency name set to: `{name}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your currency's name")
    

    @setnotes.command()
    async def current(self, ctx):
        """
        Gets the current settings for the notes database
        """
        settings = await self.config.guild(ctx.guild).all()
        embed=discord.Embed(title="__Current settings:__")
        for k, v in settings.items():
            if k != "admin_ckey":
                if k != "mysql_password": # Ensures that the database password is not sent
                    if v == "":
                        v = None
                    embed.add_field(name=f"{k}:",value=v,inline=False)
                else:
                    embed.add_field(name=f"{k}:",value="`redacted`",inline=False)
        await ctx.send(embed=embed)


    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def notes(self, ctx, *, ckey: str):
        """
        Gets the notes for a specific player
        """
        ckey = key_to_ckey(ckey)
            
        prefix = await self.config.guild(ctx.guild).mysql_prefix()

        query = f"SELECT timestamp, adminckey, text, type, deleted FROM {prefix}messages WHERE targetckey='{ckey.lower()}' ORDER BY timestamp DESC"
        message = await ctx.send("Getting player notes...")

        try:
            rows = await self.query_database(ctx, query)
            if not rows:
                embed=discord.Embed(description=f"No notes found for: {str(ckey).title()}", color=0xf1d592)
                return await message.edit(content=None,embed=embed)
            # Parse the data into individual fields within an embeded message in Discord for ease of viewing
            notes = ""
            total = 0
            temp_embeds = []
            embeds = []
            for row in rows:
                if row['deleted'] == 1:
                    continue
                total += 1
                notes += f"\n[{row['timestamp']} | {row['type']} by {row['adminckey']}]\n{row['text']}"
            for note in pagify(notes):
                embed = discord.Embed(description=box(note, lang="asciidoc"), color=0xf1d592)
                temp_embeds.append(embed)
            max_i = len(temp_embeds)
            i = 1
            for embed in temp_embeds:
                embed.set_author(name=f"Notes for {str(ckey).title()} | Total notes: {total}")
                embed.set_footer(text=f"Page {i}/{max_i} | All times are server time")
                embeds.append(embed)
                i += 1
            await message.delete()
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        
        except mysql.connector.Error as err:
            embed=discord.Embed(title=f"Error looking up notes for: {ckey}", description=f"{format(err)}", color=0xff0000)
            await message.edit(content=None,embed=embed)
        
        except ModuleNotFoundError:
            await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")
    
    
    async def player_search(self, ctx, ip = None, ckey = None, cid = None) -> dict:
        """
        Runs multiple database queries to obtain the player's information
        """
        prefix = await self.config.guild(ctx.guild).mysql_prefix()

        try:
            # First query is determined by the identifier given 
            if ip:
                #IPs are stored as a 32 bit integer in the databse. We need to convert it before doing the query.
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM {prefix}player WHERE ip='{int(ipaddress.IPv4Address(ip))}'"
                query = await self.query_database(ctx, query)
            elif ckey:
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM {prefix}player WHERE ckey='{ckey}'"
                query = await self.query_database(ctx, query)
            elif cid:
                query = f"SELECT ckey, firstseen, lastseen, computerid, ip, accountjoindate FROM {prefix}player WHERE computerid='{cid}'"
                query = await self.query_database(ctx, query)

            results = {}
            try:
                query = query[0] # Checks to see if a player was found, if the list is empty nothing was found so we return the empty dict.
            except IndexError:
                return None
            results['ip'] = ipaddress.IPv4Address(query['ip']) #IP's are stored as a 32 bit integer, converting it for readability
            results['cid'] = query['computerid']
            results['ckey'] = query['ckey']
            results['first'] = query['firstseen']
            results['last'] = query['lastseen']
            results['join'] = query['accountjoindate']

            #Obtain the number of total connections
            query = f"SELECT COUNT(*) FROM {prefix}connection_log WHERE ckey='{results['ckey']}'"
            query = await self.query_database(ctx, query)
            results['num_connections'] = query[0]['COUNT(*)']

            #Obtain the number of total deaths
            query = f"SELECT COUNT(*) FROM {prefix}death WHERE byondkey='{results['ckey']}'"
            query = await self.query_database(ctx, query)
            results['num_deaths'] = query[0]['COUNT(*)']

            #Obtain role time statistics
            query = f"SELECT job, minutes FROM {prefix}role_time WHERE ckey='{ckey}' AND (job='Ghost' OR job='Living')"
            try:
                query = await self.query_database(ctx, query)
            except mysql.connector.Error:
                query = None

            if query:
                for job in query:
                    if job['job'] == "Living":
                        results['living_time'] = job['minutes'] // 60
                    else:
                        results['ghost_time'] = job['minutes'] // 60

                if 'living_time' not in results.keys():
                    results['living_time'] = 0
                if 'ghost_time' not in results.keys():
                    results['ghost_time'] = 0

            else:
                results['living_time'] = 0
                results['ghost_time'] = 0

            results['total_time'] = results['living_time'] + results['ghost_time']

            #Obtain metacoins and antag tokens (if avaialble).
            query = f"SELECT metacoins FROM {prefix}player WHERE ckey='{results['ckey']}'"
            try:
                query = await self.query_database(ctx, query)
                results['metacoins'] = (query[0])['metacoins']
            except mysql.connector.Error:
                pass
            
            query = f"SELECT antag_tokens FROM {prefix}player WHERE ckey='{results['ckey']}'"
            try:
                query = await self.query_database(ctx, query)
                results['antag_tokens'] = (query[0])['antag_tokens']
            except mysql.connector.Error:
                pass

            #Obtain the number of bans and, if applicable, the last ban
            query = f"SELECT bantime FROM {prefix}ban WHERE ckey='{results['ckey']}' ORDER BY bantime DESC"
            query = await self.query_database(ctx, query)
            results['num_bans'] = len(query)
            if results['num_bans'] > 0:
                results['latest_ban'] = list(query[0].values())[0]
            else:
                results['latest_ban'] = None

            #Obtain the total number of notes
            query = f"SELECT COUNT(*) FROM {prefix}messages WHERE targetckey='{results['ckey']}'"
            query = await self.query_database(ctx, query)
            results['notes'] = query[0]['COUNT(*)']

            if results['living_time'] > 0:
                results['notes_per_hour'] = round(results['notes'] / (results['total_time']), 2)
                results['deaths_per_hour'] = round(results['num_deaths'] / (results['living_time']), 2)
            else:
                results['notes_per_hour'] = 0
                results['deaths_per_hour'] = 0

            return results

        except:
            raise


    @commands.command(aliases=['ckey'])
    async def playerinfo(self, ctx, *, ckey: str):
        """
        Lookup a player's stats based on their ckey
        """
        ckey = key_to_ckey(ckey)

        try:
            message = await ctx.send("Looking up player....")
            async with ctx.typing():
                embed=discord.Embed(color=await ctx.embed_color())
                embed.set_author(name=f"Player info for {str(ckey).title()}")
                player = await self.player_search(ctx, ckey=ckey)
            
            if player is None:
                raise ValueError
            
            player_stats = f"**Playtime**: {player['total_time']}h ({player['living_time']}h/{player['ghost_time']}h)\n**Deaths per Hour**: {player['deaths_per_hour']}"
            if 'metacoins' in player.keys():
                player_stats += f"\n**{await self.config.guild(ctx.guild).currency_name()}**: {player['metacoins']}"
            if 'antag_tokens' in player.keys():
                player_stats += f"\n**Antag Tokens**: {player['antag_tokens']}"

            embed.add_field(name="__Player Statistics__:", value=player_stats, inline=False)
            embed.add_field(name="__Connection Information:__", value=f"**First Seen**: {player['first']}\n**Last Seen**: {player['last']}\n**Account Join Date**: {player['join']}\n**Number of Connections**: {player['num_connections']}", inline=False)
            await message.edit(content=None, embed=embed)

        except ValueError:
            return await message.edit(content="No results found.")
        
        except mysql.connector.Error  as err:
            embed=discord.Embed(title=f"Error looking up player", description=f"{format(err)}", color=0xff0000)
            return await message.edit(content=None,embed=embed)
            
        except ModuleNotFoundError:
            return await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")


    @checks.mod_or_permissions(administrator=True)
    @commands.command()
    async def findplayer(self, ctx, *, identifier: Union[ipaddress.IPv4Address, int, str] = None):
        """
        Obtains information about a specific player.

        Will search for players using a provided IP, CID, or CKEY. 
        """

        try:
            message = await ctx.send("Looking up player....")
            async with ctx.typing():

                if type(identifier) is ipaddress.IPv4Address:
                    player = await self.player_search(ctx, ip=identifier)
                elif type(identifier) is int:
                    player = await self.player_search(ctx, cid=identifier)
                elif type(identifier) is str:
                    identifier = key_to_ckey(identifier)
                    player = await self.player_search(ctx, ckey=identifier)
                else:
                    return await message.edit(content="That doesn't look like an IP, CID, or CKEY. Please check your entry and try again!")
                    
            if player is None:
                raise ValueError
                
            embed=discord.Embed(color=await ctx.embed_color())
            embed.set_author(name=f"Player info for {str(player['ckey']).title()}")

            player_stats = f"**Playtime**: {player['total_time']}h ({player['living_time']}h/{player['ghost_time']}h)\n**Deaths per Hour**: {player['deaths_per_hour']}"
            if 'metacoins' in player.keys():
                player_stats += f"\n**{await self.config.guild(ctx.guild).currency_name()}**: {player['metacoins']}"
            if 'antag_tokens' in player.keys():
                player_stats += f"\n**Antag Tokens**: {player['antag_tokens']}"
            
            embed.add_field(name="__Identity:__",value=f"**CKEY**: {player['ckey']}\n**CID**: {player['cid']}\n**IP**: {player['ip']}\n**Account Join Date**: {player['join']}", inline=False)                    
            embed.add_field(name="__Player Statistics__:", value=player_stats, inline=False)
            embed.add_field(name="__Connection Information:__", value=f"**First Seen**: {player['first']}\n**Last Seen**: {player['last']}\n**Number of Connections**: {player['num_connections']}", inline=False)
    
            embed.add_field(name="__Bans/Notes:__", value=f"**Number of Notes**: {player['notes']}\n**Number of Bans**: {player['num_bans']}\n**Last Ban**: {player['latest_ban']}\n**Notes per Hour**: {player['notes_per_hour']}", inline=False)

            await message.edit(content=None, embed=embed)

            # After 5-minutes redact the player's CID and IP.
            await asyncio.sleep(300)
            embed.set_field_at(0, name="__Identity:__",value=f"**CKEY**: {player['ckey']}\n**CID**: `[Redacted]`\n**IP**: `[Redacted]`\n**Account Join Date**: {player['join']}", inline=False)                    

            await message.edit(content=None, embed=embed)

        except ValueError:
            return await message.edit(content="No results found.")
        
        except (mysql.connector.Error, ValueError) as err:
            embed=discord.Embed(title=f"Error looking up player", description=f"{format(err)}", color=0xff0000)
            return await message.edit(content=None,embed=embed)
            
        except ModuleNotFoundError:
            return await message.edit(content="`mysql-connector` requirement not found! Please install this requirement using `pip install mysql-connector`.")


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