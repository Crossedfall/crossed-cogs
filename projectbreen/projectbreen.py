#Standard Imports
import asyncio
from random import randint
import yaml

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.data_manager import bundled_data_path, cog_data_path

__version__ = "0.0.1"
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class ProjectBreen(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3649816574, force_registration=True)

        default_global = {
            "channels": [],
        }

        self.listofbreens = str(bundled_data_path(self) / 'listofbreens.yml')

        self.config.register_global(**default_global)
    
    @commands.command()
    @commands.is_owner()
    async def breenify(self, ctx, channel: discord.TextChannel):
        """
        Add a channel to the cult of Breen
        """
        currentChannels = await self.config.channels()
        if channel.id not in currentChannels:
                currentChannels.append(channel.id)
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
        if channel.id not in currentChannels:
            await ctx.send("That channel is not apart of the cult!")
        else:
            currentChannels.remove(channel.id)
            await self.config.channels.set(currentChannels)
            await ctx.send(f"I've removed {channel} from the cult of Breen. It will no longer receive his blessing.")
    
    @commands.command()
    @commands.is_owner()
    async def testbreen(self, ctx, keyword: str):
        """
        test the breen
        """
        breens = yaml.load(open(self.listofbreens))
        if keyword in breens:
            await ctx.send(breens[keyword][0])

    

    