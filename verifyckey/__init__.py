from .verifyckey import VerifyCkey

async def setup(bot):
    await bot.add_cog(VerifyCkey(bot))
