from .dmcompile import DMCompile

async def setup(bot):
    await bot.add_cog(DMCompile(bot))
