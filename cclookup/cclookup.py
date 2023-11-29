# Standard Imports
import asyncio
from datetime import datetime

# Discord Imports
import discord

# Extra Imports
import httpx

# Redbot Imports
from redbot.core import commands
from redbot.core.utils.chat_formatting import box, humanize_list, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

# Util Imports
from .util import key_to_ckey

__version__ = "1.0.1"
__author__ = "Crossedfall"

BaseCog = getattr(commands, "Cog", object)


class CCLookup(BaseCog):
    def __init__(self, bot):

        self.bot = bot
        self.api_url = "https://centcom.melonmesa.com"

    @commands.command()
    @commands.cooldown(1, 2)
    @commands.max_concurrency(10, wait=True)
    async def centcom(self, ctx, ckey: str, active=False):
        """
        Checks the shared CentCom database for information on a given ckey

        Add "True" to the command if you'd like to only search through active bans. By default, this command will provide all bans

        The CentCom API is maintained by Bobbahbrown here: https://git.io/JJ7CD
        For information about the API itself, please visit: https://centcom.melonmesa.com/
        """
        converted_key = key_to_ckey(ckey)

        message = await ctx.send("Performing lookup...")

        bans = await self.centcom_lookup(converted_key, active=active)

        try:
            if bans is not None:
                if not bans:
                    active_text = ""
                    if active:
                        active_text = "active "
                    embed = discord.Embed(description=f"No {active_text}bans found for: {ckey.title()}", color=0x2B74AB)
                    return await message.edit(embed=embed, content="")
                else:
                    bans_list = ""
                    total = 0
                    temp_embeds = []
                    embeds = []
                    expiresstr = "Permanent"
                    status = "Active"

                    for ban in bans:
                        total += 1
                        if "expires" in ban:
                            expires = True
                            expiresstr = ban["expires"][:-10]
                        else:
                            expires = False
                            expiresstr = "Permanent"
                            status = "Active"
                        if not ban["active"]:
                            if "unbannedBy" in ban.keys():
                                status = "Unbanned"
                            elif expires and datetime.strptime(expiresstr, "%Y-%m-%d").date() < datetime.now().date():
                                status = "Expired"
                            else:
                                status = "Inactive"
                        bans_list += (
                            f"\n[Banned On: {ban['bannedOn'][:-10]} - Expires: {expiresstr} - {status}]\n"
                            f"{ban['reason']}\n"
                            f"{ban['type']} banned by {ban['bannedBy']} from {ban['sourceName']} ({ban['sourceRoleplayLevel']} RP)\n"
                            "-----"
                        )
                    for ban in pagify(bans_list, ["[Banned On:"]):
                        embed = discord.Embed(description=box(ban, lang="asciidoc"), color=0x2B74AB)
                        temp_embeds.append(embed)
                    max_i = len(temp_embeds)
                    i = 1
                    for embed in temp_embeds:
                        embed.set_author(name=f"Bans for {ckey.title()} | total bans: {total}")
                        embed.set_footer(text=f"Page {i}/{max_i}")
                        embeds.append(embed)
                        i += 1
                    await message.delete()
                    await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                await message.delete()
                await ctx.send("I am unable to connect to the CentCom API at this time.")
        except discord.NotFound:
            pass

    @commands.command()
    @commands.cooldown(1, 2)
    @commands.max_concurrency(10, wait=True)
    async def ccservers(self, ctx):
        """
        Gets a list of contributing servers
        """
        server_list = await self.centcom_server_list()
        server_names = []

        if server_list is not None:
            for server in server_list:
                server_names.append(server["name"])
            await ctx.send(f"The servers contributing to the CentCom ban database are: {humanize_list(server_names)}")
        else:
            await ctx.send("I am unable to get a list of servers at this time.")

    async def centcom_lookup(self, ckey: str, active=False) -> list:
        """
        Performs the full lookup of a given ckey with added optional parameters for active bans and specifying a source
        """
        params = ""
        max_attempts = 3
        attempt = 0

        if active is True:
            params = "?onlyActive=True"
        # ToDo add an option for 'source'
        # ---------------------------------
        # if source.lower() != "all":
        #   <processing to determine source ID>
        #   params += "?source={ID}"

        # httpx doesn't support retries, so we'll build our own basic loop for that
        while max_attempts > attempt:
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get(f"{self.api_url}/ban/search/{ckey}{params}")

                if r.status_code == 200:
                    return r.json()
                else:
                    attempt += 1
                await asyncio.sleep(5)
            except (httpx._exceptions.ConnectTimeout, httpx._exceptions.HTTPError):
                attempt += 1
                await asyncio.sleep(5)
                pass

        return None

    async def centcom_server_list(self) -> list:
        """
        Gets and returns a list of contributing servers
        """
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.api_url}/source/list")

            if r.status_code == 200:
                return r.json()
            else:
                return None
        except httpx._exceptions.ConnectTimeout:
            return None
