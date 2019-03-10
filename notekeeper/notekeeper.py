#Standard Imports
import asyncio
import mysql.connector
import ipaddress
from datetime import datetime
import math

#Discord Imports
import discord

#Redbot Imports
from redbot.core import commands, checks, Config, utils
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import (
    menu,
    DEFAULT_CONTROLS,
    prev_page,
    next_page,
    close_menu,
    start_adding_reactions,
)

__version__ = "0.1.0" #Working but needs optimization 
__author__ = "Crossedfall"


BaseCog = getattr(commands, "Cog", object)

class NoteKeeper(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 3657648194, force_registration=True)

        default_user = {
            "notes": {},
        }

        self.config.register_user(**default_user)

    @commands.command()
    async def createnote(self, ctx, *, note: str):
        """
        Create a new note
        """
        try: 
            date = datetime.today()
            notes = await self.config.user(ctx.author).notes()
            notes.update({date:f'{note}'})
            await self.config.user(ctx.author).notes.set(notes)
            await ctx.send("Your note has been saved!")
        except (ValueError, AttributeError, KeyError):
            await ctx.send("I ran into a problem saving your note! Please check your note and try again.")
        
    @commands.command()
    async def viewnotes(self, ctx): #Heavily borrowed from the Audio cog to make this
        """
        List all of your notes
        """

        async def _notes_menu(
            ctx: commands.Context,
            pages: list,
            controls: dict,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                await self._notes_button_action(ctx, all_notes, emoji, page)
                await message.delete()
                return None

        MENU_CONTROLS = {
            "1⃣": _notes_menu,
            "2⃣": _notes_menu,
            "3⃣": _notes_menu,
            "4⃣": _notes_menu,
            "5⃣": _notes_menu,
            "⬅": prev_page,
            "❌": close_menu,
            "➡": next_page,
        }
        notes = []
        all_notes = await self.config.user(ctx.author).notes()
        for index, (k,v) in enumerate(all_notes.items()):
            brief = v[:75] + (v[75:] and '...')
            note = {'Number':index, 'Date':datetime.strptime(k, '%Y-%m-%d %H:%M:%S.%f').date(), 'Note':brief}
            notes.append(note)
        
        len_note_pages = math.ceil(len(notes) / 5)
        notes_page_list = []
        for page_num in range(1, len_note_pages + 1):
            embed = await self._build_notes_list(ctx, notes, page_num)
            notes_page_list.append(embed)

        await menu(ctx, notes_page_list, MENU_CONTROLS)

    async def _build_notes_list(self, ctx, notes, page_num):
        notes_num_pages = math.ceil(len(notes) / 5)
        notes_idx_start = (page_num - 1) * 5
        notes_idx_end = notes_idx_start + 5
        notes_list = ""
        

        for i, note in enumerate(notes[notes_idx_start:notes_idx_end], start=notes_idx_start):
            note_num = i + 1
            if note_num > 5:
                note_num = note_num % 5
            if note_num == 0:
                note_num = 5
            
            notes_list += "`{0}.` **{1}**\n_{2}_\n".format(
                    note_num, note['Date'], note['Note']
                )
            
        embed = discord.Embed(
            color=0xf1d592, title="Notes:", description=notes_list
        )
        embed.set_footer(
            text=(("Page {page_num}/{total_pages}") + " | {num_results} {footer}").format(
                page_num=page_num,
                total_pages=notes_num_pages,
                num_results=len(notes),
                footer=("notes | All dates are determined by the bot's timezone")
            )
        )
        return embed

    async def _notes_button_action(self, ctx, notes, emoji, page):
        def get_nth_note(dict,  n=0):
            if n < 0:
                n += len(dict)
            for i, key in enumerate(dict.keys()):
                if i == n:
                    return (dict[key])
            raise IndexError

        if emoji == "1⃣":
            search_choice = 0 + (page * 5)
        if emoji == "2⃣":
            search_choice = 1 + (page * 5)
        if emoji == "3⃣":
            search_choice = 2 + (page * 5)
        if emoji == "4⃣":
            search_choice = 3 + (page * 5)
        if emoji == "5⃣":
            search_choice = 4 + (page * 5)

        try:
            note = get_nth_note(notes, search_choice)
            clean_date = datetime.strptime(list(notes.keys())[list(notes.values()).index(note)], '%Y-%m-%d %H:%M:%S.%f').date()
            embed = discord.Embed(
                color=0xf1d592, title=f"{clean_date}", description=note
            )

            await ctx.send(embed=embed)
        except IndexError:
            await ctx.send("Unable to get that note. Please try again and double check your selection.")
        
