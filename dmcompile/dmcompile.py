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
INCLUDE_PATTERN = re.compile(r'#(|\W+)include')

__version__ = "1.1.0"
__author__ = "Crossedfall"

BaseCog = getattr(commands, "Cog", object)

class DMCompile(BaseCog):
    def __init__(self, bot):
        
        self.bot = bot
        self.repo_tags = []
        self.config = Config.get_conf(self, 32174327454, force_registration=True)

        default_config = {
            "listener_url": "http://localhost:5000/compile",
            "default_version": "514.1589"
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
    async def listener(self, ctx, url:str):
        """
        Set the full URL for the listener

        Should be similar to: http://localhost:5000/compile
        """

        try:
            await self.config.listener_url.set(url)
            await ctx.send(f"Listener URL set to: {url}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the listener's URL. Please check your entry and try again.")

    @setcompile.command()
    async def default_version(self, ctx, version:str):
        """
        Set the default version of BYOND used

        Should be similar to: 514.1549
        """

        try:
            await self.config.default_version.set(version)
            await ctx.send(f"Default version set to: {version}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the default version. Please check your entry and try again.")

    @commands.command(usage="[version] <code>")
    async def compile(self, ctx, *, code:str):
        """
        Compile and run DM code

        This command will attempt to compile and execute given DM code. It will respond with the full compile log along with any outputs given during runtime. If there are any errors during compilation, the bot will respond with a list provided by DreamMaker.

        The code must be contained within a codeblock, for example:
        ```c
        world.log << "Hello world!"
        ```
        If you're using multiple functions, or if your code requires indentation, you must define a `proc/main()` as shown below.
        ```c
        proc/example()
            world.log << "I'm an example function!"

        proc/main()
            example()
        ```
        You can also do [p]compile `expression` to evaluate and print an expression. Example [p]compile `NORTH | EAST`.

        You can include the target BYOND version before the code block. Example: [p]compile 514.1549 `world.byond_build`
        """
        tiny_output = False

        version = await self.config.default_version()

        code_quote_char = '```' if '```' in code else '`'
        if code_quote_char not in code:
            return await ctx.send("Your code has to be in a code block!")
        maybe_version, code = code.split(code_quote_char, 1)
        code = code_quote_char + code
        maybe_version = maybe_version.strip()
        if maybe_version:
            version = maybe_version

        if code_quote_char == '`':
            tiny_output = True

        code = self.cleanup_code(utils.chat_formatting.escape(code))
        if code is None:
            return await ctx.send("Your code has to be in a code block!")
        if INCLUDE_PATTERN.search(code) is not None:
            return await ctx.send("You can't have any `#include` statements in your code.")
            
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
                if tiny_output:
                    await ctx.send("Timed out")
                    return await message.delete()
                else:
                    embed = discord.Embed(title="Execution timed out (30 seconds)", description=f"**Compiler Output:**\n{box(escape(compile_log, mass_mentions=True, formatting=True))}\n**Execution Output:**\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0xd3d3d3)
                    await ctx.send(embed=embed)
                    return await message.delete()

            errors = ERROR_PATTERN.search(compile_log)
            warnings = WARNING_PATTERN.search(compile_log)
            if int(errors.group(1)) > 0:
                if tiny_output:
                    await ctx.send("Compile error. Maybe you meant to use \\`\\`\\` instead of \\`?")
                    return await message.delete()
                else:
                    embed = discord.Embed(title="Compilation failed!", description=f"Compiler output:\n{box(escape(compile_log, mass_mentions=True, formatting=True))}", color=0xff0000)
                    await ctx.send(embed=embed)
                    return await message.delete()
            elif int(warnings.group(1)) > 0:
                embed = discord.Embed(title="Warnings found during compilation", description=f"**Compiler Output:**\n{box(escape(compile_log, mass_mentions=True, formatting=True))}**Execution Output:**\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0xffcc00)
                await ctx.send(embed=embed)
                return await message.delete()
            else:
                if tiny_output:
                    output = run_log
                    output = '\n'.join(output.split('\n')[2:]).strip()
                    output = '`' + escape(output, mass_mentions=True, formatting=True) + '`'
                    await ctx.send(output)
                    return await message.delete()
                else:
                    embed = discord.Embed(description=f"**Execution Output:**\n{box(escape(run_log, mass_mentions=True, formatting=True))}", color=0x00ff00)
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
        content = content.strip()
        if content.startswith("```") and content.endswith("```"):
            content = CODE_BLOCK_RE.sub("", content)[:-3]
            return content.strip('\n')
        elif content.startswith("`") and content.endswith("`"):
            return 'world.log << json_encode(' + content[1:-1] + ')'
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
        
