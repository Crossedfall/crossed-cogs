from .getnotes import GetNotes


async def setup(bot):
    await bot.add_cog(GetNotes(bot))
