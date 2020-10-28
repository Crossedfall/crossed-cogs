#Standard Imports
import asyncio
import socket
import struct
import urllib.parse
import logging

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.predicates import MessagePredicate

__version__ = "1.1.0"
__author__ = "Crossedfall"

log = logging.getLogger("red.VerifyCkey")

class VerifyCkey(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.server_list = None
        self.config = Config.get_conf(self, 8949156131, force_registration=True)

        default_global = {
            "game_server": "golden.beestation13.com",
            "game_port": 1337,
            "comms_key": "test123",
            "guild_id": 427337870844362753,
            "roles_to_add": {},
            "persistent_verification": False,
            "verified_users": {},
            "verify_steps": {
                'step1':[
                    "Step 1: Login to the game server",
                    "Connect to the game server using your ckey",
                    "https://cdn.discordapp.com/attachments/668027476961918976/734710785485307955/unknown.png"
                ],
                'step2':[
                    "Step 2: Locate the account identifier verb",
                    "Navigate to the OOC tab and click on the `Show Account Identifier` verb. Copy the identifier string provided.",
                    "https://cdn.discordapp.com/attachments/668027476961918976/734712087611179047/unknown.png"
                ],
                'step3':[
                    "Step 3: Verify", 
                    "Send the bot your account identification string with `?identify <string>`. **DO NOT** use this command outside of a DM. This code is unique to you and SHOULD NOT BE SHARED. Treat it like a password.\n\nAfter a short wait, your account will be verified and a new role will be granted.",
                    "https://cdn.discordapp.com/attachments/668027476961918976/734910511115665448/unknown.png"
                ]
            }
        }

        self.config.register_global(**default_global)

    @commands.group()
    @checks.is_owner()
    async def ckeyauthset(self, ctx):
        """
        Config settings for BeeStation's Discord verification
        """
        pass

    @ckeyauthset.command()
    async def server(self, ctx, host:str, port:int):
        """
        IP or DNS and port used to connect to the game server
        """
        try:
            await self.config.game_server.set(host)
            await ctx.send(f"Server set to: `{host}`")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the host! Please check your entry and try again.")

        try:
            if 1024 <= port <= 65535: # We don't want to allow reserved ports to be set
                await self.config.game_port.set(port)
                await ctx.send(f"Host port set to: `{port}`")
            else:
                await ctx.send(f"`{port}` is not a valid port!")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was a problem setting your port. Please check to ensure you're attempting to use a port from 1024 to 65535")

    @ckeyauthset.command()
    async def commskey(self, ctx, key:str):
        """
        Set the comms key used to authenticate requests to the server

        Only use this command in DMs!
        """
        if isinstance(ctx.channel, discord.TextChannel):
            embed=discord.Embed(title="Warning!", description="Please DM me that command, do not use it here!", color=0xFF0000)
            await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass
        else:
            await self.config.comms_key.set(key)
            await ctx.send("Comms key set!")
    
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @ckeyauthset.command()
    async def roles(self, ctx, role:discord.Role):
        """
        Set the role(s) to be given out whenever a user verifies their account

        The guild will be globally set to match where this command is running from.
        """
        roles = await self.config.roles_to_add()
        if f'{role.id}' in roles.keys():
            del roles[f'{role.id}']
            await ctx.send(f"I will no longer grant the role `{role}` whenever a user verifies their account.")
        else:
            roles[f'{role.id}'] = role.name
            await ctx.send(f"Role added. Current roles: {humanize_list(list(roles.values()))}")
        
        await self.config.guild_id.set(ctx.guild.id)
        await self.config.roles_to_add.set(roles)

    @ckeyauthset.command()
    async def steps(self, ctx):
        """
        Change the text/images provided by the verify command
        """
        steps = await self.config.verify_steps()
        embed_list = []
        pred_continue = MessagePredicate.yes_or_no(ctx)
        pred_steps = MessagePredicate.same_context(ctx)

        for info in steps.values():
            embed=discord.Embed(title=f"{info[0]}", description=f"{info[1]}", color=0xf99437)
            embed.set_image(url=f"{info[2]}")
            embed_list.append(embed)
        
        for embed in embed_list:
            await ctx.send(embed=embed)

        await ctx.send("Would you like to change the above?")
        await self.bot.wait_for("message", check=pred_continue)
        if pred_continue.result is True:
            continue_steps = True
            step_count = 1
            while continue_steps is True:
                await ctx.send(f"Give me a title for step {step_count}")
                msg = await self.bot.wait_for("message", check=pred_steps)
                steps[f'step{step_count}'][0] = msg.content
                await ctx.send(f"Give me a description for step {step_count}")
                msg = await self.bot.wait_for("message", check=pred_steps)
                steps[f'step{step_count}'][1] = msg.content
                await ctx.send(f"Give me an image for step {step_count}")
                msg = await self.bot.wait_for("message", check=pred_steps)
                if msg.attachments:
                    steps[f'step{step_count}'][2] = msg.attachments[0].url
                else:
                    steps[f'step{step_count}'][2] = msg.content
                
                await ctx.send("Add more steps?")
                await self.bot.wait_for("message", check=pred_continue)
                if pred_continue.result is False:
                    continue_steps = False
                else:
                    step_count += 1
            
            await self.config.verify_steps.set(steps)
            await ctx.send("Your new steps are now..")
            embed_list = []
            for info in steps.values():
                embed=discord.Embed(title=f"{info[0]}", description=f"{info[1]}", color=0xf99437)
                embed.set_image(url=f"{info[2]}")
                embed_list.append(embed)
            
            for embed in embed_list:
                await ctx.send(embed=embed)
        else:
            await ctx.send("Understood! The steps will remain unchanged")
        
    @ckeyauthset.command()
    async def togglepersistence(self, ctx, toggle: bool = None):
        """
        Toggle persistent verification on/off

        Setting this to True will maintain a user's verification status, even if they leave the Discord server. If the user rejoins the server,
        they will be granted any verification roles registered with the `ckeyauthset roles` command. Requires the ability to manage roles.

        Setting this to False will have the bot remove a user's verification status after leaving the Discord server.
        """
        if toggle is None:
            toggle = await self.config.persistent_verification()
            toggle = not toggle

        if toggle is True:
            if ((ctx.guild.get_member(self.bot.user.id)).guild_permissions).manage_roles: #Can the bot manage roles?
                await self.config.persistent_verification.set(True)
                await ctx.send("I will maintain a user's verification status, even if they leave the Discord server.")
            else:
                await ctx.send("It doesn't look like I can manage roles, please check my permissions and try again.")
        else:
            await self.config.persistent_verification.set(False)
            await ctx.send("Users who leave the Discord server will no longer maintain their verification status.")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def verify(self, ctx):
        """
        Start the verification process
        """
        steps = await self.config.verify_steps()
        embed_list = []
        
        for info in steps.values():
            embed=discord.Embed(title=f"{info[0]}", description=f"{info[1]}", color=0xf99437)
            embed.set_image(url=f"{info[2]}")
            embed_list.append(embed)
        
        try:
            for embed in embed_list:
                await ctx.author.send(embed=embed)        
            try:
                await ctx.message.add_reaction("✅")
            except discord.errors.NotFound:
                pass
        except discord.Forbidden:
            await ctx.send("I can't send direct messages to you. Please open your DMs and try again.")
    
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def identify(self, ctx, identifier:str):
        """
        This command only works in DMs! Do not use this command in the main server
        """
        if isinstance(ctx.channel, discord.TextChannel):
            embed=discord.Embed(title="Warning!", description="Please DM me that command, do not use it here!", color=0xFF0000)
            message = await ctx.send(embed=embed)
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass

            await asyncio.sleep(15)
            try:
                await message.delete()
            except discord.NotFound:
                pass
        else:
            users = await self.config.verified_users()
            guild = self.bot.get_guild(await self.config.guild_id())
            member = guild.get_member(ctx.author.id)

            if guild is None:
                embed=discord.Embed(title="Error!", description="Configuration error detected. Unable to locate the registering Discord server. Please notify an admin!", color=0xFF0000)
                return await ctx.send(embed=embed)

            if f'{ctx.author.id}' not in users.keys():
                try:
                    ckey = await self.check_ckey(identifier)
                    if ckey:
                        ckey = ckey['identified_ckey'][0]
                        if ckey in users.values():
                            return await ctx.send(f"That identifier doesn't seem to exist. Please check the steps in `{ctx.prefix}verify` and try again.")
                        users[f'{ctx.author.id}'] = ckey
                        roles_dict = await self.config.roles_to_add()
                        roles_list = []
                        for role in roles_dict.keys():
                            roles_list.append(guild.get_role(int(role)))
                        await member.add_roles(*roles_list, reason="Verified user")        
                        await self.config.verified_users.set(users)
                        embed=discord.Embed(title=f"Welcome, {ckey.title()}!", description=f"I've added the following roles to you in Discord: **{humanize_list(list(roles_dict.values()))}**", color=0x77dd77)
                        embed.set_footer(text="Remember to read our rules and act accordingly. Enjoy your stay!")
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"That identifier doesn't seem to exist. Please check the steps in `{ctx.prefix}verify` and try again.")
                except (ConnectionRefusedError, socket.gaierror, socket.timeout):
                    await ctx.send("There was an error connecting to the server! Please try again later. If the problem persists, contact an admin.")
                except (discord.errors.Forbidden, discord.errors.HTTPException):
                    await ctx.send("I was unable to add your role. Please contact an admin asking them to check my permissions.")
            else:
                await ctx.send("You have already verified a ckey!")
    
    @commands.guild_only()
    @commands.command()
    @checks.admin()
    async def deverify(self, ctx, user:discord.Member):
        """
        Remove a user's verification status and relating roles
        """
        users = await self.config.verified_users()

        if f'{user.id}' in users.keys():
            roles_dict = await self.config.roles_to_add()
            roles_list = []
            for role in roles_dict.keys():
                roles_list.append(ctx.guild.get_role(int(role)))
            try:
                await user.remove_roles(*roles_list, reason=f"Deverified user. Requested by {ctx.author}")
            except discord.Forbidden:
                embed=discord.Embed(title="Unable to remove roles", description="Missing permissions to remove one or more roles. Please check to make sure that I have access to manage roles and that the role is not higher than mine.", color=0xFF0000)
                return await ctx.send(embed=embed)

            del users[f'{user.id}']
            await self.config.verified_users.set(users)
            await ctx.send(f"Deverified {user.name}.")

        else:
            await ctx.send("That user is not currently verified.")

    @commands.guild_only()
    @commands.command()
    @checks.mod()
    async def getckey(self, ctx, user:discord.Member):
        """
        Get the ckey associated with a specific Discord user
        """
        users = await self.config.verified_users()

        if f'{user.id}' in users.keys():
            await ctx.send(f"{user.mention}'s verified ckey is: `{users[f'{user.id}']}`")
        else:
            await ctx.send("That user hasn't verified a ckey.")

    async def check_ckey(self, uuid:str):
        """
        Verify the uuid with the server
        """
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 

            querystr = f"?key={await self.config.comms_key()}&identify_uuid&uuid={uuid}"

            query = b"\x00\x83" + struct.pack('>H', len(querystr) + 6) + b"\x00\x00\x00\x00\x00" + querystr.encode() + b"\x00" #Creates a packet for byond according to TG's standard
            conn.settimeout(60) #Byond is slow, timeout set relatively high to account for any latency
            conn.connect((await self.config.game_server(), await self.config.game_port())) 

            conn.sendall(query)

            data = conn.recv(4096) #Minimum number should be 4096, anything less will lose data

            parsed_data = urllib.parse.parse_qs(data[5:-1].decode())

            return parsed_data
        except (ConnectionRefusedError, socket.gaierror, socket.timeout) as e:
            raise e #Server is likely offline

        finally:
            conn.close()
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """
        Deverify users when they leave the guild
        """
        persistent_check = await self.config.persistent_verification()
        if persistent_check is True:
            return
        else:
            users = await self.config.verified_users()
            if f'{member.id}' in users.keys():
                del users[f'{member.id}']
                await self.config.verified_users.set(users)
                log.debug(f"Member left the server. Removed verification status for {member.name}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Re-verify users when they join the guild
        """
        persistent_check = await self.config.persistent_verification()
        if persistent_check is False:
            return
        else:
            users = await self.config.verified_users()
            if f'{member.id}' in users.keys():
                roles_dict = await self.config.roles_to_add()
                roles_list = []
                for role in roles_dict.keys():
                    roles_list.append(member.guild.get_role(int(role)))
                try:
                    await member.add_roles(*roles_list, reason="Verified user")
                    log.debug(f"Verified returning user {member.name}")
                except (discord.errors.HTTPException, discord.errors.Forbidden) as e:
                    log.warning(f"Unable to add roles to returning user {member.name}.\n{e}")
