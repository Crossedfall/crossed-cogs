from .plusrep import PlusRep

async def setup(bot):
    await bot.add_cog(PlusRep(bot))
