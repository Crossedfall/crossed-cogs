#Standard Imports
import asyncio
import re
import yaml
from random import randint

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, prev_page, next_page
from redbot.core.data_manager import bundled_data_path, cog_data_path

__version__ = "0.1.1" #Working but needs optimization and actual features
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class PlusRep(BaseCog):
    def __init__(self, bot):
        self.upvote = "👍"
        self.downvote = "👎"
        self.selfvoters = {}
        self.bot = bot
        self.config = Config.get_conf(self, 3656823494, force_registration=True)

        default_guild = {
            "reputation": {},
            "reaction_channels": {},
            "threshold": 0,
            "role": None,
            "leaderboard_name": None
        }

        self.callouts = str(bundled_data_path(self) / 'callouts.yml')
        self.config.register_guild(**default_guild)


    @commands.guild_only()
    @commands.group()
    async def plusrep(self, ctx):
        """
        PlusRep Commands
        """
        pass

    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """
        Add/remove a channel from the bot's list of channels to monitor

        The bot will react to every message in this channel, so it's best to ensure that it's not a channel that has frequent discussions
        """
        try:
            channels = await self.config.guild(ctx.guild).reaction_channels()
            if channels.pop(f'{channel.id}', None) is not None:
                await self.config.guild(ctx.guild).reaction_channels.set(channels)
                await ctx.send(f"I will no longer monitor {channel.mention}.")
            else:
                channels[channel.id] = (channel.guild.id, channel.last_message_id)
                await self.config.guild(ctx.guild).reaction_channels.set(channels)
                await ctx.send(f"Understood! I will monitor {channel.mention} for new posts.")

        except(ValueError, TypeError, AttributeError):
            await ctx.send("There was a problem setting the channel. Please check your entry and try again!")
    
    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def listchannels(self, ctx):
        """
        Generate a list of channels being monitored in the current guild
        """
        channels = await self.config.guild(ctx.guild).reaction_channels()
        msg = "I am currently monitoring: "

        if channels:
            for channel in channels.keys():
                channel_obj = ctx.guild.get_channel(channel)
                if channel_obj is not None:
                    msg += f"{channel_obj.mention} "
        
        if msg is "I am currently monitoring: ":
            await ctx.send("I'm not monitoring any channels!")
        else:
            await ctx.send(msg)

    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def role(self, ctx, role: discord.Role = None, threshold: int = None):
        """
        Grant a role whenever a user gets enough reputation
        """

        if not role:
            await ctx.send("I will no longer grant a role if a user gains enough reputation.")
            await self.config.guild(ctx.guild).role.set(None)
            await self.config.guild(ctx.guild).threshold.set(None)
            return
        
        if not threshold:
            await ctx.send("How much reputation should a user have before I grant them their role?")
            pred = MessagePredicate.valid_int(ctx)
            await self.bot.wait_for('message', check=pred)
            await self.config.guild(ctx.guild).threshold.set(pred.result)
            await self.config.guild(ctx.guild).role.set(role)
            await ctx.send(f"Got it! I will grant the `{role.name}` role whenever a user gains {pred.result} reputation.")
            return

        await self.config.guild(ctx.guild).role.set(role.id)
        await self.config.guild(ctx.guild).threshold.set(threshold)
        await ctx.send(f"OK! I will grant the `{role.name}` role whenever a user gains {threshold} reputation.")

    @commands.admin_or_permissions(administrator=True)
    @plusrep.command()
    async def leaderboardname(self, ctx, *,name: str):
        """
        Sets the name of the guild's reputation leaderboard. Names are limited to a max of 70 characters.
        """
        if len(name) > 70:
            await ctx.send("Your name is too long, please provide a name that's at most 70 characters.")
            return
        
        await self.config.guild(ctx.guild).leaderboard_name.set(name)
        await ctx.send(f"Your leaderboard has been renamed to `{name}`.")
        

    @plusrep.command()
    async def leaderboard(self, ctx):
        """
        Guild reputation leaderboard
        """
        header = await ctx.send("Populating leaderboard....")

        async def close_menu(ctx: commands.Context, pages: list, controls: dict, message: discord.Message, page: int, timeout: float, emoji: str):
            if message:
                await message.delete()
                await header.delete()
                return None
        
        LEADERBOARD_CONTROLS = {"⬅": prev_page, "❌": close_menu, "➡": next_page}

        rep = await self.config.guild(ctx.guild).reputation()
        lname = await self.config.guild(ctx.guild).leaderboard_name()
        if not rep:
            await header.edit(content="Nobody has any reputation!")
            return
        else:
            sorted_data = sorted(rep.items(), key=lambda x: x[1], reverse=True)
            msg = "{name:33}{score:19}\n".format(name="Name", score="Rep")
            for i, user in enumerate(sorted_data):
                if user[1] == 0:
                    continue
                user_idx = i + 1
                user_obj = await self.bot.fetch_user(user[0])
                if user_obj == ctx.author:
                    name = f"{user_idx}. <<{user_obj.name}>>"
                else:
                    name = f"{user_idx}. {user_obj.name}"
                msg += f"{name:33}{user[1]}\n"
            
            page_list = []
            for page in pagify(msg, delims=["\n"], page_length=1000):
                embed = discord.Embed(
                    color=await ctx.embed_color(), description=(box(page, lang="md"))
                )
                page_list.append(embed)
            await header.edit(content=box(f"[{lname}]", lang="ini"))
            await menu(ctx, page_list, LEADERBOARD_CONTROLS)
            ### Thank you Aik for the above https://github.com/aikaterna/aikaterna-cogs/blob/v3/trickortreat/trickortreat.py#L187 ###

    @commands.is_owner()
    @plusrep.command()
    async def clear(self, ctx):
        """
        Clears ALL rep. Do not use this unless you need to
        """
        await self.config.guild(ctx.guild).reputation.set({})
        await ctx.send("Cleared")

    @commands.is_owner()
    @plusrep.command()
    async def tallyrep(self, ctx):
        """
        Command to force a full recount of rep. This will be slow if there are a lot of messages to check
        """
        rep = {}
        channels = (await self.config.guild(ctx.guild).reaction_channels()).keys()
        msg = await ctx.send("Getting rep. This may take a while if the channels are very large...")
        for channel in channels:
            try:
                channel = self.bot.get_channel(int(channel))
                async for message in channel.history(limit=2000):
                    if message.author.bot:
                        continue
                    if message.reactions:
                        for reaction in message.reactions:
                            reaction_users = await reaction.users().flatten()
                            if self.bot.user not in reaction_users:
                                continue
                            if str(reaction.emoji) == self.upvote:
                                if f'{message.author.id}' in rep:
                                    rep[f'{message.author.id}'] += reaction.count - 1
                                else:
                                    rep[f'{message.author.id}'] = 0
                                    rep[f'{message.author.id}'] += reaction.count - 1
                                if message.author in reaction_users:
                                    rep[f'{message.author.id}'] -= 1
                            elif str(reaction.emoji) == self.downvote:
                                if f'{message.author.id}' in rep:
                                    rep[f'{message.author.id}'] -= reaction.count - 1
                                    if rep[f'{message.author.id}'] <= 0:
                                        rep[f'{message.author.id}'] = 0
                                else:
                                    rep[f'{message.author.id}'] = 0
                                if message.author in reaction_users:
                                    rep[f'{message.author.id}'] += 1
            except:
                continue

        await self.config.guild(ctx.guild).reputation.set(rep)
        await msg.edit(content=f"Hey {ctx.author.mention}, the rep updated!")                     

    async def giverole(self, user: discord.Member, rep: int, channel: discord.channel):
        """
        Checks to see if a user has earned their role! Punishes those that hit zero rep
        """
        threshold = await self.config.guild(channel.guild).threshold()
        if not threshold:
            return
        
        role = channel.guild.get_role(await self.config.guild(channel.guild).role())

        if rep <= 0:
            if role in user.roles:
                await user.remove_roles(role, reason="Hit zero rep")
                await channel.send(f"Wow. You managed to hit zero rep {user.mention}. Guess you wont be needing your `{role.name}` role anymore.")
        elif rep < threshold:
            return
        else:
            if role not in user.roles:
                await user.add_roles(role, reason="Reputation threshold reached")
                await channel.send(f"Congrats {user.mention}! You've just earned the `{role.name}` role based on your current reputation!")        

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return
        if message.author.bot is True:
            return
        
        url = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content.lower())
        if not message.attachments and not url:
            return
        
        if f'{message.channel.id}' in (await self.config.guild(message.guild).reaction_channels()).keys():
            await message.add_reaction(self.upvote)
            await message.add_reaction(self.downvote)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):     
        channel = self.bot.get_channel(id=payload.channel_id)
        try:
            guild = channel.guild
        except AttributeError:
            return
        try:
            message = await channel.fetch_message(id=payload.message_id)
        except AttributeError:
            message = await channel.get_message(id=payload.message_id)
        except discord.errors.NotFound:
            return
        if f'{channel.id}' not in ((await self.config.guild(message.guild).reaction_channels()).keys()):
            return
        member = guild.get_member(message.author.id)
        reactor = guild.get_member(payload.user_id)
        if reactor.bot is True:
            return
        if message.author.bot:
            return
        #### Thanks Trusty for the above https://github.com/TrustyJAID/Trusty-cogs/blob/master/starboard/starboard.py#L756 ####
        for reaction in message.reactions:
            if self.upvote == str(reaction.emoji) or self.downvote == str(reaction.emoji):
                reaction_users = await reaction.users().flatten()
                if self.bot.user not in reaction_users:
                    return

        if self.upvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if member.id == reactor.id:
                if f'{reactor.id}' not in self.selfvoters:
                    self.selfvoters[f'{reactor.id}'] = 3
                    callouts = yaml.load(open(self.callouts))
                    index = randint(0, (len(callouts['selfvoters'])-1))
                    await channel.send(str(callouts["selfvoters"][index]).format(f'{reactor.mention}'))
                    return
                elif self.selfvoters[f'{reactor.id}'] > 0:
                    self.selfvoters[f'{reactor.id}'] -= 1
                    return
                else:
                    self.selfvoters.pop(f'{reactor.id}', None)
                    return

            if f'{member.id}' in rep.keys():
                rep[f'{member.id}'] += 1
            else:
                rep[f'{member.id}'] = 1
        elif self.downvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if member.id == reactor.id:
                return
            if f'{member.id}' in rep.keys():
                if rep[f'{member.id}'] <= 0:
                    rep[f'{member.id}'] = 0
                else:
                    rep[f'{member.id}'] -= 1
            else:
                rep[f'{member.id}'] = 0
        else:
            return
        
        await self.config.guild(message.guild).reputation.set(rep)
        await self.giverole(user=member, rep=rep[f'{member.id}'], channel=channel)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        channel = self.bot.get_channel(id=payload.channel_id)
        try:
            guild = channel.guild
        except AttributeError:
            return
        try:
            message = await channel.fetch_message(id=payload.message_id)
        except AttributeError:
            message = await channel.get_message(id=payload.message_id)
        except discord.errors.NotFound:
            return
        if f'{channel.id}' not in ((await self.config.guild(message.guild).reaction_channels()).keys()):
            return
        member = guild.get_member(message.author.id)
        reactor = guild.get_member(payload.user_id)
        if message.author.bot:
            return
        if reactor.bot is True:
            return
        if message.author.id == payload.user_id:
            return
        #### Thanks Trusty for the above ####
        valid = True
        for reaction in message.reactions:
            if self.upvote == str(reaction.emoji) or self.downvote == str(reaction.emoji):
                reaction_users = await reaction.users().flatten()
                if self.bot.user not in reaction_users:
                    valid = False
                else:
                    valid = True
        if valid is False:
            return

        if self.upvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                rep[f'{member.id}'] -= 1
            else:
                return
        elif self.downvote == str(payload.emoji):
            rep = await self.config.guild(message.guild).reputation()
            if f'{member.id}' in rep.keys():
                if rep[f'{member.id}'] <= 0:
                    return
                rep[f'{member.id}'] += 1
            else:
                return
        else:
            return
        
        await self.config.guild(message.guild).reputation.set(rep)
        await self.giverole(user=member, rep=rep[f'{member.id}'], channel=channel)