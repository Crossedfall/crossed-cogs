#Standard Imports
import asyncio
import ipaddress
import struct
import select
import socket
import urllib.parse

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils

__version__ = "0.9.0"
__author__ = "Crossedfall"

BaseCog = getattr(commands, "Cog", object)

class SS13Status(BaseCog):

    def __init__(self, bot):
        global serv #Will be the task responsible for incoming game data
        global antispam #Used to prevent @here mention spam
        global statusmsg #Used to delete the status message
        global newroundmsg #Used to delete the new round notification
        newroundmsg = None
        statusmsg  = None
        antispam = 0

        self.bot = bot
        self.config = Config.get_conf(self, 3257193194, force_registration=True)

        default_global = {
            "server": "127.0.0.1",
            "game_port": 7777,
            "offline_message": "Currently offline",
            "server_url": "byond://127.0.0.1:7777", 
            "new_round_channel": None,
            "admin_notice_channel": None,
            "comms_key": "default_pwd",
            "listen_port": 8081,
        }

        self.config.register_global(**default_global)
        serv = bot.loop.create_task(self.listener())
    
    def __unload(self):
        serv.cancel()

    async def changed_port(self, ctx, port: int):
        global serv
        serv.cancel()
        await asyncio.sleep(5) 
        serv = self.bot.loop.create_task(self.listener())
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
                await ctx.send(f"Database port set to: `{port}`")
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
    async def newroundnotificationchannel(self, ctx, text_channel: discord.TextChannel):
        """
        Set the text channel to display new round notifications
        """
        try: 
            await self.config.new_round_channel.set(text_channel.id)
            await ctx.send(f"New round notifications will be sent to: <#{text_channel.id}>")

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
            await ctx.send(f"Admin notifications will be sent to: <#{text_channel.id}>")

        except(ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting the notification channel. Please check your entry and try again.")

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
            elif k is 'new_round_channel' or k is 'admin_notice_channel': #Linkify channels
                embed.add_field(name=f"{k}:", value=f"<#{v}>", inline=False)
            else:
                embed.add_field(name=f"{k}:", value=v, inline=False)
        
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    #@commands.cooldown(1, 30)
    async def status(self, ctx):
        """
        Gets the current server status and round details
        """
        global statusmsg
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
            hours = int(round(duration/3600))
            minutes = int(round(duration/60))

            #Might make the embed configurable at a later date

            embed=discord.Embed(color=0x26eaea)
            embed.add_field(name="Version", value=str(*data['version']), inline=True)
            embed.add_field(name="Map", value=str(*data['map_name']), inline=True)
            embed.add_field(name="Mode", value=str(*data['mode']), inline=True)
            embed.add_field(name="Players", value=str(*data['players']), inline=True)
            embed.add_field(name="Admins", value=str(*data['admins']), inline=True)
            embed.add_field(name="Round Duration", value=f"{hours:02d}:{minutes:02d}", inline=True)
            embed.add_field(name="Server Link:", value=f"{server_url}", inline=False)

            try:
                await statusmsg.delete()
                statusmsg = await ctx.send(embed=embed)
            except(discord.DiscordException, AttributeError):
                statusmsg = await ctx.send(embed=embed)
        

    async def query_server(self, game_server:str, game_port:int ) -> dict:
        """
        Queries the server for information
        """
        querystr = "?status" #Might expand on this later to allow extra queries so I'm making this a separate string for now
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        try:
            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
            conn.settimeout(20) #Byond is slow, timeout set relatively high to account for any latency
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
            """
            
        except ConnectionRefusedError:
            return None #Server is likely offline

        finally:
            conn.close()
    
    async def spam_check(self):
        await asyncio.sleep(300)

        global antispam
        antispam = 0

    async def handle_data(self, reader, writer):
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
        global antispam
        global newroundmsg
        admin_channel = await self.config.admin_notice_channel()
        new_round_channel = await self.config.new_round_channel()
        comms_key = await self.config.comms_key()
        byondurl = await self.config.server_url()

        if ('key' in parsed_data) and (comms_key in parsed_data['key']): #Check to ensure that we're only serving messages from our game
            if ('serverStart' in parsed_data) and (new_round_channel is not None):
                embed = discord.Embed(title="Starting new round!", description=byondurl, color=0x8080ff)
                try:
                    await newroundmsg.delete()
                    newroundmsg = await self.bot.get_channel(new_round_channel).send(embed=embed)
                except(discord.DiscordException, AttributeError):
                    newroundmsg = await self.bot.get_channel(new_round_channel).send(embed=embed)

            elif ('announce_channel' in parsed_data) and ('admin' in parsed_data['announce_channel']): #Secret messages only meant for admin eyes
                announce = str(*parsed_data['announce'])
                if "Ticket" in announce:
                    ticket = announce.split('): ')
                    embed = discord.Embed(title=f"{ticket[0]}):", description=ticket[1],color=0xff0000)
                    await self.bot.get_channel(admin_channel).send(embed=embed)

                elif "@here" in announce and antispam == 0: #Ping any online admins once every 5 minutes
                    if "A new ticket" in announce:
                        await self.bot.get_channel(admin_channel).send(f"@here - A new ticket was submitted but no admins appear to be online.\n")
                        
                        antispam = 1
                        await self.spam_check()

                    else:
                        await self.bot.get_channel(admin_channel).send(f"@here - A new round ending event requires/might need attention, but there are no admins online.\n")

                        antispam = 1
                        await self.spam_check()

                elif "@here" not in announce: 
                    embed = discord.Embed(title=announce, color=0xf95100)
                    await self.bot.get_channel(admin_channel).send(embed=embed)

                else: #If it's not one of the above, it's not worth serving
                    pass
        else:#Don't serve any messages that aren't from our game
            pass


    async def listener(self):
        await asyncio.sleep(10) #Delay before listening to ensure that the interface isn't bound multiple times
        port = await self.config.listen_port()

        server = await asyncio.start_server(self.handle_data, '0.0.0.0', port) #Listen on all interfaces from a non-standard port

        async with server: #Listen until the cog is unloaded or the bot shutsdown
            await server.serve_forever()