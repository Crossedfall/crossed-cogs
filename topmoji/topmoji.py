#Standard Imports
import asyncio

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, utils
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, prev_page, next_page
from redbot.core.utils.chat_formatting import box, pagify

__version__ = "1.0.0"
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class Topmoji(BaseCog):
    def __init__(self, bot):
        self.bot = bot

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def topmoji(self, ctx, max_history: int = None):
        """
        Counts the total number of times a guild emoji has been used.

        Use this command with a number to define how far back this cog should look when counting emojis. The smaller the number the faster it'll be. 

        Using this command without a number will cause it to check every message it can. __This may take a long time and could use a lot of resources.__
        """
        async def close_menu(ctx: commands.Context, pages: list, controls: dict, message: discord.Message, page: int, timeout: float, emoji: str):
            if message:
                await message.delete()
                await msg.delete()
                return None
        
        TOPMOJI_CONTROLS = {"⬅": prev_page, "❌": close_menu, "➡": next_page}

        emojis = ctx.guild.emojis
        channels = ctx.guild.text_channels
        count = {}

        msg = await ctx.send("Counting emotes. This may take a while...")
        async with ctx.typing():
            for channel in channels:
                try:
                    async for message in channel.history(limit=max_history):
                        if message.author.bot is True:
                            continue
                        for emoji in emojis:
                            if f'{emoji.id}' in message.content:
                                if f'{emoji.id}' not in count:
                                    count[f'{emoji.id}'] = 1
                                else:
                                    count[f'{emoji.id}'] += 1
                except discord.errors.Forbidden:
                    continue

            sorted_data = sorted(count.items(), key=lambda x: x[1], reverse=True)
            message = "{emote:45}{num:5}\n".format(emote="Emote", num="Count")
            for item in enumerate(sorted_data):
                emote = f'{self.bot.get_emoji(int(item[1][0]))}'
                message += f"{emote:45}{item[1][1]}\n"
            page_list = []
            for page in pagify(message, delims=["\n"], page_length=1000):
                embed = discord.Embed(
                    color=await ctx.embed_color(), description=(box(page, lang="md"))
                )
                page_list.append(embed)
            await msg.edit(content=box(f"[Top Emotes]", lang="ini"))
            await menu(ctx, page_list, TOPMOJI_CONTROLS)
    