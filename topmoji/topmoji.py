#Standard Imports
import asyncio

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, utils
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, contextlib
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
                return None
        
        async def next_page(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            perms = message.channel.permissions_for(ctx.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                with contextlib.suppress(discord.NotFound):
                    await message.remove_reaction(emoji, ctx.author)
            if page == len(pages) - 1:
                page = 0  # Loop around to the first item
            else:
                page = page + 1
            pages[page].set_footer(text=f"Page {page+1} of {len(pages)}")
            return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)


        async def prev_page(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            perms = message.channel.permissions_for(ctx.me)
            if perms.manage_messages:  # Can manage messages, so remove react
                with contextlib.suppress(discord.NotFound):
                    await message.remove_reaction(emoji, ctx.author)
            if page == 0:
                page = len(pages) - 1  # Loop around to the last item
            else:
                page = page - 1
            pages[page].set_footer(text=f"Page {page+1} of {len(pages)}")
            return await menu(ctx, pages, controls, message=message, page=page, timeout=timeout)
        
        TOPMOJI_CONTROLS = {"⬅": prev_page, "❌": close_menu, "➡": next_page}

        me = ctx.guild.get_member(self.bot.user.id)
        embed_footer = 1 #Page count

        await ctx.send("Counting messages. This may take a while...")
        async with ctx.typing():
            emojis = {emote[1]:0 for emote in enumerate(await ctx.guild.fetch_emojis())}
            messages = [message.content for channel in ctx.guild.text_channels if (channel.permissions_for(me)).read_message_history async for message in channel.history(limit=max_history) if message.author.bot is False]
            #These stupidly long lines shaves off up to 10% of the search time needed because python

            for message in messages:
                for emoji in emojis:
                    if f'{emoji}' in message:
                        emojis[emoji] += 1

            sorted_data = sorted(emojis.items(), key=lambda x: x[1], reverse=True)
            message = "{emote:45}{num:5}\n".format(emote="Emote", num="Count")
            for item in sorted_data:
                if item[1] == 0:
                    continue
                message += f"{f'{item[0]}':45}{item[1]}\n"
            page_list = []
            for page in pagify(message, delims=["\n"], page_length=2000):
                embed = discord.Embed(
                    color=await ctx.embed_color(), 
                    description=(box(page, lang="md")),
                    title=f"[Top Emotes]"
                )
                page_list.append(embed)
            page_list[0].set_footer(text=f"Page {embed_footer} of {len(page_list)}")
            await menu(ctx, page_list, TOPMOJI_CONTROLS)