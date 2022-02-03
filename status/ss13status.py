#Standard Imports
import asyncio
import struct
import socket
import urllib.parse
import html as htmlparser
import time
import textwrap
from datetime import datetime
import logging
import json

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config

__version__ = "1.1.0"
__author__ = "Crossedfall"

log = logging.getLogger("red.SS13Status")

class SS13Status(commands.Cog):

    def __init__(self, bot):
        self.serv = None #Will be the task responsible for incoming game data
        self.antispam = 0 #Used to prevent @here mention spam
        self.statusmsg = None #Used to delete the status message
        self.newroundmsg = None #Used to delete the new round notification
        self.roundID = None

        self.bot = bot
        self.config = Config.get_conf(self, 3257193194, force_registration=True)

        default_global = {
            "server": None,
            "game_port": None,
            "offline_message": "Currently offline",
            "server_url": "byond://127.0.0.1:7777", 
            "new_round_channel": None,
            "admin_notice_channel": None,
            "mentor_notice_channel": None,
            "ban_notice_channel": None,
            "mention_role": None,
            "comms_key": "default_pwd",
            "listen_port": 8081,
            "timeout": 10,
            "topic_toggle": False,
            "legacy_topics": True
        }

        self.config.register_global(**default_global)
        self.serv = bot.loop.create_task(self.listener())
        self.svr_chk_task = self.bot.loop.create_task(self.server_check_loop())
    
    def cog_unload(self):
        self.serv.cancel()

    async def changed_port(self, ctx, port: int):
        self.serv.cancel()
        await asyncio.sleep(5) 
        self.serv = self.bot.loop.create_task(self.listener())
        await ctx.send(f"Listening on port: {port}")

    @commands.guild_only()
    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def setstatus(self, ctx):
        """
        Configuration group for the SS13 status command
        """
        pass
    
    @setstatus.command(aliases=['host'])
    async def server(self, ctx, host: str):
        """
        Sets the server IP used for status checks
        """
        try:
            await self.config.server.set(host)
            await ctx.send(f"Server set to: `{host}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the host! Please check your entry and try again.")
    
    @setstatus.command()
    async def port(self, ctx, port: int):
        """
        Sets the port used for the status checks
        """
        try:
            if 1024 <= port <= 65535: # We don't want to allow reserved ports to be set
                await self.config.game_port.set(port)
                await ctx.send(f"Host port set to: `{port}`")
            else:
                await ctx.send(f"`{port}` is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535")

    @setstatus.command()
    async def offline(self, ctx, *, msg: str):
        """
        Set a custom message for whenever the server is offline.
        """ 
        try:
            await self.config.offline_message.set(msg)
            await ctx.send(f"Offline message set to: `{msg}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your custom offline message. Please check your entry and try again.")
    
    @setstatus.command()
    async def byondurl(self, ctx, url: str):
        """
        Set the byond URL for your server (For embeds)
        """
        try:
            await self.config.server_url.set(url)
            await ctx.send(f"Server url set to: `{url}`")

        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your server URL. Please check your entry and try again.")
    
    @setstatus.command()
    async def newroundchannel(self, ctx, text_channel: discord.TextChannel = None):
        """
        Sets the channel for new round notifications. 
        
        Use without providing a channel to reset this to None.
        """
        try: 
            if text_channel is not None:
                await self.config.new_round_channel.set(text_channel.id)
                await ctx.send(f"New round notifications will be sent to: {text_channel.mention}")
            else:
                await self.config.new_round_channel.set(None)
                await ctx.send("I will no longer send new round notifications.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    async def adminchannel(self, ctx, text_channel: discord.TextChannel = None):
        """
        Set the text channel to display admin notifications.
        
        Use without providing a channel to reset this to None.
        """
        try:
            if text_channel is not None:
                await self.config.admin_notice_channel.set(text_channel.id)
                await ctx.send(f"Admin notifications will be sent to: {text_channel.mention}")
            else:
                await self.config.admin_notice_channel.set(None)
                await ctx.send("I will no longer provide admin notices.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    async def mentorchannel(self, ctx, text_channel: discord.TextChannel = None):
        """
        Set the text channel for mentor notifications.
        
        Use without providing a channel to reset this to None.
        """
        try:
            if text_channel is not None:
                await self.config.mentor_notice_channel.set(text_channel.id)
                await ctx.send(f"Mentor notifications will be sent to: {text_channel.mention}")
            else:
                await self.config.mentor_notice_channel.set(None)
                await ctx.send("I will no longer provide mentor notices.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    async def banchannel(self, ctx, text_channel: discord.TextChannel = None):
        """
        Set the text channel for ban notifications.
        
        Use without providing a channel to reset this to None.
        """
        try:
            if text_channel is not None:
                await self.config.ban_notice_channel.set(text_channel.id)
                await ctx.send(f"Ban notifications will be sent to: {text_channel.mention}")
            else:
                await self.config.ban_notice_channel.set(None)
                await ctx.send("I will no longer provide ban notices.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    async def mentionrole(self, ctx, role: discord.Role = None):
        """
        Sets a role to mention in new round notifications. 
        
        Use without providing a role to reset to None.
        """
        try:
            if role is not None:
                await self.config.mention_role.set(role.id)
                await ctx.send(f"New round notifications will now mention the `{role.name}` role.")
            else:
                await self.config.mention_role.set(None)
                await ctx.send("I will no longer mention anyone whenever a new round starts.")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the mention role. Please check your entry and try again.")


    @setstatus.command()
    async def commskey(self, ctx, key: str):
        """
        Set the communications key for the server
        """
        try:
            await self.config.comms_key.set(key) #Used to verify incoming game data
            await ctx.send("Comms key set.")
            try:
                await ctx.message.delete()
            except(discord.DiscordException):
                await ctx.send("I do not have the required permissions to delete messages. You may wish to edit/remove your comms key manually.")
        
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your communications key. Please check your entry and try again.")

    @setstatus.command()
    async def listenport(self, ctx, port: int):
        """
        Set the port you'd like the bot to listen on
        """
        try:
            if 1024 <= port <= 65535: #Same as the other port config option, we only want to allow non-reserved ports
                await self.config.listen_port.set(port)
                await ctx.send(f"Changing the port...")
                await self.changed_port(ctx, port) #Restart the listening service
            else:
                await ctx.send(f"{port} is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535")

    @setstatus.command()
    async def timeout(self, ctx, seconds: int):
        """
        Sets the timeout duration for status checks
        """
        try:
            await self.config.timeout.set(seconds)
            await ctx.send(f"Timeout duration set to: `{seconds} seconds`")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the timeout duration. Please check your input and try again.")

    @setstatus.command()
    async def toggletopic(self, ctx, toggle:bool = None):
        """
        Channel topic status toggle

        With this enabled, the topic description will be automatically set with the server's latest details. Automatically updating every 5 minutes.
        """

        if toggle is None:
            toggle = await self.config.topic_toggle()
            toggle = not toggle

        try:
            await self.config.topic_toggle.set(toggle)
            if toggle is True:
                await ctx.send(f"I will display the server's status within the new round channel. If you haven't already, be sure to set that with `{ctx.prefix}setstatus newroundchannel <channel>`")
            else:
                await ctx.send("I will no longer display the server's status within the new round channel's topic description.")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting topic toggle. Please check your input and try again.")

        try:
            channel = self.bot.get_channel(await self.config.new_round_channel())
            if channel is not None:
                await channel.edit(topic="")
        except:
            await ctx.send("I was unable to clear the channel's current topic. You might want to clear it manually.")

    @setstatus.command()
    async def current(self, ctx):
        """
        Lists the current settings
        """
        settings = await self.config.all()
        embed=discord.Embed(title="__Current Settings:__")
        
        for k, v in settings.items():
            if k == 'comms_key': #We don't want to actively display the comms key
                embed.add_field(name=f"{k}:", value="`redacted`", inline=False)
            elif (k == 'new_round_channel' or k == 'admin_notice_channel' or k == 'mentor_notice_channel' or k == 'ban_notice_channel') and (v is not None): #Linkify channels
                embed.add_field(name=f"{k}:", value=f"<#{v}>", inline=False)
            elif k == 'mention_role':
                role = discord.utils.get(ctx.guild.roles, id=await self.config.mention_role())
                if role is not None:
                    embed.add_field(name=f"{k}:", value=role.name)
                else:
                    embed.add_field(name=f"{k}:", value=v)
            elif k == 'timeout':
                embed.add_field(name=f"{k}:", value=f"{v} seconds")
            else:
                embed.add_field(name=f"{k}:", value=v, inline=False)
        
        await ctx.send(embed=embed)

    @setstatus.command()
    async def togglelegacy(self, ctx, toggle: bool = None):
        """
        Toggle between the legacy topic system and the latest version. 
        
        If you aren't sure which option to use, set this to True.
        """
        if toggle is None:
            toggle = await self.config.legacy_topics()
            toggle = not toggle
        
        await self.config.legacy_topics.set(toggle)
        await ctx.send(f"""Understood! I will use the {"legacy" if toggle is True else "updated"} topic system to communicate with the server.""")


    @commands.guild_only()
    @commands.command()
    async def players(self, ctx):
        """
        Lists the current players on the server
        """
        port = await self.config.game_port()
        try:
            server = socket.gethostbyname(await self.config.server())
            topic_system = await self.config.legacy_topics()
            data = await self.query_server(server, port, "?whoIs", topic_system)
        except TypeError:
            await ctx.send(f"Failed to get players. Check that you have fully configured this cog using `{ctx.prefix}setstatus`.")
            return
            
        if data:
            try:
                players = [i for i in data['players']]

                embed = discord.Embed(title=f"__Current Players__ ({len(players)}): ", description=f'\n'.join(map(str,players)))

                await ctx.send(embed=embed)
            except KeyError:
                await ctx.send("Unable to determine who is playing! Please check the world topic to ensure it is correctly configured.")
        else:
            await ctx.send(embed=discord.Embed(title="__Current Players__ (0):", description="No players current online"))

    @commands.guild_only()
    @commands.command()
    async def adminwho(self, ctx):
        """
        List the current admins on the server
        """
        port = await self.config.game_port()
        try:
            server = socket.gethostbyname(await self.config.server())
            topic_system = await self.config.legacy_topics()
            data = await self.query_server(server, port, "?getAdmins", topic_system)
        except TypeError:
            await ctx.send(f"Failed to get admins. Check that you have fully configured this cog using `{ctx.prefix}setstatus`.")
            return

        if data:
            try:
                admins = [i for i in data['admins']]

                embed = discord.Embed(title=f"__Current Admins__ ({len(admins)}): ", description=f'\n'.join(map(str,admins)))

                await ctx.send(embed=embed)
            except KeyError:
                await ctx.send("Unable to determine who is administrating! Please check the world topic to ensure it is correctly configured.")
        else:
            await ctx.send(embed=discord.Embed(title="__Current Admins__ (0):", description="No Admins are current online"))
        


    @commands.guild_only()
    @commands.command()
    @commands.cooldown(1, 5)
    async def status(self, ctx):
        """
        Gets the current server status and round details
        """
        port = await self.config.game_port()        
        msg = await self.config.offline_message()
        server_url = await self.config.server_url()
        try:
            server = socket.gethostbyname(await self.config.server())
            topic_system = await self.config.legacy_topics()
            data = await self.query_server(server, port, legacy=topic_system)
        except TypeError:
            return await ctx.send(f"Failed to get the server's status. Check that you have fully configured this cog using `{ctx.prefix}setstatus`.")
        except LookupError as e:
            return await ctx.send(f"There appears to be an error with this cog's configuration. Please contact an admin with the following:\n`{e}`")

        if not data: #Server is not responding, send the offline message
            embed=discord.Embed(title="__Server Status:__", description=f"{msg}", color=0xff0000)
            await ctx.send(embed=embed)

        else:
            #Reported time is in seconds, we need to convert that to be easily understood
            duration = int(data['round_duration'])
            duration = time.strftime('%H:%M', time.gmtime(duration))
            #Players also includes the number of admins, so we need to do some quick math
            players = (int(data['players']) - int(data['admins'])) 
            #Format long map names
            mapname = str.title(data['map_name'])
            mapname = '\n'.join(textwrap.wrap(mapname,25))


            #Might make the embed configurable at a later date

            embed=discord.Embed(color=0x26eaea)
            embed.add_field(name="Map", value=mapname, inline=True)
            embed.add_field(name="Security Level", value=str.title(data['security_level']), inline=True)
            if  "shuttle_mode" in data:
                if ("docked" or "call") not in data['shuttle_mode']:
                    embed.add_field(name="Shuttle Status", value=str.title(data['shuttle_mode']), inline=True)
                else:
                    embed.add_field(name="Shuttle Timer", value=time.strftime('%M:%S', time.gmtime(int(data['shuttle_timer']))), inline=True)
            else:
                embed.add_field(name="Shuttle Status", value="Refueling", inline=True)
            embed.add_field(name="Players", value=players, inline=True)
            embed.add_field(name="Admins", value=int(data['admins']), inline=True)
            embed.add_field(name="Round Duration", value=duration, inline=True)
            embed.add_field(name="Server Link:", value=f"<{server_url}>", inline=False)

            try:
                await self.statusmsg.delete()
                self.statusmsg = await ctx.send(embed=embed)
            except(discord.DiscordException, AttributeError):
                self.statusmsg = await ctx.send(embed=embed)
        

    async def query_server(self, game_server:str, game_port:int, querystr: str = "?status", legacy: bool = None) -> dict:
        """
        Queries the server for information
        """
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

        try:
            if legacy is False:
                querystr = json.dumps({
                    "auth": "anonymous",
                    "query": querystr.lstrip("?"),
                    "source": "Redbot - ss13Status"
                })

            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard   
            conn.settimeout(await self.config.timeout()) #Byond is slow, timeout set relatively high to account for any latency
            conn.connect((game_server, game_port)) 

            conn.sendall(query)

            data = conn.recv(4096) #Minimum number should be 4096, anything less will lose data

            if legacy or legacy is None:
                parsed_data = urllib.parse.parse_qs(data[5:-1].decode())
                for k,v in parsed_data.items(): #Legacy topics return a dict of lists
                    parsed_data[k] = v[0]
            else:
                parsed_data = json.loads(data[5:-1].decode())
                if 'data' not in parsed_data:
                    raise LookupError(f"Bad response from server {parsed_data}")
                parsed_data = parsed_data['data']

            return parsed_data
            """
            +----------------+--------+
            | Reported Items | Return |
            +----------------+--------+
            | Version        | str    |
            | mode           | str    |
            | respawn        | int    |
            | enter          | int    |
            | vote           | int    |
            | ai             | int    |
            | host           | str    |
            | active_players | int    |
            | players        | int    |
            | revision       | str    |
            | revision_date  | date   |
            | admins         | int    |
            | gamestate      | int    |
            | map_name       | str    |
            | security_level | str    |
            | round_duration | int    |
            | shuttle_mode   | str    |
            | shuttle_timer  | str    |
            +----------------+--------+
            """ #pylint: disable=unreachable
            
        except (ConnectionRefusedError, socket.gaierror, socket.timeout, TimeoutError) as e:
            log.debug(f"Unable to retrieve information from the server due to:\n{e}")
            return None #Server is likely offline
        except LookupError as e:
            log.warning(e)
            raise e
        except json.JSONDecodeError:
            log.warning(f"Unable to communicate with the server. It looks like we're sending updated topic requests but the server is expecting legacy requests.")
            raise LookupError("A JSON request sent, but one was not returned. Verify that the correct topic system is set.")

        finally:
            conn.close()

    async def data_handler(self, reader, writer):
        ###############
        #Data Handling#
        ###############
        data = await reader.read(10000)
        msg = data.decode()
        msg = msg.split(" ")[1] #Drop the 'GET'
        parsed_data = urllib.parse.parse_qs(msg[2:len(msg)]) #Drop the leading ?/ and make the text readable

        writer.close()
        
        ##################
        #Message Handling#
        ##################
        admin_channel = self.bot.get_channel(await self.config.admin_notice_channel())
        mentor_channel = self.bot.get_channel(await self.config.mentor_notice_channel())
        ban_channel = self.bot.get_channel(await self.config.ban_notice_channel())
        new_round_channel = self.bot.get_channel(await self.config.new_round_channel())
        if admin_channel is not None:
            mention_role = discord.utils.get(admin_channel.guild.roles, id=(await self.config.mention_role()))
        comms_key = await self.config.comms_key()
        byondurl = await self.config.server_url()
        parser = htmlparser

        log.debug("Message incoming!")

        if ('key' in parsed_data) and (comms_key in parsed_data['key']): #Check to ensure that we're only serving messages from our game
            if ('serverStart' in parsed_data) and (new_round_channel is not None):
                embed = discord.Embed(title="Starting new round!", description=f"<{byondurl}>", color=0x8080ff)

                if ('roundID' in parsed_data):
                    self.roundID = parsed_data['roundID'][0]
                    embed.set_footer(text=f"Round: {self.roundID}")

                try:
                    await self.newroundmsg.delete()
                    if mention_role is not None:
                        try:
                            await mention_role.edit(mentionable=True)
                            self.newroundmsg = await new_round_channel.send(mention_role.mention)
                            await mention_role.edit(mentionable=False)
                            await self.newroundmsg.edit(embed=embed)

                        except(discord.Forbidden):
                            await admin_channel.send(f"Mentions are configured, but I don't have permissions to edit {mention_role.mention}")
                            self.newroundmsg = await new_round_channel.send(embed=embed)

                    else:
                        self.newroundmsg = await new_round_channel.send(embed=embed)

                except(discord.DiscordException, AttributeError):
                    if mention_role is not None:
                        try:
                            await mention_role.edit(mentionable=True)
                            self.newroundmsg = await new_round_channel.send(mention_role.mention)
                            await mention_role.edit(mentionable=False)
                            await self.newroundmsg.edit(embed=embed)

                        except(discord.Forbidden):
                            await admin_channel.send(f"Mentions are configured, but I don't have permissions to edit {mention_role.name}")
                            self.newroundmsg = await new_round_channel.send(embed=embed)

                    else:
                        self.newroundmsg = await new_round_channel.send(embed=embed)
            
            elif ('announce_channel' in parsed_data) and ('mentor' in parsed_data['announce_channel']) and (mentor_channel is not None):
                announce = str(*parsed_data['announce'])
                ticket = announce.split('): ')
                ticket[1] = parser.unescape(ticket[1])
                embed = discord.Embed(title=f"{ticket[0]}):", description=ticket[1], color=0x935bfc)
                if self.roundID is not None:
                    embed.set_footer(text=f"Round: {self.roundID}")
                await mentor_channel.send(embed=embed)

            elif ('announce_channel' in parsed_data) and ('ban' in parsed_data['announce_channel']) and (ban_channel is not None): #shitty copypaste cause I dunno what am doing
                announce = str(*parsed_data['announce'])
                ticket = announce.split('): ')
                ticket[1] = parser.unescape(ticket[1])
                embed = discord.Embed(title=f"{ticket[0]}):", description=ticket[1], color=0xff0000)
                if self.roundID is not None:
                    embed.set_footer(text=f"Round: {self.roundID}")
                await ban_channel.send(embed=embed)

            elif ('announce_channel' in parsed_data) and ('admin' in parsed_data['announce_channel']) and (admin_channel is not None): #Secret messages only meant for admin eyes
                announce = str(*parsed_data['announce'])
                if "Ticket" in announce:
                    ticket = announce.split('): ')
                    ticket[1] = parser.unescape(ticket[1])
                    embed = discord.Embed(title=f"{ticket[0]}):", description=ticket[1],color=0xff0000)
                    if self.roundID is not None:
                        embed.set_footer(text=f"Round: {self.roundID}")
                    await admin_channel.send(embed=embed)

                elif "@here" in announce and self.antispam == 0: #Ping any online admins once every 5 minutes
                    if "A new ticket" in announce:
                        await admin_channel.send(f"@here - A new ticket was submitted but no admins appear to be online.\n")
                        
                        self.antispam = 1
                        await asyncio.sleep(300)
                        self.antispam = 0

                    elif 4 in parsed_data['gamestate']:
                        await admin_channel.send(f"End-round activity detected.\n")
                    
                    else:
                        await admin_channel.send(f"@here - A new round ending event requires/might need attention, but there are no admins online.\n")

                        self.antispam = 1
                        await asyncio.sleep(300)
                        self.antispam = 0
                
                elif "@here" not in announce: 
                    embed = discord.Embed(title=announce, color=0xf95100)
                    if self.roundID is not None:
                        embed.set_footer(text=f"Round: {self.roundID}")
                    await admin_channel.send(embed=embed)

            else: #If it's not one of the above, it's not worth serving
                log.debug(f"The message was not something I could handle. -- {str(*parsed_data['announce'])}")
                pass
        else:#Don't serve any messages that aren't from our game
            log.debug(f"""Message recieved but {f"the key ({str(*parsed_data['announce'])}) did not match." if 'key' in parsed_data else "no key was provided."}""")
            pass


    async def listener(self):
        await asyncio.sleep(10) #Delay before listening to ensure that the interface isn't bound multiple times
        port = await self.config.listen_port()

        server = await asyncio.start_server(self.data_handler, '0.0.0.0', port) #Listen on all interfaces from a non-standard port

        async with server: #Listen until the cog is unloaded or the bot shutsdown
            await server.serve_forever()

    async def server_check_loop(self): #This will be used to cache statuses later
        check_time = 300
        error_limit = 10
        error_counter = 0
        now = datetime.utcnow()
        while self == self.bot.get_cog("SS13Status"):
            log.debug("Starting server checks")
                     
            channel = self.bot.get_channel(await self.config.new_round_channel())
            toggle = await self.config.topic_toggle()
            server = await self.config.server()
            port = await self.config.game_port()
            
            if toggle is False or server is None or port is None or channel is None or error_counter < error_limit:
                pass
            else:

                if channel.permissions_for(channel.guild.me).manage_channels is False:
                    log.debug("Unable to set channel topic.")
                    pass
                else:
                    try:
                        topic_system = await self.config.legacy_topics()
                        status = await self.query_server(server, port, legacy=topic_system)
                    except Exception as e:
                        error_counter = error_counter + 1
                        if error_counter < error_limit:
                            check_time = check_time + 300
                            log.warning(f"There was an error getting the server's status. Attempting again in {check_time}. Error {error_counter} of {error_limit} before disabling checks.\n\nException:\n{e}")
                            await asyncio.sleep(check_time)
                            continue
                        else:
                            log.warning(f"Exceeded the number of status errors. Disabling server checks.\n\nException:\n{e}")
                            break

                    if status is not None:
                        duration = int(*status['round_duration'])
                        duration = time.strftime('%H:%M', time.gmtime(duration))
                        topic = f"Server info for <{await self.config.server_url()}>: Players: {status['players'][0]} | Map: {str.title(*status['map_name'])} | Security Level: {str.title(*status['security_level'])} | Round Duration: {duration}"
                    else:
                        topic = f"Server info for <{await self.config.server_url()}>: Offline" 

                    await channel.edit(topic=topic)

            now = datetime.utcnow()
            next_check = datetime.utcfromtimestamp(now.timestamp() + check_time)
            log.debug("Done. Next check at {}".format(next_check.strftime("%Y-%m-%d %H:%M:%S")))
            check_time = 300
            error_counter = 0
            await asyncio.sleep(check_time)
