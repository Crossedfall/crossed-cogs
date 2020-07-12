# Standard Imports
import asyncio
import re
import json

# Extra Imports
import httpx

# Discord Imports
import discord

# Redbot Imports
from redbot.core import commands, checks, utils, Config
from redbot.core.utils import chat_formatting
from redbot.core.utils.chat_formatting import box, escape

CODE_BLOCK_RE = re.compile(r"^((```.*)(?=\s)|(```))")
ERROR_PATTERN = re.compile(r'\ntest\.dmb.\S.(\d*)\s(error)')
WARNING_PATTERN = re.compile(r'\ntest\.dmb.\S.\d*\serrors,\s(\d*).(warning.)')

__version__ = "1.0.0"
__author__ = "Crossedfall"

BaseCog = getattr(commands, "Cog", object)

class DMCompile(BaseCog):
    def __init__(self, bot):
        
        self.bot = bot
        self.repo_tags = []
        self.config = Config.get_conf(self, 32174327454, force_registration=True)

        default_config = {
            "listener_url": "http://localhost:5000/compile"
        }

        self.config.register_global(**default_config)
        self.cache_versions = self.bot.loop.create_task(self.version_list())

    @commands.group()
    @checks.admin_or_permissions(administrator=True)
    async def setcompile(self, ctx):
        """
        DM Compiler settings
        """
        pass

    @setcompile.command()
    async def listener(self, ctx, url:str = None):
        """
        Set the full URL for the listener

        Should be similar to: http://localhost:5000/compile
        """

        try:
            await self.config.listener_url.set(url)
            await ctx.send(f"Listener URL set to: {url}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the listener's URL. Please check your entry and try again.")
    
    @commands.command()
    async def listbyond(self, ctx):
        """
        List the available BYOND versions

        List generated from the beestation/byond docker repository.

        _This command also updates the internal list of available versions for the compiler._
        """

        repo_tags = await self.version_list()
        repo_tags.remove("latest")
        
        await ctx.send(f"The currently available BYOND versions are:\n> {chat_formatting.humanize_list(repo_tags)}")

    @commands.command()
    async def compile(self, ctx, version:str = "latest", *,code:str):
        """
        Compile and run DM code

        This command will attempt to compile and execute given DM code. It will respond with the full compile log along with any outputs given during runtime. If there are any errors during compilation, the bot will respond with a list provided by DreamMaker.

        The code must be contained within a codeblock, for example:
        ```
        world.log << 'Hello world!'
        ```
        If you're using multiple functions, or if your code requires indentation, you must define a `proc/main()` as shown below.
        ```
        proc/example()
            world.log << "I'm an example function!"

        proc/main()
            example()
        ```

        Use `listbyond` to get a list of BYOND versions you can compile with. 
        """
        if version == '```':
            version = "latest"
            code = f"```\n{code}"
        else:
            if version not in self.repo_tags:
                return await ctx.send(f"That version of BYOND is not supported. Use `{ctx.prefix}listbyond` for a list of supported versions.")
        
        code = self.cleanup_code(utils.chat_formatting.escape(code))
        if code is None:
            return await ctx.send("Your code has to be in a code block!")
            
        try:
            message = await ctx.send("Compiling....")
            
            async with ctx.typing():
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.post(await self.config.listener_url(), json={'code_to_compile':code, 'byond_version':version}, timeout=60)
                        r = r.json()
                except (json.JSONDecodeError, httpx.ReadTimeout):
                    embed = discord.Embed(description=f"There was a problem with the listener. Unable to retrieve any results!", color=0xff0000)
                    await ctx.send(embed=embed)
                    return await message.delete()

                if 'build_error' in r.keys():
                    embed = discord.Embed(title="Unable to build image", description=f"{r['exception']}", color=0xff0000)
                    await ctx.send(embed=embed)
                    return await message.delete()

                compile_log = r['compile_log']
                run_log = r['run_log']

            if r['timeout']:
                embed = discord.Embed(title="Execution timed out (30 seconds)", description=f"Compiler Output:\n{box(escape(compile_log, mass_mentions=True, formatting=True))}\nExecution Output:\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0xd3d3d3)
                await ctx.send(embed=embed)
                return await message.delete()

            errors = ERROR_PATTERN.search(compile_log)
            warnings = WARNING_PATTERN.search(compile_log)
            if int(errors.group(1)) > 0:
                embed = discord.Embed(title="Compilation failed!", description=f"Compiler output:\n{box(escape(compile_log, mass_mentions=True, formatting=True))}", color=0xff0000)
                await ctx.send(embed=embed)
                return await message.delete()
            elif int(warnings.group(1)) > 0:
                embed = discord.Embed(title="Warnings found during compilation", description=f"Compiler Output:\n{box(escape(compile_log, mass_mentions=True, formatting=True))}\nExecution Output:\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0xffcc00)
                await ctx.send(embed=embed)
                return await message.delete()
            else:
                embed = discord.Embed(description=f"Compiler Output:\n{box(escape(compile_log, mass_mentions=True, formatting=True))}\nExecution Output:\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0x00ff00)
                await ctx.send(embed=embed)
                return await message.delete()

        except (httpx.NetworkError, httpx.ConnectTimeout):
            embed = discord.Embed(description=f"Error connecting to listener", color=0xff0000)
            await ctx.send(embed=embed)
            return await message.delete()

        except AttributeError:
            embed = discord.Embed(description=f"There was a problem with the listener. Unable to retrieve any results!", color=0xff0000)
            await ctx.send(embed=embed)
            return await message.delete()

    def cleanup_code(self, content):
        """clears those pesky codeblocks"""
        if content.startswith("```") and content.endswith("```"):
            content = CODE_BLOCK_RE.sub("", content)[:-3]
            return content.strip('\n')
        else:
            return None

    async def version_list(self):
        """Gets a list of BYOND versions from Docker"""
        self.repo_tags = []

        async with httpx.AsyncClient() as client:
            r = await client.get('https://hub.docker.com/v2/repositories/beestation/byond/tags')
        
        for version in r.json()['results']:
            self.repo_tags.append(version['name'])
        
        self.repo_tags.sort()

        return self.repo_tags
        