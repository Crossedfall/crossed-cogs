#Standard Imports
import asyncio
from random import randint
import yaml
import datetime

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.data_manager import bundled_data_path, cog_data_path

__version__ = "0.0.1"
__author__ = "Crossedfall"

epoch = datetime.datetime.utcfromtimestamp(0)

BaseCog = getattr(commands, "Cog", object)

class BreenReacts(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = 0
        self.config = Config.get_conf(self, 3649816574, force_registration=True)

        default_global = {
            "channels": {},
        }

        self.listofbreens = str(bundled_data_path(self) / 'listofbreens.yml')
        self.terms_path = str(bundled_data_path(self) / 'terms.yml')

        self.config.register_global(**default_global)
    
    @commands.command()
    @commands.is_owner()
    async def breenify(self, ctx, channel: discord.TextChannel):
        """
        Add a channel to the cult of Breen
        """
        currentChannels = await self.config.channels()
        if str(channel.id) not in currentChannels:
                currentChannels[int(channel.id)] = (datetime.datetime.utcnow() - epoch).total_seconds()
                await self.config.channels.set(currentChannels)
                await ctx.send(f"I've added {channel} to the cult of Breen.")
        else:
            await ctx.send("That channel is already apart of the cult!")

    @commands.command()
    @commands.is_owner()
    async def debreen(self, ctx, channel: discord.TextChannel):
        """
        Remove a channel from the cult of Breen
        """
        currentChannels = await self.config.channels()
        if str(channel.id) not in currentChannels:
            await ctx.send("That channel is not apart of the cult!")
            await ctx.send(currentChannels)
        else:
            del currentChannels[str(channel.id)]
            await self.config.channels.set(currentChannels)
            await ctx.send(f"I've removed {channel} from the cult of Breen. It will no longer receive his blessing.")
    
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return
        if message.author.bot is True:
            return
        
        conf = await self.config.channels()

        if str(message.channel.id) in conf:    
            time_diff = (datetime.datetime.utcnow() - epoch).total_seconds() - conf[str(message.channel.id)]
            if time_diff >= 600:
                terms = yaml.load(open(self.terms_path))
                reactions = yaml.load(open(self.listofbreens))
                s = message.content.translate(str.maketrans('','',"!?.,'123456789"))

                
                for k, v in terms.items():
                    for i in v:
                        if i in s.lower():
                            index = randint(0, (len(reactions[k])-1))
                            conf[str(message.channel.id)] = (datetime.datetime.utcnow() - epoch).total_seconds()
                            await self.config.channels.set(conf)
                            await message.channel.send(reactions[k][index])
                            return
                

    

    