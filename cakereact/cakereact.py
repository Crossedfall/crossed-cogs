#Standard Imports
import asyncio

#Discord Imports
from discord.ext import commands

__version__ = "1.0.0"
__author__ = "Crossedfall"

class CakeReact:
    def __init__(self, bot):
        self.bot = bot
    
    @commands.cooldown(5, 60, commands.BucketType.channel)
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if 'cake' in message.content.lower():
            await message.add_reaction('🍰')
        if ('cookie' in message.content.lower()) or ('biscuit' in message.content.lower()):
            await message.add_reaction('🍪')
        if ('fix it' in message.content.lower()) or ('lil fix' in message.content.lower()):
            await message.add_reaction('<:lilfix:445057492834189322>')