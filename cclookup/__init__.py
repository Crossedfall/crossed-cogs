from .cclookup import CCLookup


async def setup(bot):
    await bot.add_cog(CCLookup(bot))
