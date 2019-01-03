#Standard Imports
import asyncio
import ipaddress
import struct
import select
import socket
import urllib.parse
import html.parser as htmlparser
import time

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "0.9.2"
__author__ = "Crossedfall"

BaseCog = getattr(commands, "Cog", object)

class SS13Status(BaseCog):

    def __init__(self, bot):
        self.serv = None #Will be the task responsible for incoming game data
        self.antispam = None #Used to prevent @here mention spam
        self.statusmsg = None #Used to delete the status message
        self.newroundmsg = None #Used to delete the new round notification

        self.bot = bot
        self.config = Config.get_conf(self, 3257193194, force_registration=True)

        default_global = {
            "server": "127.0.0.1",
            "game_port": 7777,
            "offline_message": "Currently offline",
            "server_url": "byond://127.0.0.1:7777", 
            "new_round_channel": None,
            "admin_notice_channel": None,
            "mention_role": None,
            "comms_key": "default_pwd",
            "listen_port": 8081,
            "timeout": 10,
        }

        self.config.register_global(**default_global)
        self.serv = bot.loop.create_task(self.listener())
    
    def __unload(self):
        self.serv.cancel()

    async def changed_port(self, ctx, port: int):
        self.serv.cancel()
        await asyncio.sleep(5) 
        self.serv = self.bot.loop.create_task(self.listener())
        await ctx.send(f"Listening on port: {port}")

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
        Sets the server IP used for status checks, defaults to localhost
        """
        try:
            ipaddress.ip_address(host) # Confirms that the IP provided is valid. If the IP is not valid, a ValueError is thrown.
            await self.config.server.set(host)
            await ctx.send(f"Server set to `{host}`")
        except(ValueError):
            await ctx.send(f"`{host}` is not a valid IP address!")
    
    @setstatus.command()
    @checks.is_owner()
    async def port(self, ctx, port: int):
        """
        Sets the port used for the status checks, defaults to 7777
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
    @checks.is_owner()
    async def offline(self, ctx, msg: str):
        """
        Set a custom message for whenever the server is offline.
        """ 
        try:
            await self.config.offline_message.set(msg)
            await ctx.send(f"Offline message set to: `{msg}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your custom offline message. Please check your entry and try again.")
    
    @setstatus.command()
    @checks.is_owner()
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
    @checks.is_owner()
    async def newroundchannel(self, ctx, text_channel: discord.TextChannel):
        """
        Set the text channel to display new round notifications
        """
        try: 
            await self.config.new_round_channel.set(text_channel.id)
            await ctx.send(f"New round notifications will be sent to: {text_channel.mention}")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    @checks.is_owner()
    async def adminchannel(self, ctx, text_channel: discord.TextChannel):
        """
        Set the text channel to display admin notifications
        """
        try:
            await self.config.admin_notice_channel.set(text_channel.id)
            await ctx.send(f"Admin notifications will be sent to: {text_channel.mention}")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

    @setstatus.command()
    @checks.is_owner()
    async def mentionrole(self, ctx, role: discord.Role):
        """
        Sets a role to mention in new round notifications
        """
        try:
         await self.config.mention_role.set(role.id)
         await ctx.send(f"New round notifications will now mention the `{role.name}` role.")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the mention role. Please check your entry and try again.")


    @setstatus.command()
    @checks.is_owner()
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
    @checks.is_owner()
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
    @checks.is_owner()
    async def timeout(self, ctx, seconds: int):
        """
        Sets the timeout duration for server status checks (in seconds)
        """
        try:
            await self.config.timeout.set(seconds)
            await ctx.send(f"Timeout duration set to: `{seconds} seconds`")
        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the timeout duration. Please check your input and try again.")

    @setstatus.command()
    @checks.admin_or_permissions(administrator=True)
    async def current(self, ctx):
        """
        Lists the current settings
        """
        settings = await self.config.all()
        embed=discord.Embed(title="__Current Settings:__")
        
        for k, v in settings.items():
            if k is 'comms_key': #We don't want to actively display the comms key
                embed.add_field(name=f"{k}:", value="`redacted`", inline=False)
            elif (k is 'new_round_channel' or k is 'admin_notice_channel') and (v is not None): #Linkify channels
                embed.add_field(name=f"{k}:", value=f"<#{v}>", inline=False)
            elif k is 'mention_role':
                role = discord.utils.get(ctx.guild.roles, id=await self.config.mention_role())
                if role is not None:
                    embed.add_field(name=f"{k}:", value=role.name)
                else:
                    embed.add_field(name=f"{k}:", value=v)
            elif k is 'timeout':
                embed.add_field(name=f"{k}:", value=f"{v} seconds")
            else:
                embed.add_field(name=f"{k}:", value=v, inline=False)
        
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def players(self, ctx):
        """
        Lists the current players on the server
        """
        server = await self.config.server()
        port = await self.config.game_port()
        data = await self.query_server(server,port,"?whoIs")

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
        server = await self.config.server()
        port = await self.config.game_port()
        data = await self.query_server(server,port,"?adminWho")

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
        server = await self.config.server()
        port = await self.config.game_port()        
        msg = await self.config.offline_message()
        server_url = await self.config.server_url()

        data = await self.query_server(server, port)

        if not data: #Server is not responding, send the offline message
            embed=discord.Embed(title="__Server Status:__", description=f"{msg}", color=0xff0000)
            await ctx.send(embed=embed)

        else:
            #Reported time is in seconds, we need to convert that to be easily understood
            duration = int(*data['round_duration'])
            duration = time.strftime('%H:%M', time.gmtime(duration))
            #Players also includes the number of admins, so we need to do some quick math
            players = (int(*data['players']) - int(*data['admins'])) 

            #Might make the embed configurable at a later date

            embed=discord.Embed(color=0x26eaea)
            embed.add_field(name="Map", value=str.title(*data['map_name']), inline=True)
            embed.add_field(name="Security Level", value=str.title(*data['security_level']), inline=True)
            if ("docked" or "call") not in data['shuttle_mode']:
                embed.add_field(name="Shuttle Status", value=str.title(*data['shuttle_mode']), inline=True)
            else:
                embed.add_field(name="Shuttle Timer", value=time.strftime('%M:%S', time.gmtime(int(*data['shuttle_timer']))), inline=True)
            embed.add_field(name="Players", value=players, inline=True)
            embed.add_field(name="Admins", value=int(*data['admins']), inline=True)
            embed.add_field(name="Round Duration", value=duration, inline=True)
            embed.add_field(name="Server Link:", value=f"{server_url}", inline=False)

            try:
                await self.statusmsg.delete()
                self.statusmsg = await ctx.send(embed=embed)
            except(discord.DiscordException, AttributeError):
                self.statusmsg = await ctx.send(embed=embed)
        

    async def query_server(self, game_server:str, game_port:int, querystr="?status" ) -> dict:
        """
        Queries the server for information
        """
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        timeout = self.config.timeout()
        try:
            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
            conn.settimeout(timeout) #Byond is slow, timeout set relatively high to account for any latency
            conn.connect((game_server, game_port)) 

            conn.sendall(query)

            data = conn.recv(4096) #Minimum number should be 4096, anything less will lose data

            parsed_data = urllib.parse.parse_qs(data[5:-1].decode())

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
            
        except (ConnectionRefusedError, socket.gaierror, socket.timeout):
            return None #Server is likely offline

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
        new_round_channel = self.bot.get_channel(await self.config.new_round_channel())
        mention_role = discord.utils.get(admin_channel.guild.roles, id=(await self.config.mention_role()))
        comms_key = await self.config.comms_key()
        byondurl = await self.config.server_url()
        parser = htmlparser.HTMLParser()

        if ('key' in parsed_data) and (comms_key in parsed_data['key']): #Check to ensure that we're only serving messages from our game
            if ('serverStart' in parsed_data) and (new_round_channel is not None):
                embed = discord.Embed(title="Starting new round!", description=byondurl, color=0x8080ff)

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

            elif ('announce_channel' in parsed_data) and ('admin' in parsed_data['announce_channel']): #Secret messages only meant for admin eyes
                announce = str(*parsed_data['announce'])
                if "Ticket" in announce:
                    ticket = announce.split('): ')
                    ticket[1] = parser.unescape(ticket[1])
                    embed = discord.Embed(title=f"{ticket[0]}):", description=ticket[1],color=0xff0000)
                    await admin_channel.send(embed=embed)

                elif "@here" in announce and self.antispam == 0: #Ping any online admins once every 5 minutes
                    if "A new ticket" in announce:
                        await admin_channel.send(f"@here - A new ticket was submitted but no admins appear to be online.\n")
                        
                        self.antispam = 1
                        await asyncio.sleep(300)
                        self.antispam = 0

                    else:
                        await admin_channel.send(f"@here - A new round ending event requires/might need attention, but there are no admins online.\n")

                        self.antispam = 1
                        await asyncio.sleep(300)
                        self.antispam = 0
                
                elif "@here" not in announce: 
                    embed = discord.Embed(title=announce, color=0xf95100)
                    await admin_channel.send(embed=embed)

                else: #If it's not one of the above, it's not worth serving
                    pass
        else:#Don't serve any messages that aren't from our game
            pass


    async def listener(self):
        await asyncio.sleep(10) #Delay before listening to ensure that the interface isn't bound multiple times
        port = await self.config.listen_port()

        server = await asyncio.start_server(self.data_handler, '0.0.0.0', port) #Listen on all interfaces from a non-standard port

        async with server: #Listen until the cog is unloaded or the bot shutsdown
            await server.serve_forever()